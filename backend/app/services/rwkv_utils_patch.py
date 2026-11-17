########################################################################################################
# The RWKV Language Model - https://github.com/BlinkDL/RWKV-LM
########################################################################################################
# 此文件为 rwkv/utils.py 的补丁版本，在项目本地维护。
# 修改点：
#   1. generate() 返回 (out_str, state, occurrence) 而非仅 out_str
#   2. generate() 接受 occurrence 参数，支持跨轮次重复惩罚
#   3. callback 抛 StopIteration 时仍返回当前 state/occurrence
# 路径适配：通过 import rwkv 定位 site-packages 中的 rwkv 目录，从而找到 tokenizer 与词表
########################################################################################################

import os, sys
import numpy as np
import torch
from torch.nn import functional as F

# 定位 site-packages 中的 rwkv 目录，保证 tokenizer 和词表文件可以被找到
import rwkv
_RWKV_DIR = os.path.dirname(rwkv.__file__)
if _RWKV_DIR not in sys.path:
    sys.path.insert(0, _RWKV_DIR)

# 以下 tokenizer 和词表路径均通过 _RWKV_DIR 定位，不依赖 __file__ 位置
from rwkv_tokenizer import TRIE_TOKENIZER
_VOCAB_PATH = os.path.join(_RWKV_DIR, 'rwkv_vocab_v20230424.txt')


class PIPELINE_ARGS():
    # 默认值对齐 RWKV-Runner 的 TextRWKV 实现：
    #   temperature=1, top_p=0.3, top_k=0
    #   alpha_presence=0, alpha_frequency=1, alpha_decay=0.996
    # 说明：presence=0 表示「不惩罚首次出现的 token」，frequency=1 表示
    # 「高频重复的 token 才重罚」。这样模型的用词不会被过早压制，表达更自然。
    def __init__(self, temperature=1.0, top_p=0.3, top_k=0, alpha_frequency=1.0, alpha_presence=0.0, alpha_decay=0.996, token_ban=[], token_stop=[], chunk_len=256):
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.alpha_frequency = alpha_frequency  # Frequency Penalty (as in GPT-3)
        self.alpha_presence = alpha_presence  # Presence Penalty (as in GPT-3)
        self.alpha_decay = alpha_decay  # gradually decay the penalty
        self.token_ban = token_ban  # ban the generation of some tokens
        self.token_stop = token_stop  # stop generation whenever you see any token here
        self.chunk_len = chunk_len  # split input into chunks to save VRAM (shorter -> slower)


# ── 对齐 RWKV-Runner 的 token 级别约束 ────────────────────────────────────
# END_OF_LINE: v7/World 词表里 "\n" 的 token id，用于 newline_adj 调整换行概率
END_OF_LINE = 11
EOS_ID = 0

# 硬禁止连续重复的标点（上一个 token 是这些之一时，禁止再次生成同一个）
_AVOID_REPEAT_CHARS = "，：？！"
# 这些 token 不参与重复惩罚统计（标点/空白/数字本身就该高频出现）
_AVOID_PENALTY_CHARS = '\n,.:?!，。：？！"“”<>[]{}/\\|;；~`@#$%^&*()_+-=0123456789 '


def _build_token_sets(tokenizer):
    """按 Runner 的规则构建 AVOID_REPEAT / AVOID_PENALTY 两个 token id 集合。"""
    avoid_repeat, avoid_penalty = set(), set()
    for ch in _AVOID_REPEAT_CHARS:
        ids = tokenizer.encode(ch)
        if len(ids) == 1:
            avoid_repeat.add(ids[0])
    for ch in _AVOID_PENALTY_CHARS:
        ids = tokenizer.encode(ch)
        if len(ids) == 1:
            avoid_penalty.add(ids[0])
    return avoid_repeat, avoid_penalty



class PIPELINE():
    def __init__(self, model, WORD_NAME):
        self.model = model
        if WORD_NAME == 'cl100k_base':
            import tiktoken
            self.tokenizer = tiktoken.get_encoding(WORD_NAME)
        elif WORD_NAME == 'rwkv_vocab_v20230424':
            self.tokenizer = TRIE_TOKENIZER(_VOCAB_PATH)
        else:
            from tokenizers import Tokenizer
            self.tokenizer = Tokenizer.from_file(WORD_NAME)

    def refine_context(self, context):
        context = context.strip().split('\n')
        for c in range(len(context)):
            context[c] = context[c].strip().strip('\u3000').strip('\r')
        context = list(filter(lambda c: c != '', context))
        context = '\n' + ('\n'.join(context)).strip()
        if context == '':
            context = '\n'
        return context

    def encode(self, x):
        if 'Tokenizer' in str(type(self.tokenizer)):
            return self.tokenizer.encode(x).ids
        else:
            return self.tokenizer.encode(x)

    def decode(self, x):
        return self.tokenizer.decode(x)

    def sample_logits(self, logits, temperature=1.0, top_p=0.85, top_k=0):
        if temperature == 0:
            temperature = 1.0
            top_p = 0
        probs = F.softmax(logits.float(), dim=-1)
        top_k = int(top_k)
        # 'privateuseone' is the type of custom devices like `torch_directml.device()`
        if probs.device.type in ['cpu', 'privateuseone']:
            probs = probs.cpu().numpy()
            sorted_ids = np.argsort(probs)
            sorted_probs = probs[sorted_ids][::-1]
            cumulative_probs = np.cumsum(sorted_probs)
            cutoff = float(sorted_probs[np.argmax(cumulative_probs >= top_p)])
            probs[probs < cutoff] = 0
            if top_k < len(probs) and top_k > 0:
                probs[sorted_ids[:-top_k]] = 0
            if temperature != 1.0:
                probs = probs ** (1.0 / temperature)
            probs = probs / np.sum(probs)
            out = np.random.choice(a=len(probs), p=probs)
            return int(out)
        else:
            sorted_ids = torch.argsort(probs)
            sorted_probs = probs[sorted_ids]
            sorted_probs = torch.flip(sorted_probs, dims=(0,))
            cumulative_probs = torch.cumsum(sorted_probs, dim=-1).cpu().numpy()
            cutoff = float(sorted_probs[np.argmax(cumulative_probs >= top_p)])
            probs[probs < cutoff] = 0
            if top_k < len(probs) and top_k > 0:
                probs[sorted_ids[:-top_k]] = 0
            if temperature != 1.0:
                probs = probs ** (1.0 / temperature)
            out = torch.multinomial(probs, num_samples=1)[0]
            return int(out)

    def generate(self, ctx, token_count=100, args=PIPELINE_ARGS(), callback=None, state=None, occurrence=None):
        """流式生成。行为对齐 RWKV-Runner 的 TextRWKV.generate：

        1. newline_adj       —— 每次 forward 后调整换行 token 的概率
        2. AVOID_REPEAT      —— 若上个 token 是「，：？！」，硬禁止连续重复
        3. AVOID_PENALTY     —— 标点/空白/数字不参与重复惩罚统计
        """
        all_tokens = []
        out_last = 0
        out_str = ''
        if occurrence is None:
            occurrence = {}

        # 懒构建 token 集合（依赖具体 tokenizer，只需算一次）
        if not hasattr(self, '_avoid_repeat_tokens'):
            self._avoid_repeat_tokens, self._avoid_penalty_tokens = _build_token_sets(self.tokenizer)

        # 历史 prompt 的 token（用于 global_penalty：incremental prefill 时仅含新增部分）
        ctx_tokens = ctx if isinstance(ctx, (list, tuple)) else self.encode(ctx)

        for i in range(token_count):

            # forward & adjust prob.
            # 支持传入已 tokenize 的 list，便于做增量 prefill（省去重复 encode）
            if i == 0:
                tokens = ctx_tokens
            else:
                tokens = [token]
            while len(tokens) > 0:
                out, state = self.model.forward(tokens[:args.chunk_len], state)
                tokens = tokens[args.chunk_len:]

            for n in args.token_ban:
                out[n] = -float('inf')

            # ── global_penalty：把 prompt 里出现过的 token 计入惩罚（跳过标点/数字/空白）
            # 对齐 Runner 的 adjust_forward_logits(i==0 分支)
            if getattr(args, 'global_penalty', False) and i == 0:
                for tk in ctx_tokens:
                    tk = int(tk)
                    if tk not in self._avoid_penalty_tokens:
                        if tk not in occurrence:
                            occurrence[tk] = 1
                        else:
                            occurrence[tk] += 1

            for n in occurrence:
                out[n] -= (args.alpha_presence + occurrence[n] * args.alpha_frequency)

            # ── newline_adj：调整换行概率（Runner: out[END_OF_LINE] += newline_adj）
            newline_adj = getattr(args, 'newline_adj', 0)
            if newline_adj:
                out[END_OF_LINE] += newline_adj

            # ── AVOID_REPEAT：禁止连续重复的中文标点
            # 对齐 Runner 的 run_rnn：if last_token in AVOID_REPEAT: out[last] = -inf
            if len(all_tokens) > 0 and all_tokens[-1] in self._avoid_repeat_tokens:
                last = all_tokens[-1]
                try:
                    out[last] = -999999999
                except (IndexError, RuntimeError):
                    out[last] = -65504

            # sampler
            token = self.sample_logits(out, temperature=args.temperature, top_p=args.top_p, top_k=args.top_k)
            if token in args.token_stop:
                break
            all_tokens += [token]
            for xxx in occurrence:
                occurrence[xxx] *= args.alpha_decay

            ttt = self.decode([token])
            www = 1
            if ttt in ' \t0123456789':
                www = 0
            if token not in occurrence:
                occurrence[token] = www
            else:
                occurrence[token] += www

            # output
            tmp = self.decode(all_tokens[out_last:])
            if '\ufffd' not in tmp:  # is valid utf-8 string?
                if callback:
                    try:
                        callback(tmp)
                    except StopIteration:
                        # callback 提前终止时，仍然返回当前的 state 和 occurrence
                        return out_str, state, occurrence
                out_str += tmp
                out_last = i + 1
        return out_str, state, occurrence