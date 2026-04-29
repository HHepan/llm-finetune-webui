from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio

from app.services import file_service

from app.services.rwkv_inference import get_inference_manager

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    message: str
    messages: List[ChatMessage] = []
    params: Dict[str, Any] = {}


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    流式对话接口
    
    请求体:
    - model: 模型路径 (如 "20260414/checkpoint-1000.pth" 或 "20260414/checkpoint-1000.pth|session")
    - message: 当前用户消息
    - messages: 对话历史
    - params: 推理参数
    
    响应: SSE 流式 (text/event-stream)
    """
    try:
        model_path = request.model
        # 解析 model|session 格式
        if '|' in model_path:
            model_path, session = model_path.split('|', 1)
        else:
            session = ''

        parts = model_path.split('/')
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid model path")

        folder = parts[0]
        model_file = parts[1]
        model_file_without_ext = model_file.replace('.pth', '')

        checkpoint_path = f"/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/checkpoints/{folder}/{model_file_without_ext}"

        manager = get_inference_manager()
        manager.load_model(checkpoint_path, session=session)

        all_messages = request.messages + [{"role": "user", "content": request.message}]
        prompt = manager.build_prompt(all_messages)

        queue = asyncio.Queue()
        stop_event = asyncio.Event()

        def sync_callback(token: str, perplexity: float = None):
            print(f"[CHAT API] Sending token to queue: {token}")

            temp_file_path = f"/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/checkpoints/{folder}/chat-data/temp.txt"
            with open(temp_file_path, 'a', encoding='utf-8') as f:
                f.write(token)

            queue.put_nowait((token, perplexity))

        def run_generation():
            try:
                temp_file_path = f"/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/checkpoints/{folder}/chat-data/temp.txt"
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    pass

                print(f"[CHAT API] Starting generation, prompt: {prompt[:100]}...")
                manager.generate(
                    prompt=prompt,
                    callback=sync_callback,
                    folder=folder,
                    model_name=model_file_without_ext,
                    session=session
                )
                print("[CHAT API] Generation completed")
            except Exception as e:
                print(f"[CHAT API] Generation error: {e}")
                queue.put_nowait(("__error__", str(e)))
            finally:
                print("[CHAT API] Setting stop event")
                stop_event.set()

        import threading
        gen_thread = threading.Thread(target=run_generation)
        gen_thread.start()

        while not stop_event.is_set() or not queue.empty():
            try:
                token, perplexity = await asyncio.wait_for(queue.get(), timeout=0.1)
                print(f"[CHAT API] Got token from queue: {token}")
                if token == "__error__":
                    error_data = json.dumps({"error": perplexity}, ensure_ascii=False)
                    yield f"data: {error_data}\n\n"
                    break
                data_str = json.dumps({"content": token}, ensure_ascii=False)
                data_str = data_str.strip('"')
                print(f"[CHAT API] Token: {token}")
                print(f"[CHAT API] Data string before yield: {data_str}")
                print(f"[CHAT API] Yielding data: data: {data_str}\\n\\n")
                yield f'data: {data_str}\n\n'
            except asyncio.TimeoutError:
                continue

        # 先保存对话内容，再发送完成标记
        full_response = manager.get_last_response()
        if full_response:
            all_messages = request.messages + [
                ChatMessage(role="user", content=request.message),
                ChatMessage(role="assistant", content=full_response)
            ]
            dialogue_content = [{"role": m.role, "content": m.content} for m in all_messages]
            try:
                file_service.update_dialogue_content(folder, model_file_without_ext, session, dialogue_content)
                print(f"[CHAT API] Dialogue saved to chat-data file")
            except Exception as e:
                print(f"[CHAT API] Failed to save dialogue: {e}")

        yield "data: [FINAL]\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpdateParamsRequest(BaseModel):
    params: Dict[str, Any]


@router.put("/update-params")
async def update_params(request: UpdateParamsRequest):
    """热更新推理参数"""
    try:
        manager = get_inference_manager()
        manager.current_params = request.params
        print(f"[CHAT API] Params updated: {request.params}")
        return {"message": "参数已更新", "params": request.params}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preload-model")
async def preload_model(model: str = Query(...), session: str = Query(default="")):
    """预加载模型"""
    try:
        # 解析 model|session 格式
        if '|' in model:
            model_path, session = model.split('|', 1)
        else:
            model_path = model
            session = session or ''

        parts = model_path.split('/')
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid model path")

        folder = parts[0]
        model_file = parts[1]
        model_file_without_ext = model_file.replace('.pth', '')

        checkpoint_path = f"/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/checkpoints/{folder}/{model_file_without_ext}"

        manager = get_inference_manager()
        manager.load_model(checkpoint_path, session=session)

        print(f"[CHAT API] Model preloaded: {model_path}, session: {session}")
        return {"message": "模型加载成功", "model": model_path, "session": session}
    except Exception as e:
        print(f"[CHAT API] Failed to preload model: {e}")
        raise HTTPException(status_code=500, detail=str(e))
