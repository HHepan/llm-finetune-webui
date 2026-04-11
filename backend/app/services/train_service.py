import os
import re
import subprocess
import threading
from typing import Dict, List, Optional

WORKSPACE_ROOT = "/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace"
RWKV_PEFT_DIR = os.path.join(WORKSPACE_ROOT, "tools", "RWKV-PEFT")
JSON2BINIDX_DIR = os.path.join(RWKV_PEFT_DIR, "json2binidx_tool", "data")
VOCAB_FILE = os.path.join(RWKV_PEFT_DIR, "json2binidx_tool", "rwkv_vocab_v20230424.txt")
LORA_SCRIPT = os.path.join(RWKV_PEFT_DIR, "scripts", "lora.sh")
BASE_MODELS_DIR = os.path.join(WORKSPACE_ROOT, "base_models")
CHECKPOINTS_DIR = os.path.join(WORKSPACE_ROOT, "checkpoints")

MODEL_SIZE_MAP = {
    "0.1B": {"n_layer": 12, "n_embd": 768},
    "0.4B": {"n_layer": 24, "n_embd": 1024},
    "1.5B": {"n_layer": 24, "n_embd": 2048},
    "2.9B": {"n_layer": 32, "n_embd": 2560},
    "7B": {"n_layer": 32, "n_embd": 4096},
    "14B": {"n_layer": 61, "n_embd": 4096},
}


def clear_and_copy_data(train_data: str, train_data_folder: str) -> str:
    if os.path.exists(JSON2BINIDX_DIR):
        for f in os.listdir(JSON2BINIDX_DIR):
            os.remove(os.path.join(JSON2BINIDX_DIR, f))
    else:
        os.makedirs(JSON2BINIDX_DIR, exist_ok=True)

    src_file = os.path.join(WORKSPACE_ROOT, "data", train_data_folder, train_data)
    if not os.path.exists(src_file):
        raise FileNotFoundError(f"训练数据文件不存在: {src_file}")
    
    dst_file = os.path.join(JSON2BINIDX_DIR, train_data)
    subprocess.run(["cp", src_file, dst_file], check=True)
    
    return dst_file


def convert_data_to_binidx(data_file: str) -> str:
    base_name = os.path.splitext(data_file)[0]
    output_prefix = os.path.join(JSON2BINIDX_DIR, base_name)
    
    cmd = [
        "python3",
        os.path.join(RWKV_PEFT_DIR, "json2binidx_tool", "tools", "preprocess_data.py"),
        "--input", data_file,
        "--output-prefix", output_prefix,
        "--vocab", VOCAB_FILE,
        "--dataset-impl", "mmap",
        "--tokenizer-type", "RWKVTokenizer",
        "--append-eod"
    ]
    
    result = subprocess.run(cmd, cwd=RWKV_PEFT_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"数据转换失败: {result.stderr}")
    
    bin_file = os.path.join(JSON2BINIDX_DIR, f"{base_name}_text_document.bin")
    idx_file = os.path.join(JSON2BINIDX_DIR, f"{base_name}_text_document.idx")
    
    if os.path.exists(bin_file):
        final_bin = os.path.join(JSON2BINIDX_DIR, f"{base_name}.bin")
        final_idx = os.path.join(JSON2BINIDX_DIR, f"{base_name}.idx")
        subprocess.run(["mv", bin_file, final_bin], check=True)
        subprocess.run(["mv", idx_file, final_idx], check=True)
        return final_bin
    
    raise RuntimeError("转换后的 bin 文件未生成")


def generate_lora_script(params: Dict) -> str:
    model_cfg = MODEL_SIZE_MAP.get(params["model_size"], {"n_layer": 32, "n_embd": 2560})
    n_layer = model_cfg["n_layer"]
    n_embd = model_cfg["n_embd"]
    
    base_model_path = os.path.join(BASE_MODELS_DIR, params["base_model"])
    data_name = os.path.splitext(params["train_data"])[0]
    data_file = os.path.join(JSON2BINIDX_DIR, data_name)
    
    peft_config = f'{{"r":{params["lora_r"]},"lora_alpha":{params["lora_alpha"]},"lora_dropout":{params["lora_dropout"]}}}'
    
    script_content = f'''load_model="{base_model_path}"
proj_dir='{CHECKPOINTS_DIR}'
data_file={data_file}

n_layer={n_layer}
n_embd={n_embd}

micro_bsz={params["micro_bsz"]}
epoch_save={params["epoch_save"]}
epoch_steps={params["epoch_steps"]}
ctx_len={params["ctx_len"]}
peft_config='{peft_config}'

python train.py --load_model $load_model \\
  --proj_dir $proj_dir --data_file $data_file \\
  --vocab_size 65536 \\
  --data_type binidx \\
  --n_layer $n_layer --n_embd $n_embd \\
  --ctx_len $ctx_len --micro_bsz $micro_bsz \\
  --epoch_steps $epoch_steps --epoch_count {params["epoch_count"]} --epoch_save $epoch_save \\
  --lr_init {params["lr_init"]} --lr_final {params["lr_final"]} \\
  --accelerator gpu --precision bf16 \\
  --devices 1 --strategy deepspeed_stage_1 --grad_cp 1 \\
  --my_testing "x070" \\
  --peft lora --peft_config $peft_config
'''
    
    temp_script = os.path.join(RWKV_PEFT_DIR, "scripts", "lora_temp.sh")
    with open(temp_script, "w") as f:
        f.write(script_content)
    
    os.chmod(temp_script, 0o755)
    return temp_script


def parse_tqdm_line(line: str) -> dict | None:
    """解析tqdm进度条输出，提取结构化数据"""
    import re
    pattern = re.compile(
        r'Epoch (\d+):\s*.*?\| ?(\d+)/(\d+)\s+\[.*?(\d+\.\d+)it/s.*?lr=([\d.e-]+).*?sum_loss=([\d.]+).*?loss=([\d.]+)'
    )
    match = pattern.search(line)
    if match:
        return {
            "current_epoch": int(match.group(1)),
            "total_epochs": 0,  
            "current_step": int(match.group(2)),
            "total_steps": int(match.group(3)),
            "its_per_sec": float(match.group(4)),
            "lr": float(match.group(5)),
            "sum_loss": float(match.group(6)),
            "loss": float(match.group(7))
        }
    return None


def run_training(
    params: Dict,
    on_log: callable,
    on_progress: callable,
    on_complete: callable,
    on_error: callable,
    stop_event: callable = None
) -> subprocess.Popen:
    process = None
    try:
        on_log("开始准备训练数据...")
        
        data_file = clear_and_copy_data(params["train_data"], params["train_data_folder"])
        on_log(f"已复制训练数据: {params['train_data']}")
        
        on_log("正在转换数据格式...")
        bin_file = convert_data_to_binidx(data_file)
        on_log(f"数据转换完成: {bin_file}")
        
        on_log("正在生成训练脚本...")
        script_path = generate_lora_script(params)
        on_log(f"训练脚本已生成")
        
        on_log("开始训练...")
        process = subprocess.Popen(
            ["sh", script_path],
            cwd=RWKV_PEFT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True
        )
        
        print(f"[DEBUG] process started, pid = {process.pid}")
        
        epoch_pattern = re.compile(r'Epoch\s+(\d+)/(\d+)\s+\|\s+Step\s+(\d+)/(\d+)\s+\|\s+Loss:\s+([\d.]+)')
        
        line_count = 0
        for line in iter(process.stdout.readline, ''):
            line_count += 1
            if line_count % 100 == 0:
                print(f"[DEBUG] read {line_count} lines, last line: {line[:50]}")
            
            if stop_event and stop_event():
                on_log("正在停止训练...")
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                on_log("训练已停止")
                return process
            
            tqdm_data = parse_tqdm_line(line)
            if tqdm_data:
                on_progress(
                    tqdm_data["current_epoch"],
                    tqdm_data["total_epochs"],
                    tqdm_data["current_step"],
                    tqdm_data["total_steps"],
                    tqdm_data["loss"],
                    tqdm_data["lr"],
                    tqdm_data["its_per_sec"],
                    tqdm_data["sum_loss"]
                )
                on_log(line.strip())
            
            match = epoch_pattern.search(line)
            if match:
                current_epoch = int(match.group(1))
                total_epochs = int(match.group(2))
                current_step = int(match.group(3))
                total_steps = int(match.group(4))
                loss = float(match.group(5))
                
                on_progress(current_epoch, total_epochs, current_step, total_steps, loss)
            
            if not tqdm_data and not match:
                on_log(line.strip())
        
        print(f"[DEBUG] process.wait() called, pid = {process.pid}")
        process.wait()
        print(f"[DEBUG] process.wait() returned, returncode = {process.returncode}")
        
        if process.returncode == 0:
            on_log("训练完成!")
            on_complete()
        else:
            on_error(f"训练失败，退出码: {process.returncode}")
            
    except Exception as e:
        print(f"[DEBUG] run_training exception: {e}")
        print(f"[DEBUG] exception type: {type(e)}")
        import traceback
        print(f"[DEBUG] traceback: {traceback.format_exc()}")
        on_error(str(e))
    
    print(f"[DEBUG] run_training about to return, process = {process}")
    return process