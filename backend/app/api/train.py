import time
import random
import threading
from typing import List, Dict
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/train", tags=["train"])

train_state = {
    "status": "idle",
    "start_time": 0,
    "current_epoch": 0,
    "current_step": 0,
    "total_epochs": 1,
    "total_steps": 100,
    "logs": [],
    "loss_history": [],
}

log_lock = threading.Lock()


def generate_mock_logs():
    with log_lock:
        for epoch in range(1, train_state["total_epochs"] + 1):
            train_state["current_epoch"] = epoch
            for step in range(1, train_state["total_steps"] + 1):
                train_state["current_step"] = step
                progress = ((epoch - 1) * train_state["total_steps"] + step) / (
                    train_state["total_epochs"] * train_state["total_steps"]
                )
                loss = max(0.1, 2.5 - progress * 1.5 + random.uniform(-0.2, 0.2))
                loss = round(loss, 4)

                log_line = f"[{train_state['start_time'] + (epoch - 1) * 10 + step * 0.1:.1f}s] Epoch {epoch}/{train_state['total_epochs']} | Step {step}/{train_state['total_steps']} | Loss: {loss:.4f} | LR: 2.00e-05"
                train_state["logs"].append(log_line)
                train_state["loss_history"].append({"step": step, "loss": loss, "epoch": epoch})
                time.sleep(0.05)

        train_state["status"] = "completed"


@router.get("/status")
async def get_status() -> Dict:
    return {
        "status": train_state["status"],
        "current_epoch": train_state["current_epoch"],
        "current_step": train_state["current_step"],
        "total_epochs": train_state["total_epochs"],
        "total_steps": train_state["total_steps"],
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
async def start_training(total_epochs: int = 1, total_steps: int = 100):
    if train_state["status"] == "running":
        raise HTTPException(status_code=400, detail="训练正在进行中")

    train_state["status"] = "running"
    train_state["start_time"] = int(time.time())
    train_state["current_epoch"] = 0
    train_state["current_step"] = 0
    train_state["total_epochs"] = total_epochs
    train_state["total_steps"] = total_steps
    train_state["logs"] = []
    train_state["loss_history"] = []

    thread = threading.Thread(target=generate_mock_logs, daemon=True)
    thread.start()

    return {"message": "训练已启动", "status": "running"}


@router.post("/stop")
async def stop_training():
    train_state["status"] = "idle"
    return {"message": "训练已停止", "status": "idle"}