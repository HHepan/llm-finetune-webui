"""
Benchmark: Dual-GPU RWKV_x070 (原生PyTorch) vs rwkv-fla (Triton kernel)
使用 13.3B 模型，HuggingFace 格式 tokenizer。
"""

import time
import gc
import sys
import os

# Add parent dir for app.services imports
sys.path.insert(0, os.path.dirname(__file__))

import torch
import sys
sys.path.append("/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/tools/RWKV-PEFT/json2binidx_tool/tools")
from rwkv_tokenizer import RWKV_TOKENIZER

# ─── Model paths ──────────────────────────────────────────────────────────
PTH_PATH = "/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/base_models/rwkv7-g1g-13.3b-20260523-ctx8192.pth"
FLA_DIR = "/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/base_models/rwkv7-g1g-13.3b-20260523-ctx8192-fla"

# ─── Test config ──────────────────────────────────────────────────────────
PROMPT = "Hello, my name is"
PREVIEW_CHARS = 30  # preview first / last N chars
BURN_TOKENS = 5     # first N tokens excluded from avg (warmup)
GEN_TOKENS = 50     # total tokens to generate per run
REPEAT = 3          # repeat runs to get stable avg

# ─── Tokenizer ────────────────────────────────────────────────────────────
print("Loading tokenizer ...")
tokenizer = RWKV_TOKENIZER("/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/tools/RWKV-PEFT/json2binidx_tool/rwkv_vocab_v20230424.txt")
print(f"  OK")

TOKEN_STOP = [0]

def _decode(tok):
    try:
        return tokenizer.decode([tok])
    except Exception:
        return "[?]"


# ════════════════════════════════════════════════════════════════════════════
# Benchmark 1: RWKV_x070_Dual (原生 PyTorch)
# ════════════════════════════════════════════════════════════════════════════

def bench_rwkv_dual():
    from app.services.rwkv_x070_dual import RWKV_x070_Dual

    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()

    t_start = time.time()
    model = RWKV_x070_Dual(model=PTH_PATH, strategy='cuda:0 fp16 -> cuda:1 fp16')
    model.eval()
    torch.cuda.synchronize()
    load_time = time.time() - t_start

    # Encode prompt
    tokens = tokenizer.encode(PROMPT)

    # Warmup: run one token forward
    state = [None] * (model.n_layer * 3)
    for i in range(model.n_layer):
        dev = model.dev_map.get(i, str(model.z['emb.weight'].device)) if model.is_multi else str(model.z['emb.weight'].device)
        stype = model.dtype
        state[i*3+0] = torch.zeros(model.n_embd, dtype=stype, device=dev)
        state[i*3+1] = torch.zeros((model.n_embd // model.head_size, model.head_size, model.head_size),
                                   dtype=torch.float, device=dev)
        state[i*3+2] = torch.zeros(model.n_embd, dtype=stype, device=dev)

    logits, state = model.forward(tokens, state)
    torch.cuda.synchronize()

    # Benchmark: token-by-token decode
    timings = []
    cur_token = int(torch.argmax(logits).item())
    output_tokens = [cur_token]

    for step in range(1, GEN_TOKENS):
        torch.cuda.synchronize()
        t0 = time.perf_counter()

        logits, state = model.forward([cur_token], state)

        torch.cuda.synchronize()
        t1 = time.perf_counter()

        timings.append(t1 - t0)
        cur_token = int(torch.argmax(logits).item())
        output_tokens.append(cur_token)

        if cur_token in TOKEN_STOP and step >= 3:
            output_tokens = output_tokens[:-1]
            break

    # Compute stats
    if len(timings) > BURN_TOKENS:
        warm_timings = timings[BURN_TOKENS:]
    else:
        warm_timings = timings

    avg_ms = sum(warm_timings) / len(warm_timings) * 1000
    tokens_per_sec = 1.0 / (sum(warm_timings) / len(warm_timings))

    text = tokenizer.decode(output_tokens)
    preview = f"{text[:PREVIEW_CHARS]} ... {text[-PREVIEW_CHARS:]}" if len(text) > PREVIEW_CHARS * 2 + 3 else text

    del model
    gc.collect()
    torch.cuda.empty_cache()

    return {
        "name": "RWKV_x070_Dual (原生 PyTorch)",
        "load_time": load_time,
        "total_tokens": len(output_tokens),
        "avg_ms_per_token": round(avg_ms, 2),
        "tokens_per_sec": round(tokens_per_sec, 2),
        "output_preview": preview,
        "per_step_ms": [round(t * 1000, 1) for t in timings],
    }


# ════════════════════════════════════════════════════════════════════════════
# Benchmark 2: FLAInference (rwkv-fla Triton)
# ════════════════════════════════════════════════════════════════════════════

def bench_fla():
    from app.services.fla_inference import FLAInference

    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()

    t_start = time.time()
    fla = FLAInference(
        model_dir=FLA_DIR,
        dtype=torch.float16,
        split_layer=31,  # 61 layers: 0-30 on GPU 0, 31-60 on GPU 1
    )
    torch.cuda.synchronize()
    load_time = time.time() - t_start

    # Prefill
    tokens = tokenizer.encode(PROMPT)
    emb_device = str(fla.model.model.embeddings.weight.device)

    with torch.no_grad():
        input_ids = torch.tensor([tokens], dtype=torch.long, device=emb_device)
        outputs = fla.model(input_ids=input_ids, past_key_values=None, use_cache=True)
        pkv = outputs.past_key_values
        logits = outputs.logits[0, -1, :]

    torch.cuda.synchronize()

    # Benchmark: token-by-token decode
    timings = []
    cur_token = int(torch.argmax(logits).item())
    output_tokens = [cur_token]

    for step in range(1, GEN_TOKENS):
        torch.cuda.synchronize()
        t0 = time.perf_counter()

        with torch.no_grad():
            next_id = torch.tensor([[cur_token]], dtype=torch.long, device=emb_device)
            outputs = fla.model(input_ids=next_id, past_key_values=pkv, use_cache=True)
            pkv = outputs.past_key_values
            logits = outputs.logits[0, -1, :]

        torch.cuda.synchronize()
        t1 = time.perf_counter()

        timings.append(t1 - t0)
        cur_token = int(torch.argmax(logits).item())
        output_tokens.append(cur_token)

        if cur_token in TOKEN_STOP and step >= 3:
            output_tokens = output_tokens[:-1]
            break

    # Compute stats
    if len(timings) > BURN_TOKENS:
        warm_timings = timings[BURN_TOKENS:]
    else:
        warm_timings = timings

    avg_ms = sum(warm_timings) / len(warm_timings) * 1000
    tokens_per_sec = 1.0 / (sum(warm_timings) / len(warm_timings))

    text = tokenizer.decode(output_tokens)
    preview = f"{text[:PREVIEW_CHARS]} ... {text[-PREVIEW_CHARS:]}" if len(text) > PREVIEW_CHARS * 2 + 3 else text

    del fla
    gc.collect()
    torch.cuda.empty_cache()

    return {
        "name": "FLAInference (rwkv-fla Triton)",
        "load_time": load_time,
        "total_tokens": len(output_tokens),
        "avg_ms_per_token": round(avg_ms, 2),
        "tokens_per_sec": round(tokens_per_sec, 2),
        "output_preview": preview,
        "per_step_ms": [round(t * 1000, 1) for t in timings],
    }


# ════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("RWKV 13.3B 推理速度 Benchmark")
    print(f"Prompt: '{PROMPT}'")
    print(f"Target: {GEN_TOKENS} tokens (burn={BURN_TOKENS}), {REPEAT} runs each")
    print("=" * 72)

    all_results = {}

    # ── Run RWKV Dual ──
    print("\n[1/2] Running RWKV_x070_Dual ...")
    if REPEAT > 1:
        print(f"  Warmup run (ignored)...")
        bench_rwkv_dual()

    rwkv_runs = []
    for r in range(REPEAT):
        print(f"  Run {r+1}/{REPEAT} ...", end=" ", flush=True)
        res = bench_rwkv_dual()
        print(f"{res['tokens_per_sec']} tok/s")
        rwkv_runs.append(res)

    avg_tps = sum(r["tokens_per_sec"] for r in rwkv_runs) / len(rwkv_runs)
    all_results["RWKV_x070_Dual"] = {
        "runs": rwkv_runs,
        "avg_tps": round(avg_tps, 2),
        "avg_ms": round(1000 / avg_tps, 2),
        "load_time": rwkv_runs[0]["load_time"],
        "output_preview": rwkv_runs[0]["output_preview"],
    }

    # ── Run FLA ──
    print("\n[2/2] Running FLAInference ...")
    if REPEAT > 1:
        print(f"  Warmup run (ignored)...")
        bench_fla()

    fla_runs = []
    for r in range(REPEAT):
        print(f"  Run {r+1}/{REPEAT} ...", end=" ", flush=True)
        res = bench_fla()
        print(f"{res['tokens_per_sec']} tok/s")
        fla_runs.append(res)

    avg_tps = sum(r["tokens_per_sec"] for r in fla_runs) / len(fla_runs)
    all_results["FLAInference"] = {
        "runs": fla_runs,
        "avg_tps": round(avg_tps, 2),
        "avg_ms": round(1000 / avg_tps, 2),
        "load_time": fla_runs[0]["load_time"],
        "output_preview": fla_runs[0]["output_preview"],
    }

    # ── Summary ──
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)

    for key, data in all_results.items():
        rtk = data["avg_tps"]
        rms = data["avg_ms"]
        print(f"\n  {key}:")
        print(f"    Load time:     {data['load_time']:.1f}s")
        print(f"    Avg speed:     {rtk} tok/s  ({rms} ms/token)")
        per_run = [f"{r['tokens_per_sec']}" for r in data["runs"]]
        print(f"    Per-run:       {', '.join(per_run)} tok/s")
        print(f"    Output:        {data['output_preview']}")

    # Speedup
    d_tps = all_results["RWKV_x070_Dual"]["avg_tps"]
    f_tps = all_results["FLAInference"]["avg_tps"]
    if d_tps > 0:
        speedup = f_tps / d_tps
        print(f"\n  Speedup (FLA vs Dual): {speedup:.2f}x")
        if speedup > 1:
            print(f"  FLA is {speedup:.2f}x faster ✓")
        else:
            print(f"  FLA is {1/speedup:.2f}x slower ✗")

    print()


if __name__ == "__main__":
    main()
