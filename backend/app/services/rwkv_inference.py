import os
import gc
import json
import copy
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
from .rwkv_utils_patch import PIPELINE, PIPELINE_ARGS

CHECKPOINT_DIR = Path("/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/checkpoints")
BASE_MODELS_DIR = Path("/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/base_models")
VOCAB_PATH = "/home/lijiahao/MachineLr/hepan/llm-finetune-webui/workspace/tools/RWKV-PEFT/json2binidx_tool/rwkv_vocab_v20230424.txt"

# 推理参数默认值 —— 对齐 RWKV-Runner 的 TextRWKV：
#   temperature=1, top_p=0.3, top_k=0
#   alpha_presence=0, alpha_frequency=1, alpha_decay=0.996
#   newline_adj=0（Runner 默认不加权，仅在特定场景调）
DEFAULT_PARAMS = {
    "max_tokens": 2048,
    "clean_rounds": 10,
    "temperature": 1.0,
    "top_p": 0.3,
    "top_k": 0,
    "alpha_frequency": 1.0,
    "alpha_presence": 0.0,
    "alpha_decay": 0.996,
    "newline_adj": 0,
    "global_penalty": False,
    "presystem": True,      # 是否注入示范对话前缀（对齐 Runner 的 __preload）
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
        self.current_params = DEFAULT_PARAMS.copy()
        self._session_states: Dict[str, Dict] = {}  # session_key -> {state, occurrence, checkpoint_state, checkpoint_occurrence, round_count, fed_text}

    def _get_session_data(self, session_key: str) -> Dict:
        """获取指定 session 的状态数据，不存在则自动初始化"""
        if session_key not in self._session_states:
            self._session_states[session_key] = {
                'state': None,
                'occurrence': None,
                'checkpoint_state': None,
                'checkpoint_occurrence': None,
                'fed_text': '',      # state 中已经"吃进去"的完整文本，用于增量 prefill
                'checkpoint_fed_text': '',
                'round_count': 0,
            }
        return self._session_states[session_key]

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
        # 模型权重变了，所有 session 的状态全部失效
        self._session_states.clear()

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

    def build_prompt(self, messages: list, thinking_mode: bool = False) -> str:
        """构建 prompt，包含角色卡和对话历史

        RWKV-7 G1x 模板格式:
            System: 角色卡定义（可选）

            User: 消息

            Assistant: 回复

            User: 消息

            Assistant:

        滑动窗口：保留最近 N 轮对话（从 current_params.max_rounds 读取），角色卡始终保留。

        若 thinking_mode=True，则在末尾 "Assistant:" 后追加 " thinking"，触发模型输出推理过程。
        """
        prompt = ""

        # 1. 提取 system 角色卡（始终保留）
        system_content = None
        if messages and (messages[0].get("role") if isinstance(messages[0], dict) else messages[0].role) == "system":
            system_content = messages[0].get("content") if isinstance(messages[0], dict) else messages[0].content
            messages = messages[1:]  # 从对话中移除，后面单独追加

        # 2. 滑动窗口
        # RWKV 是循环模型，state 已经累积了完整历史，因此「滑动窗口裁掉早期对话」
        # 反而会破坏 state 与 prompt 的一致性：prompt 开头每轮都在变，增量 prefill
        # 完全失效（只能复用 2 个 token），且模型会"遗忘"被裁掉的内容。
        # 默认关闭裁剪；仍可通过 params.max_rounds 显式开启（设为 >0 的整数）。
        max_rounds = self.current_params.get("max_rounds", 0)
        if max_rounds and max_rounds > 0:
            max_messages = max_rounds * 2 + 1  # max_rounds 个完整轮次 + 当前用户消息
            if len(messages) > max_messages:
                print(f"[RWKV] Sliding window: {len(messages)} messages > {max_messages}, trimming to {max_rounds} rounds")
                messages = messages[-max_messages:]

        # 3. 构建 prompt
        #    ── 预设对话注入（对齐 RWKV-Runner 的 __preload）──
        #    Runner 在模型加载时先用一段示范对话喂一遍 state，让模型进入
        #    「详细、专业地回答」的模式。这里作为 prompt 前缀做等价效果。
        #    可用 params.presystem=False 关闭。
        if self.current_params.get("presystem", True):
            prompt += (
                "User: hi\n\n"
                "Assistant: Hi. I am your assistant and I will provide expert full response "
                "in full details. Please feel free to ask any question and I will always answer it.\n\n"
            )

        if system_content:
            prompt += f"System: {system_content}\n\n"

        for i, msg in enumerate(messages):
            raw_role = msg.get("role") if isinstance(msg, dict) else msg.role
            content = msg.get("content") if isinstance(msg, dict) else msg.content
            thinking = msg.get("thinking") if isinstance(msg, dict) else getattr(msg, "thinking", "")
            role = "User" if raw_role == "user" else "Assistant"

            # ★ 关键：thinking 模式下，assistant 的历史回复必须还原成
            #   " thinking<思考内容></think><正式回答>" 的完整形式。
            #   否则 state 里存着带 think 的 token 序列，而 prompt 里只有正式回答，
            #   两者前缀失配 —— 不仅增量 prefill 失效，模型看到的对话历史也会
            #   与它自己生成过的内容不一致，导致后续推理质量下降。
            if role == "Assistant" and thinking:
                content = f"<think>\n{thinking}\n</think>\n{content}"

            prompt += f"{role}: {content}\n\n"

        # 4. 最后以 Assistant: 结尾，触发模型回复
        prompt += "Assistant: "   # 注意尾随空格：Runner 为 f"{bot}{interface} "
        if thinking_mode:
            prompt += "<think>"
        return prompt

    def _token_prefix_chars(self, text: str, n_tok: int) -> int:
        """返回 text 中前 n_tok 个 token 对应的字符数（在 token 边界处截断）。"""
        try:
            tok = self.tokenizer
            # 逐步扩大字符窗口直到 token 数达到 n_tok，避免切在多字节字符中间
            lo, hi = 0, len(text) + 1
            while lo < hi:
                mid = (lo + hi) // 2
                if len(tok.encode(text[:mid])) <= n_tok:
                    lo = mid + 1
                else:
                    hi = mid
            return max(0, lo - 1)
        except Exception:
            return 0

    def generate(self, prompt: str, callback: Callable[[str, Optional[float]], None], folder: str = None, model_name: str = None, session: str = ''):
        """流式生成回复"""
        if self.model is None:
            raise RuntimeError("Model not loaded. Please call load_model first.")

        print(f"[RWKV] Starting generation with prompt: {prompt[:100]}...")

        # 取当前 session 的状态数据
        session_key = session or 'default'
        sd = self._get_session_data(session_key)

        # ── 增量 prefill ─────────────────────────────────────────────────
        # state 里已经"吃进去"了 fed_text。若本轮 prompt 与 fed_text 共享前缀，
        # 只需喂差量，避免每轮重复计算全部历史（O(n²) -> O(n)）。
        # 关键：必须在 **token 层面** 对齐，按字符切会切进 UTF-8 多字节字符中间，
        # 导致 decode 抛 UnicodeDecodeError，且 token 序列会错位。
        fed = sd.get('fed_text') or ''
        full_tokens = self.tokenizer.encode(prompt)
        feed_tokens = full_tokens      # 真正喂给模型的 token
        base_chars = 0                 # 被复用的字符数（仅用于日志/记录）

        if sd['state'] is not None and fed:
            fed_tokens = self.tokenizer.encode(fed)

            # 求 token 级最长公共前缀
            k = 0
            lim = min(len(fed_tokens), len(full_tokens))
            while k < lim and fed_tokens[k] == full_tokens[k]:
                k += 1

            if k > 0:
                feed_tokens = full_tokens[k:]
                # 记录公共 token 前缀对应的文本（用于下一轮 fed_text）
                base_chars = self._token_prefix_chars(fed, k)
                print(f"[RWKV] Incremental prefill: reuse {k} tok, feed {len(feed_tokens)} tok")
            else:
                print(f"[RWKV] No common token prefix, full rebuild")
                sd['state'] = None
        else:
            if sd['state'] is not None:
                print(f"[RWKV] No fed_text baseline, full rebuild")
            sd['state'] = None

        if sd['state'] is None:
            feed_tokens = full_tokens
            base_chars = 0

        # 保存检查点——深拷贝当前 state（occurrence 每轮重置，无需备份）
        sd['checkpoint_state'] = copy.deepcopy(sd['state'])
        sd['checkpoint_occurrence'] = copy.deepcopy(sd['occurrence'])
        sd['checkpoint_fed_text'] = fed[:base_chars] if sd['state'] is not None else ''

        # 如果有session，重新加载对应参数
        if session and folder and model_name:
            self.current_params = self.load_params_from_json(folder, model_name, session)

        params = self.current_params
        print(f"[RWKV] Using params: {params}")

        pipeline_args = PIPELINE_ARGS(
            temperature=params.get("temperature", 1.0),
            top_p=params.get("top_p", 0.3),
            top_k=params.get("top_k", 0),
            alpha_frequency=params.get("alpha_frequency", 1.0),
            alpha_presence=params.get("alpha_presence", 0.0),
            alpha_decay=params.get("alpha_decay", 0.996),
            token_stop=[0],
        )
        # Runner 的额外运行时机制
        pipeline_args.newline_adj = params.get("newline_adj", 0)
        pipeline_args.global_penalty = params.get("global_penalty", False)

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
            raw_out, new_state, _ = self.pipeline.generate(
                feed_tokens,
                token_count=max_tokens,
                args=pipeline_args,
                callback=my_print,
                state=sd['state'],
                occurrence=None  # occurrence 每轮重置，防止跨轮惩罚过载
            )
            sd['state'] = new_state
            sd['occurrence'] = None  # 重置 occurrence，确保下轮从空开始
            # 记录 state 中已吃进的完整文本：复用前缀 + 本轮 prompt 全部 + 模型原始输出
            sd['fed_text'] = fed[:base_chars] + prompt[base_chars:] + (raw_out or '')
        except StopIteration:
            pass
        finally:
            if not stop_detected[0]:
                for char in pending_chars:
                    if char != '\n' or output:
                        output.append(char)
                        callback(char, None)
            pending_chars.clear()

        sd['round_count'] += 1

        if sd['round_count'] % clean_rounds == 0:
            print(f"[RWKV] Clean rounds reached ({clean_rounds}) for session '{session_key}', cleaning memory...")
            gc.collect()
            torch.cuda.empty_cache()

        self.last_response = "".join(output)
        return self.last_response, is_truncated[0]

    def get_last_response(self) -> str:
        return getattr(self, 'last_response', '')

    def rollback(self, session: str = ''):
        """回滚到上一个检查点（重生成时使用，让模型忘记上一轮的回答）"""
        session_key = session or 'default'
        sd = self._get_session_data(session_key)
        sd['state'] = sd['checkpoint_state']
        sd['fed_text'] = sd.get('checkpoint_fed_text', '')
        print(f"[RWKV] Rolled back checkpoint for session '{session_key}': has_state={sd['state'] is not None}, fed={len(sd['fed_text'])} chars")

    def reset_state(self, session: str = ''):
        """重置模型状态（清空对话时使用，让模型彻底忘记所有历史）"""
        session_key = session or 'default'
        if session_key in self._session_states:
            del self._session_states[session_key]
        print(f"[RWKV] State fully reset for session '{session_key}'")


_manager = RWKVInferenceManager()


def get_inference_manager() -> RWKVInferenceManager:
    return _manager
