import json
import os
import signal
import shutil
import subprocess
import threading
import time
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import train_service

router = APIRouter(prefix="/api/train", tags=["train"])

CHECKPOINTS_DIR = "/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/checkpoints"

current_save_folder = None
current_params = None

def get_save_dir(save_folder: str) -> str:
    return os.path.join(CHECKPOINTS_DIR, save_folder)

def get_state_file(save_folder: str):
    return os.path.join(get_save_dir(save_folder), "train_inf.json")

def get_logs_file(save_folder: str):
    return os.path.join(get_save_dir(save_folder), "train_logs.txt")

def get_loss_file(save_folder: str):
    return os.path.join(get_save_dir(save_folder), "loss_history.jsonl")

def get_pid_file(save_folder: str):
    return os.path.join(get_save_dir(save_folder), "train_pid.txt")

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
    save_folder: str = "default"
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


def load_state_from_files(save_folder: str):
    state_file = get_state_file(save_folder)
    logs_file = get_logs_file(save_folder)
    loss_file = get_loss_file(save_folder)
    
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                saved_data = json.load(f)
                if "status" in saved_data:
                    saved_status = saved_data["status"]
                    for key in ["status", "start_time", "current_epoch", "current_step", "total_epochs", "total_steps", "current_lr", "its_per_sec", "sum_loss"]:
                        if key in saved_status:
                            train_state[key] = saved_status[key]
                if "params" in saved_data:
                    global current_params
                    current_params = saved_data["params"]
        except Exception:
            pass

    if os.path.exists(logs_file):
        try:
            with open(logs_file, 'r') as f:
                train_state["logs"] = f.read().splitlines()
        except Exception:
            pass

    if os.path.exists(loss_file):
        try:
            loss_history = []
            with open(loss_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            loss_history.append(json.loads(line))
                        except Exception:
                            pass
            train_state["loss_history"] = loss_history
        except Exception:
            pass


def save_state_to_files(save_folder: str, params: Dict = None):
    save_dir = get_save_dir(save_folder)
    os.makedirs(save_dir, exist_ok=True)

    state_file = get_state_file(save_folder)
    logs_file = get_logs_file(save_folder)
    loss_file = get_loss_file(save_folder)

    total_epochs = params.get("epoch_count", 1) if params else train_state.get("total_epochs", 1)

    status_data = {
        "status": train_state["status"],
        "start_time": train_state["start_time"],
        "current_epoch": train_state["current_epoch"],
        "current_step": train_state["current_step"],
        "total_epochs": total_epochs,
        "total_steps": train_state["total_steps"],
        "current_lr": train_state.get("current_lr", 0),
        "its_per_sec": train_state.get("its_per_sec", 0),
        "sum_loss": train_state.get("sum_loss", 0),
    }

    params_data = params if params else {}

    state_to_save = {
        "status": status_data,
        "params": params_data
    }

    with open(state_file, 'w') as f:
        json.dump(state_to_save, f)

    with open(logs_file, 'w') as f:
        f.write('\n'.join(train_state["logs"]))

    with open(loss_file, 'w') as f:
        for entry in train_state["loss_history"]:
            f.write(json.dumps(entry) + '\n')


def check_process_running(save_folder: str):
    pid_file = get_pid_file(save_folder)
    if not os.path.exists(pid_file):
        return False
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        import signal
        os.kill(pid, signal.SIGOPT)
        return True
    except Exception:
        return False


def save_pid(save_folder: str):
    import time
    pid_file = get_pid_file(save_folder)
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))


# 模块初始化时不加载状态，改为在启动训练时加载


def create_log_callback():
    def on_log(message: str):
        with log_lock:
            train_state["logs"].append(message)
            if current_save_folder:
                save_state_to_files(current_save_folder, current_params)
    return on_log


def create_progress_callback():
    def on_progress(current_epoch: int, total_epochs: int, current_step: int, total_steps: int, loss: float, lr: float = 0, its_per_sec: float = 0, sum_loss: float = 0):
        train_state["current_epoch"] = current_epoch
        train_state["current_step"] = current_step
        train_state["current_lr"] = lr
        train_state["its_per_sec"] = its_per_sec
        train_state["sum_loss"] = sum_loss
        with log_lock:
            train_state["loss_history"].append({
                "step": current_step,
                "loss": loss,
                "epoch": current_epoch
            })
            if current_save_folder:
                save_state_to_files(current_save_folder, current_params)
    return on_progress


def create_complete_callback():
    def on_complete():
        train_state["status"] = "completed"
        if current_save_folder:
            save_state_to_files(current_save_folder, current_params)
            if os.path.exists(get_pid_file(current_save_folder)):
                os.remove(get_pid_file(current_save_folder))
    return on_complete


def create_error_callback():
    def on_error(message: str):
        train_state["status"] = "error"
        with log_lock:
            train_state["logs"].append(f"错误: {message}")
            if current_save_folder:
                save_state_to_files(current_save_folder, current_params)
                if os.path.exists(get_pid_file(current_save_folder)):
                    os.remove(get_pid_file(current_save_folder))
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
        "save_folder": current_save_folder or "",
    }


@router.get("/logs")
async def get_logs() -> List[str]:
    if train_state["status"] == "idle":
        return []
    return train_state["logs"]


@router.get("/loss")
async def get_loss() -> List[Dict]:
    return train_state["loss_history"]


@router.get("/loss-file/{folder_name}")
async def get_loss_from_file(folder_name: str) -> List[Dict]:
    """从文件读取损失数据"""
    loss_file = os.path.join(CHECKPOINTS_DIR, folder_name, "loss_data.jsonl")
    if not os.path.exists(loss_file):
        return []
    
    loss_data = []
    try:
        with open(loss_file, 'r') as f:
            for index, line in enumerate(f, 1):
                if line.strip():
                    try:
                        data = json.loads(line)
                        loss_data.append({
                            "step": index,
                            "loss": data.get("loss", 0)
                        })
                    except Exception:
                        pass
    except Exception:
        pass
    
    return loss_data


@router.post("/start")
async def start_training(req: TrainRequest):
    global train_thread, current_save_folder, current_params
    
    if train_state["status"] == "running":
        raise HTTPException(status_code=400, detail="训练正在进行中")

    current_save_folder = req.save_folder
    current_params = req.model_dump()
    
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

    save_state_to_files(current_save_folder, current_params)
    save_pid(current_save_folder)

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
    
    if current_save_folder:
        train_state["status"] = "stopped"
        save_state_to_files(current_save_folder, current_params)
        if os.path.exists(get_pid_file(current_save_folder)):
            os.remove(get_pid_file(current_save_folder))
    
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


@router.get("/folders")
async def get_existing_folders():
    """获取已存在的训练文件夹列表"""
    checkpoints_path = CHECKPOINTS_DIR
    if os.path.exists(checkpoints_path):
        folders = [f for f in os.listdir(checkpoints_path) 
                   if os.path.isdir(os.path.join(checkpoints_path, f))]
        return folders
    return []


@router.get("/records")
async def get_train_records():
    """获取训练记录列表"""
    checkpoints_path = CHECKPOINTS_DIR
    records = []
    if os.path.exists(checkpoints_path):
        for folder in os.listdir(checkpoints_path):
            folder_path = os.path.join(checkpoints_path, folder)
            if os.path.isdir(folder_path):
                state_file = os.path.join(folder_path, "train_inf.json")
                if os.path.exists(state_file):
                    try:
                        with open(state_file, 'r') as f:
                            data = json.load(f)
                            params = data.get("params", {})
                            status_data = data.get("status", {})
                            status = status_data.get("status", "unknown")
                            start_time = status_data.get("start_time", 0)
                            time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(start_time)) if start_time else "未知"
                            records.append({
                                "folder_name": folder,
                                "time": time_str,
                                "base_model": params.get("base_model", "未知"),
                                "train_data": params.get("train_data", "未知"),
                                "status": status
                            })
                    except Exception:
                        pass
    return records


@router.get("/records/{folder_name}")
async def get_record_detail(folder_name: str):
    """获取单条训练记录详情"""
    folder_path = os.path.join(CHECKPOINTS_DIR, folder_name)
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="记录不存在")
    
    result = {"folder_name": folder_name}
    
    state_file = os.path.join(folder_path, "train_inf.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
                result["params"] = data.get("params", {})
                result["state"] = data.get("status", {})
        except Exception:
            pass
    
    loss_file = os.path.join(folder_path, "loss_history.jsonl")
    loss_history = []
    if os.path.exists(loss_file):
        try:
            with open(loss_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            loss_history.append(json.loads(line))
                        except Exception:
                            pass
        except Exception:
            pass
    result["loss_history"] = loss_history
    
    logs_file = os.path.join(folder_path, "train_logs.txt")
    logs = []
    if os.path.exists(logs_file):
        try:
            with open(logs_file, 'r') as f:
                logs = f.read().splitlines()
        except Exception:
            pass
    result["logs"] = logs
    
    return result


@router.delete("/records/{folder_name}")
async def delete_record(folder_name: str):
    """删除训练记录"""
    folder_path = os.path.join(CHECKPOINTS_DIR, folder_name)
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="记录不存在")
    
    shutil.rmtree(folder_path)
    return {"message": "删除成功"}