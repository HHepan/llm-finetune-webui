"""
Convert RWKV .pth weights → HuggingFace safetensors + config.json for rwkv-fla.

Usage:
    python convert_rwkv_to_fla.py <input.pth> [--output-dir <dir>]

Output:
    <output_dir>/config.json
    <output_dir>/model.safetensors  (or sharded: model-00001-of-XXXXX.safetensors)

Author: auto-generated for rwkv-fla integration
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, OrderedDict

import torch
from safetensors.torch import save_file


def parse_args():
    p = argparse.ArgumentParser(description="Convert RWKV .pth to HF safetensors for rwkv-fla")
    p.add_argument("input", type=str, help="Path to .pth file")
    p.add_argument("--output-dir", "-o", type=str, default=None,
                   help="Output directory (default: same dir as input)")
    p.add_argument("--dtype", type=str, default="fp16",
                   choices=["fp16", "bf16", "fp32"],
                   help="Output dtype (default: fp16)")
    p.add_argument("--max-shard-size", type=str, default="5GB",
                   help="Maximum shard size (default: 5GB)")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Key mapping: .pth → HuggingFace state_dict keys for RWKV7ForCausalLM (rwkv-fla)
# ---------------------------------------------------------------------------

def build_fla_state_dict(raw: Dict[str, torch.Tensor], n_layer: int, dtype: torch.dtype) -> Dict[str, torch.Tensor]:
    """
    Convert a raw RWKV .pth state_dict to rwkv-fla key names.

    The .pth uses post-transpose weights for the 4 main projection matrices:
      - receptance.weight, key.weight, value.weight, output.weight, head.weight
      are stored as [n_embd, n_embd] or [vocab_size, n_embd] (already transposed).

    rwkv-fla expects standard nn.Linear format: [out_features, in_features], so
    the post-transpose format is exactly what nn.Linear expects.  We are good.

    The LoRA modules in fla use:
      w_lora.lora.0.weight  ← w1
      w_lora.lora.2.weight  ← w2
      w_lora.lora.2.bias    ← w0 (squeezed)
      a_lora.lora.0.weight  ← a1
      a_lora.lora.2.weight  ← a2
      a_lora.lora.2.bias    ← a0 (squeezed)
      g_lora.lora.0.weight  ← g1
      g_lora.lora.2.weight  ← g2
      g_lora.lora.2.bias    ← None (g_lora created with bias=False)
      v_lora.lora.0.weight  ← v1 (only for layer_idx > 0)
      v_lora.lora.2.weight  ← v2
      v_lora.lora.2.bias    ← v0 (only for layer_idx > 0)
    """

    sd = OrderedDict()

    # ---- Embedding ----
    sd["model.embeddings.weight"] = raw["emb.weight"].to(dtype)

    # ---- Layers ----
    for i in range(n_layer):
        b = f"blocks.{i}."
        fla = f"model.layers.{i}."

        # -- LayerNorm 1 (pre-attn) --
        sd[f"{fla}attn_norm.weight"] = raw[f"{b}ln1.weight"].to(dtype)
        sd[f"{fla}attn_norm.bias"] = raw[f"{b}ln1.bias"].to(dtype)

        # -- LayerNorm 2 (pre-ffn) --
        sd[f"{fla}ffn_norm.weight"] = raw[f"{b}ln2.weight"].to(dtype)
        sd[f"{fla}ffn_norm.bias"] = raw[f"{b}ln2.bias"].to(dtype)

        # -- Pre-norm (layer 0 only) --
        if i == 0:
            sd[f"{fla}pre_norm.weight"] = raw[f"{b}ln0.weight"].to(dtype)
            sd[f"{fla}pre_norm.bias"] = raw[f"{b}ln0.bias"].to(dtype)

        a = f"{b}att."

        # -- Time-shift parameters [1, 1, hidden_size] --
        for ts in ["x_r", "x_w", "x_k", "x_v", "x_a", "x_g"]:
            sd[f"{fla}attn.{ts}"] = raw[f"{a}{ts}"].to(dtype)

        # -- Projection matrices (already [out, in] = nn.Linear format) --
        sd[f"{fla}attn.r_proj.weight"] = raw[f"{a}receptance.weight"].to(dtype)
        sd[f"{fla}attn.k_proj.weight"] = raw[f"{a}key.weight"].to(dtype)
        sd[f"{fla}attn.v_proj.weight"] = raw[f"{a}value.weight"].to(dtype)
        sd[f"{fla}attn.o_proj.weight"] = raw[f"{a}output.weight"].to(dtype)

        # -- k_k, k_a: .pth [1,1,H] → FLA expects [H] --
        sd[f"{fla}attn.k_k"] = raw[f"{a}k_k"].squeeze(0).squeeze(0).to(dtype)
        sd[f"{fla}attn.k_a"] = raw[f"{a}k_a"].squeeze(0).squeeze(0).to(dtype)
        sd[f"{fla}attn.r_k"] = raw[f"{a}r_k"].to(dtype)  # [n_head, head_size]

        # -- GroupNorm (ln_x) --
        sd[f"{fla}attn.g_norm.weight"] = raw[f"{a}ln_x.weight"].to(dtype)
        sd[f"{fla}attn.g_norm.bias"] = raw[f"{a}ln_x.bias"].to(dtype)

        # -- LoRA modules: ALL matrices need .t() (.pth [in,out] → FLA [out,in]) --
        # w1/w2 + w0 bias: .pth [1,1,H] → FLA [H]
        sd[f"{fla}attn.w_lora.lora.0.weight"] = raw[f"{a}w1"].t().contiguous().to(dtype)
        sd[f"{fla}attn.w_lora.lora.2.weight"] = raw[f"{a}w2"].t().contiguous().to(dtype)
        sd[f"{fla}attn.w_lora.lora.2.bias"] = raw[f"{a}w0"].squeeze(0).squeeze(0).to(dtype)

        # a1/a2 + a0 bias
        sd[f"{fla}attn.a_lora.lora.0.weight"] = raw[f"{a}a1"].t().contiguous().to(dtype)
        sd[f"{fla}attn.a_lora.lora.2.weight"] = raw[f"{a}a2"].t().contiguous().to(dtype)
        sd[f"{fla}attn.a_lora.lora.2.bias"] = raw[f"{a}a0"].squeeze(0).squeeze(0).to(dtype)

        # g1/g2 (no bias)
        sd[f"{fla}attn.g_lora.lora.0.weight"] = raw[f"{a}g1"].t().contiguous().to(dtype)
        sd[f"{fla}attn.g_lora.lora.2.weight"] = raw[f"{a}g2"].t().contiguous().to(dtype)

        # v1/v2 + v0 bias (only for layer_idx > 0)
        if i > 0:
            sd[f"{fla}attn.v_lora.lora.0.weight"] = raw[f"{a}v1"].t().contiguous().to(dtype)
            sd[f"{fla}attn.v_lora.lora.2.weight"] = raw[f"{a}v2"].t().contiguous().to(dtype)
            sd[f"{fla}attn.v_lora.lora.2.bias"] = raw[f"{a}v0"].squeeze(0).squeeze(0).to(dtype)

        # -- FFN --
        ff = f"{b}ffn."
        sd[f"{fla}ffn.x_k"] = raw[f"{ff}x_k"].squeeze(0).squeeze(0).to(dtype)
        sd[f"{fla}ffn.key.weight"] = raw[f"{ff}key.weight"].to(dtype)
        sd[f"{fla}ffn.value.weight"] = raw[f"{ff}value.weight"].to(dtype)

    # ---- Final LayerNorm ----
    sd["model.norm.weight"] = raw["ln_out.weight"].to(dtype)
    sd["model.norm.bias"] = raw["ln_out.bias"].to(dtype)

    # ---- LM head ----
    sd["lm_head.weight"] = raw["head.weight"].to(dtype)

    return sd


def infer_config(raw: Dict[str, torch.Tensor]) -> dict:
    """Infer RWKV7Config from raw .pth tensors."""
    n_head, head_size = raw['blocks.0.att.r_k'].shape
    vocab_size, n_embd = raw['emb.weight'].shape
    n_layer = max(int(k.split('.')[1]) + 1 for k in raw if 'blocks.' in k)

    # Infer LoRA dimensions from first block
    w1_shape = raw['blocks.0.att.w1'].shape  # [n_embd, decay_rank]
    a1_shape = raw['blocks.0.att.a1'].shape  # [n_embd, a_rank]
    g1_shape = raw['blocks.0.att.g1'].shape  # [n_embd, gate_rank]
    v1_shape = raw['blocks.1.att.v1'].shape  # [n_embd, v_rank] (layer 1, since layer 0 has no v_lora)

    # FFN intermediate size from block 0
    ffn_key = raw['blocks.0.ffn.key.weight'].shape  # [intermediate, n_embd]
    intermediate_size = ffn_key[0]

    return {
        "attn_mode": "chunk",
        "hidden_size": n_embd,
        "hidden_ratio": intermediate_size // n_embd,
        "intermediate_size": intermediate_size,
        "num_hidden_layers": n_layer,
        "head_dim": head_size,
        "num_heads": n_head,
        "decay_low_rank_dim": w1_shape[1],
        "gate_low_rank_dim": g1_shape[1],
        "a_low_rank_dim": a1_shape[1],
        "v_low_rank_dim": v1_shape[1],
        "hidden_act": "sqrelu",
        "max_position_embeddings": 8192,
        "norm_first": True,
        "norm_bias": True,
        "norm_eps": 1e-5,
        "attn": None,
        "use_cache": True,
        "pad_token_id": 0,
        "bos_token_id": 1,
        "eos_token_id": 2,
        "tie_word_embeddings": False,
        "initializer_range": 0.02,
        "fuse_norm": True,
        "fuse_cross_entropy": True,
        "fuse_linear_cross_entropy": False,
        "use_l2warp": False,
        "vocab_size": vocab_size,
        "value_dim": [n_embd] * n_layer,  # same as hidden_size for this model
        "model_type": "rwkv7",
        "transformers_version": "4.50.0",
        "architectures": ["RWKV7ForCausalLM"],
    }


def parse_shard_size(s: str) -> int:
    """Parse a shard size string like '5GB' → number of bytes."""
    s = s.strip().upper()
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    for unit, mult in sorted(units.items(), key=lambda x: -len(x[0])):
        if s.endswith(unit):
            return int(float(s[:-len(unit)]) * mult)
    return int(s)


def save_state_dict(sd: Dict[str, torch.Tensor], output_dir: Path, max_shard_size: int):
    """Save state dict as one or more safetensors files, with index if sharded."""
    total = sum(t.numel() * t.element_size() for t in sd.values())

    if total <= max_shard_size:
        path = output_dir / "model.safetensors"
        save_file(sd, str(path))
        return {"weight_map": {k: "model.safetensors" for k in sd}}

    # Sharding
    shards = []
    current_shard = OrderedDict()
    current_size = 0
    shard_idx = 0

    for key, tensor in sd.items():
        t_size = tensor.numel() * tensor.element_size()
        if current_size + t_size > max_shard_size and current_shard:
            shards.append((shard_idx, current_shard))
            shard_idx += 1
            current_shard = OrderedDict()
            current_size = 0
        current_shard[key] = tensor
        current_size += t_size
    if current_shard:
        shards.append((shard_idx, current_shard))

    weight_map = OrderedDict()
    for idx, shard_sd in shards:
        filename = f"model-{idx+1:05d}-of-{len(shards):05d}.safetensors"
        save_file(shard_sd, str(output_dir / filename))
        for k in shard_sd:
            weight_map[k] = filename

    return {"weight_map": weight_map, "total_size": total}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent / f"{input_path.stem}-fla"
    output_dir.mkdir(parents=True, exist_ok=True)

    dtype_map = {"fp16": torch.float16, "bf16": torch.bfloat16, "fp32": torch.float32}
    dtype = dtype_map[args.dtype]
    max_shard_size = parse_shard_size(args.max_shard_size)

    print(f"Loading {input_path} ...")
    raw = torch.load(str(input_path), map_location="cpu", mmap=True, weights_only=True)

    print(f"Inferring config ...")
    config = infer_config(raw)
    print(f"  n_layer={config['num_hidden_layers']}, n_embd={config['hidden_size']}, "
          f"n_head={config['num_heads']}, head_dim={config['head_dim']}")
    print(f"  vocab={config['vocab_size']}, ffn_intermediate={config['intermediate_size']}")

    print(f"Converting weights to {args.dtype} ...")
    sd = build_fla_state_dict(raw, config["num_hidden_layers"], dtype)

    total_params = sum(t.numel() for t in sd.values())
    total_bytes = sum(t.numel() * t.element_size() for t in sd.values())
    print(f"  Total params: {total_params/1e9:.2f}B, size: {total_bytes/1024**3:.2f} GB")

    # Clean up raw to free memory
    del raw

    print(f"Saving config.json ...")
    with open(output_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"Saving weights (max shard: {args.max_shard_size}) ...")
    index_data = save_state_dict(sd, output_dir, max_shard_size)

    if "weight_map" in index_data and len(set(index_data["weight_map"].values())) > 1:
        with open(output_dir / "model.safetensors.index.json", "w", encoding="utf-8") as f:
            json.dump({
                "metadata": {"total_size": index_data["total_size"]},
                "weight_map": index_data["weight_map"],
            }, f, indent=2)

    print(f"\nDone! HF model saved to: {output_dir}")
    print(f"  {output_dir}/config.json")
    for fname in sorted(set(index_data.get("weight_map", {"": "model.safetensors"}).values())):
        print(f"  {output_dir}/{fname}")


if __name__ == "__main__":
    main()
