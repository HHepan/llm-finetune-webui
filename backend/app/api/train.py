import json
import os
import signal
import subprocess
import threading
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import train_service

router = APIRouter(prefix="/api/train", tags=["train"])

CHECKPOINTS_DIR = "/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/checkpoints"
STATE_FILE = os.path.join(CHECKPOINTS_DIR, "train_state.json")
LOGS_FILE = os.path.join(CHECKPOINTS_DIR, "train_logs.txt")
LOSS_FILE = os.path.join(CHECKPOINTS_DIR, "loss_history.jsonl")
PID_FILE = os.path.join(CHECKPOINTS_DIR, "train_pid.txt")

train_state = {
    "status": "idle",
    "start_time": 0,
    "current_epoch": 0,
    "current_step": 0,
    "total_epochs": 1,
    "total_steps": 100,
    "current_lr": 0,
    "its_per_sec": 0,
    "sum_loss": 0,
    "logs": [],
    "loss_history": [],
}

log_lock = threading.Lock()
train_thread = None
training_process = None
stop_event = threading.Event()


class TrainRequest(BaseModel):
    base_model: str
    model_size: str = "2.9B"
    train_data: str
    train_data_folder: str = "out"
    micro_bsz: int = 1
    epoch_save: int = 1
    epoch_steps: int = 1000
    ctx_len: int = 512
    epoch_count: int = 1
    lr_init: float = 2e-5
    lr_final: float = 2e-5
    lora_r: int = 32
    lora_alpha: int = 32
    lora_dropout: float = 0.01


def load_state_from_files():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                saved_state = json.load(f)
                for key in ["status", "start_time", "current_epoch", "current_step", "total_epochs", "total_steps", "current_lr", "its_per_sec", "sum_loss"]:
                    if key in saved_state:
                        train_state[key] = saved_state[key]
        except Exception:
            pass

    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, 'r') as f:
                train_state["logs"] = f.read().splitlines()
        except Exception:
            pass

    if os.path.exists(LOSS_FILE):
        try:
            loss_history = []
            with open(LOSS_FILE, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            loss_history.append(json.loads(line))
                        except Exception:
                            pass
            train_state["loss_history"] = loss_history
        except Exception:
            pass


def save_state_to_files():
    os.makedirs(CHECKPOINTS_DIR, exist_ok=True)

    state_to_save = {
        "status": train_state["status"],
        "start_time": train_state["start_time"],
        "current_epoch": train_state["current_epoch"],
        "current_step": train_state["current_step"],
        "total_epochs": train_state["total_epochs"],
        "total_steps": train_state["total_steps"],
        "current_lr": train_state.get("current_lr", 0),
        "its_per_sec": train_state.get("its_per_sec", 0),
        "sum_loss": train_state.get("sum_loss", 0),
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state_to_save, f)

    with open(LOGS_FILE, 'w') as f:
        f.write('\n'.join(train_state["logs"]))

    with open(LOSS_FILE, 'w') as f:
        for entry in train_state["loss_history"]:
            f.write(json.dumps(entry) + '\n')


def check_process_running():
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        import signal
        os.kill(pid, signal.SIGOPT)
        return True
    except Exception:
        return False


def save_pid():
    import time
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


load_state_from_files()

if train_state["status"] == "running" and not check_process_running():
    train_state["status"] = "interrupted"


def create_log_callback():
    def on_log(message: str):
        with log_lock:
            train_state["logs"].append(message)
            save_state_to_files()
    return on_log


def create_progress_callback():
    def on_progress(current_epoch: int, total_epochs: int, current_step: int, total_steps: int, loss: float, lr: float = 0, its_per_sec: float = 0, sum_loss: float = 0):
        train_state["current_epoch"] = current_epoch
        train_state["current_step"] = current_step
        train_state["total_epochs"] = total_epochs
        train_state["total_steps"] = total_steps
        train_state["current_lr"] = lr
        train_state["its_per_sec"] = its_per_sec
        train_state["sum_loss"] = sum_loss
        with log_lock:
            train_state["loss_history"].append({
                "step": current_step,
                "loss": loss,
                "epoch": current_epoch
            })
            save_state_to_files()
    return on_progress


def create_complete_callback():
    def on_complete():
        train_state["status"] = "completed"
        save_state_to_files()
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    return on_complete


def create_error_callback():
    def on_error(message: str):
        train_state["status"] = "error"
        with log_lock:
            train_state["logs"].append(f"错误: {message}")
            save_state_to_files()
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    return on_error


def training_worker(params: Dict):
    global training_process
    print(f"[DEBUG] training_worker started, train_data = {params.get('train_data', 'unknown')}")
    
    result = train_service.run_training(
        params=params,
        on_log=create_log_callback(),
        on_progress=create_progress_callback(),
        on_complete=create_complete_callback(),
        on_error=create_error_callback(),
        stop_event=lambda: stop_event.is_set()
    )
    print(f"[DEBUG] run_training returned, result = {result}, type = {type(result)}")
    training_process = result
    
    print(f"[DEBUG] training_worker finished, setting training_process to None")
    training_process = None
    print(f"[DEBUG] training_process now = {training_process}")


@router.get("/status")
async def get_status() -> Dict:
    return {
        "status": train_state["status"],
        "current_epoch": train_state["current_epoch"],
        "current_step": train_state["current_step"],
        "total_epochs": train_state["total_epochs"],
        "total_steps": train_state["total_steps"],
        "current_lr": train_state.get("current_lr", 0),
        "its_per_sec": train_state.get("its_per_sec", 0),
        "sum_loss": train_state.get("sum_loss", 0),
    }


@router.get("/logs")
async def get_logs() -> List[str]:
    if train_state["status"] == "idle":
        return []
    return train_state["logs"]


@router.get("/loss")
async def get_loss() -> List[Dict]:
    return train_state["loss_history"]


@router.post("/start")
async def start_training(req: TrainRequest):
    global train_thread
    
    if train_state["status"] == "running":
        raise HTTPException(status_code=400, detail="训练正在进行中")

    import time
    train_state["status"] = "running"
    train_state["start_time"] = int(time.time())
    train_state["current_epoch"] = 0
    train_state["current_step"] = 0
    train_state["total_epochs"] = req.epoch_count
    train_state["total_steps"] = req.epoch_steps
    train_state["current_lr"] = 0
    train_state["its_per_sec"] = 0
    train_state["sum_loss"] = 0
    train_state["logs"] = []
    train_state["loss_history"] = []

    print(f"[DEBUG] start_training called")

    save_state_to_files()
    save_pid()

    params = req.model_dump()
    print(f"[DEBUG] params: {params}")
    
    training_process = True
    print(f"[DEBUG] training_process set to True")
    
    train_thread = threading.Thread(target=training_worker, kwargs={"params": params}, daemon=True)
    print(f"[DEBUG] thread created, starting...")
    train_thread.start()
    print(f"[DEBUG] thread started")

    return {"message": "训练已启动", "status": "running"}


@router.post("/stop")
async def stop_training():
    global training_process
    
    print(f"[DEBUG] stop_training called, training_process = {training_process}")
    print(f"[DEBUG] type: {type(training_process)}")
    
    print(f"[DEBUG] checking for python/sh processes related to training...")
    import os
    import subprocess as sp
    try:
        result = sp.run(['ps', 'aux'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'python' in line.lower() or 'train' in line.lower() or 'lora' in line.lower() or 'RWKV' in line:
                print(f"[DEBUG] process: {line[:100]}")
    except Exception as e:
        print(f"[DEBUG] failed to list processes: {e}")
    
    stop_event.set()
    print(f"[DEBUG] stop_event set")
    
    if training_process and training_process is not True:
        print(f"[DEBUG] training_process is process object, checking if running...")
        
        poll_result = training_process.poll()
        print(f"[DEBUG] poll() = {poll_result}")
        
        if poll_result is None:
            print(f"[DEBUG] process is running, pid = {training_process.pid}")
            try:
                os.kill(training_process.pid, signal.SIGTERM)
                print(f"[DEBUG] SIGTERM sent to {training_process.pid}")
                training_process.wait(timeout=10)
                print(f"[DEBUG] process exited after SIGTERM")
            except subprocess.TimeoutExpired:
                print(f"[DEBUG] process timeout, sending SIGKILL")
                os.kill(training_process.pid, signal.SIGKILL)
                training_process.wait()
            except ProcessLookupError:
                print(f"[DEBUG] process not found (gone)")
        else:
            print(f"[DEBUG] process already exited, returncode = {poll_result}")
    else:
        print(f"[DEBUG] training_process is True or None, checking process list...")
        
        import subprocess as sp
        
        print(f"[DEBUG] killing all training processes...")
        
        try:
            result = sp.run(['pkill', '-9', '-f', 'train.py'], capture_output=True, text=True)
            print(f"[DEBUG] pkill train.py result: {result.returncode}")
        except Exception as e:
            print(f"[DEBUG] failed to pkill train.py: {e}")
        
        try:
            result = sp.run(['pkill', '-9', '-f', 'lora_temp.sh'], capture_output=True, text=True)
            print(f"[DEBUG] pkill lora_temp.sh result: {result.returncode}")
        except Exception as e:
            print(f"[DEBUG] failed to pkill lora_temp.sh: {e}")
        
        try:
            result = sp.run(['pkill', '-9', '-f', 'python.*train.py'], capture_output=True, text=True)
            print(f"[DEBUG] pkill python train.py result: {result.returncode}")
        except Exception as e:
            print(f"[DEBUG] failed to pkill python train.py: {e}")
        
        try:
            result = sp.run(['pkill', '-9', '-f', 'RWKV-PEFT'], capture_output=True, text=True)
            print(f"[DEBUG] pkill RWKV-PEFT result: {result.returncode}")
        except Exception as e:
            print(f"[DEBUG] failed to pkill RWKV-PEFT: {e}")
    
    stop_event.clear()
    
    for f in [STATE_FILE, LOGS_FILE, LOSS_FILE, PID_FILE]:
        if os.path.exists(f):
            os.remove(f)
    
    train_state["status"] = "idle"
    train_state["start_time"] = 0
    train_state["current_epoch"] = 0
    train_state["current_step"] = 0
    train_state["total_epochs"] = 1
    train_state["total_steps"] = 100
    train_state["logs"] = []
    train_state["loss_history"] = []
    
    training_process = None
    
    return {"message": "训练已停止", "status": "idle"}