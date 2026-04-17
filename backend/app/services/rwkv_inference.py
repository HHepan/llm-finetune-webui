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
from rwkv.model import RWKV
from rwkv.utils import PIPELINE, PIPELINE_ARGS

CHECKPOINT_DIR = Path("/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/checkpoints")
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

    def load_model(self, model_path: str):
        """加载或切换模型"""
        if self.current_model_path == model_path and self.model is not None:
            return

        print(f"[RWKV] Loading model: {model_path}")

        if self.model is not None:
            self.unload_model()

        print("[RWKV] Loading RWKV model...")
        self.model = RWKV(model=model_path, strategy='cuda fp16')

        print("[RWKV] Loading tokenizer...")
        self.tokenizer = RWKV_TOKENIZER(VOCAB_PATH)
        self.pipeline = PIPELINE(self.model, "rwkv_vocab_v20230424")

        self.current_model_path = model_path
        self.round_count = 0
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

    def load_params_from_json(self, folder: str, model_name: str) -> Dict[str, Any]:
        """从 json 文件加载推理参数"""
        json_file = CHECKPOINT_DIR / folder / "chat-data" / f"{model_name}-data.json"
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('params', DEFAULT_PARAMS.copy())
        return DEFAULT_PARAMS.copy()

    def build_prompt(self, messages: list) -> str:
        """构建 prompt，包含对话历史"""
        prompt = ""
        for msg in messages:
            role = "User" if (msg.get("role") if isinstance(msg, dict) else msg.role) == "user" else "Assistant"
            content = msg.get("content") if isinstance(msg, dict) else msg.content
            prompt += f"{role}: {content}\n\nAssistant: "
        return prompt

    def generate(self, prompt: str, callback: Callable[[str, Optional[float]], None], folder: str = None, model_name: str = None):
        """流式生成回复"""
        if self.model is None:
            raise RuntimeError("Model not loaded. Please call load_model first.")

        print(f"[RWKV] Starting generation with prompt: {prompt[:100]}...")

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

        def my_print(s):
            if s == '\n\n':
                is_truncated[0] = True
                raise StopIteration
            if s == '\n':
                is_truncated[0] = True
                raise StopIteration

            s = s.rstrip('\n')
            if not s:
                return

            output.append(s)
            print(f"[RWKV] Generated token: {s}")
            callback(s, None)

        try:
            self.pipeline.generate(
                prompt,
                token_count=max_tokens,
                args=pipeline_args,
                callback=my_print,
                state=None
            )
        except StopIteration:
            pass

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
