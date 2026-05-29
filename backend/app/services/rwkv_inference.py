import os
import gc
import json
from typing import Dict, Any, Callable, Optional
from pathlib import Path

os.environ["RWKV_V7_ON"] = '1'
os.environ['RWKV_JIT_ON'] = '1'
os.environ["RWKV_CUDA_ON"] = '1'

import sys
sys.path.append("/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/tools/RWKV-PEFT/json2binidx_tool/tools")
from rwkv_tokenizer import RWKV_TOKENIZER

import torch
from .rwkv_x070_dual import RWKV_x070_Dual
from rwkv.utils import PIPELINE, PIPELINE_ARGS

CHECKPOINT_DIR = Path("/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/checkpoints")
BASE_MODELS_DIR = Path("/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/base_models")
VOCAB_PATH = "/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/tools/RWKV-PEFT/json2binidx_tool/rwkv_vocab_v20230424.txt"

DEFAULT_PARAMS = {
    "max_tokens": 2048,
    "clean_rounds": 10,
    "temperature": 1.0,
    "top_p": 0.85,
    "top_k": 0,
    "alpha_frequency": 0.2,
    "alpha_presence": 0.2,
    "alpha_decay": 0.996
}


class RWKVInferenceManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.current_model_path = None
        self.round_count = 0
        self.current_params = DEFAULT_PARAMS.copy()
        self.last_state = None
        self.last_occurrence = None

    def load_model(self, model_path: str, session: str = ''):
        """加载或切换模型"""
        # 如果模型已加载且session相同，则不需要重新加载
        if self.current_model_path == model_path and self.model is not None:
            # 更新参数（可能session不同）
            if session:
                parts = model_path.split('/')
                if len(parts) >= 2:
                    folder = parts[0]
                    model_name = parts[1].replace('.pth', '')
                    self.current_params = self.load_params_from_json(folder, model_name, session)
            return

        print(f"[RWKV] Loading model: {model_path}")

        if self.model is not None:
            self.unload_model()

        print("[RWKV] Loading RWKV model...")
        import gc
        gc.collect()
        torch.cuda.empty_cache()
        self.model = RWKV_x070_Dual(model=model_path, strategy='cuda:0 fp16 -> cuda:1 fp16')

        print("[RWKV] Loading tokenizer...")
        self.tokenizer = RWKV_TOKENIZER(VOCAB_PATH)
        self.pipeline = PIPELINE(self.model, "rwkv_vocab_v20230424")

        self.current_model_path = model_path
        self.round_count = 0
        self.last_state = None
        self.last_occurrence = None

        # 加载对应的参数
        if session:
            parts = model_path.split('/')
            if len(parts) >= 2:
                folder = parts[0]
                model_name = parts[1].replace('.pth', '')
                self.current_params = self.load_params_from_json(folder, model_name, session)

        print(f"[RWKV] Model loaded successfully")

    def unload_model(self):
        """卸载模型，释放显存"""
        if self.model is not None:
            print("[RWKV] Unloading model...")
            del self.model
            del self.tokenizer
            del self.pipeline
            self.model = None
            self.tokenizer = None
            self.pipeline = None
            self.current_model_path = None
            gc.collect()
            torch.cuda.empty_cache()
            print("[RWKV] Model unloaded, memory cleaned")

    def load_params_from_json(self, folder: str, model_name: str, session: str = '') -> Dict[str, Any]:
        """从 json 文件加载推理参数"""
        if folder == "base_models":
            chat_data_dir = BASE_MODELS_DIR / "chat-data"
        else:
            chat_data_dir = CHECKPOINT_DIR / folder / "chat-data"
        if session:
            json_file = chat_data_dir / f"{model_name}-{session}-data.json"
        else:
            json_file = chat_data_dir / f"{model_name}-data.json"
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('params', DEFAULT_PARAMS.copy())
        return DEFAULT_PARAMS.copy()

    def build_prompt(self, messages: list) -> str:
        """构建 prompt，包含角色卡和对话历史

        RWKV-7 G1x 模板格式:
            System: 角色卡定义（可选）

            User: 消息

            Assistant: 回复

            User: 消息

            Assistant:

        滑动窗口：保留最近 N 轮对话（从 current_params.max_rounds 读取），角色卡始终保留。
        """
        prompt = ""

        # 1. 提取 system 角色卡（始终保留）
        system_content = None
        if messages and (messages[0].get("role") if isinstance(messages[0], dict) else messages[0].role) == "system":
            system_content = messages[0].get("content") if isinstance(messages[0], dict) else messages[0].content
            messages = messages[1:]  # 从对话中移除，后面单独追加

        # 2. 滑动窗口：从 current_params 读取最大保留轮数
        max_rounds = self.current_params.get("max_rounds", 15)
        max_messages = max_rounds * 2 + 1  # max_rounds 个完整轮次 + 当前用户消息
        if len(messages) > max_messages:
            print(f"[RWKV] Sliding window: {len(messages)} messages > {max_messages}, trimming to {max_rounds} rounds")
            messages = messages[-max_messages:]

        # 3. 构建 prompt
        if system_content:
            prompt += f"System: {system_content}\n\n"

        for i, msg in enumerate(messages):
            raw_role = msg.get("role") if isinstance(msg, dict) else msg.role
            content = msg.get("content") if isinstance(msg, dict) else msg.content
            role = "User" if raw_role == "user" else "Assistant"
            prompt += f"{role}: {content}\n\n"

        # 4. 最后以 Assistant: 结尾，触发模型回复
        prompt += "Assistant:"
        return prompt

    def generate(self, prompt: str, callback: Callable[[str, Optional[float]], None], folder: str = None, model_name: str = None, session: str = ''):
        """流式生成回复"""
        if self.model is None:
            raise RuntimeError("Model not loaded. Please call load_model first.")

        print(f"[RWKV] Starting generation with prompt: {prompt[:100]}...")

        # 如果有session，重新加载对应参数
        if session and folder and model_name:
            self.current_params = self.load_params_from_json(folder, model_name, session)

        params = self.current_params
        print(f"[RWKV] Using params: {params}")

        pipeline_args = PIPELINE_ARGS(
            temperature=params.get("temperature", 1.0),
            top_p=params.get("top_p", 0.85),
            top_k=params.get("top_k", 0),
            alpha_frequency=params.get("alpha_frequency", 0.2),
            alpha_presence=params.get("alpha_presence", 0.2),
            alpha_decay=params.get("alpha_decay", 0.996),
            token_stop=[0],
        )

        max_tokens = params.get("max_tokens", 2048)
        clean_rounds = params.get("clean_rounds", 10)

        output = []
        is_truncated = [False]
        stop_sequences = ["\n\nUser:", "\nAssistant:", "\n\nAssistant:", "\n\n\nAssistant:", "\nAss", "\n\nAss", "\n\n\nAss"]
        stop_detected = [False]
        pending_chars = []

        def my_print(s):
            if stop_detected[0]:
                return

            pending_chars.append(s)

            full_text = ''.join(pending_chars)

            for seq in stop_sequences:
                if seq in full_text:
                    is_truncated[0] = True
                    pos = full_text.find(seq)
                    for i in range(pos):
                        char = pending_chars[i]
                        if char != '\n' or output:
                            output.append(char)
                            callback(char, None)
                    stop_detected[0] = True
                    pending_chars.clear()
                    raise StopIteration

            if len(pending_chars) >= 10:
                char = pending_chars.pop(0)
                if char != '\n' or output:
                    output.append(char)
                    callback(char, None)

        try:
            _, self.last_state, self.last_occurrence = self.pipeline.generate(
                prompt,
                token_count=max_tokens,
                args=pipeline_args,
                callback=my_print,
                state=self.last_state,
                occurrence=self.last_occurrence
            )
        except StopIteration:
            pass
        finally:
            if not stop_detected[0]:
                for char in pending_chars:
                    if char != '\n' or output:
                        output.append(char)
                        callback(char, None)
            pending_chars.clear()

        self.round_count += 1

        if self.round_count % clean_rounds == 0:
            print(f"[RWKV] Clean rounds reached ({clean_rounds}), cleaning memory...")
            gc.collect()
            torch.cuda.empty_cache()

        self.last_response = "".join(output)
        return self.last_response, is_truncated[0]

    def get_last_response(self) -> str:
        return getattr(self, 'last_response', '')


_manager = RWKVInferenceManager()


def get_inference_manager() -> RWKVInferenceManager:
    return _manager
RWKVInferenceManager()


def get_inference_manager() -> RWKVInferenceManager:
    return _manager
