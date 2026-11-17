"""
rwkv-fla dual-GPU inference wrapper for RWKV7.
Simple approach: token-by-token forward using model.forward without HF Cache.
No monkey patches needed — we manage the recurrent state ourselves
by using use_cache=True and passing past_key_values between calls.

Note: Requires the following patches to rwkv-fla for transformers 4.57+:
  - rwkvfla/models/utils.py: NewStyleCache.__init__ + append_new_layers + FlashLinearLayer abstract methods
  - rwkvfla/modules/token_shift.py: dummy_cache for None cache
These are applied automatically on first import.
"""

from typing import Callable, Dict, List, Optional, Tuple
import copy
import gc
import torch
import torch.nn.functional as F

from rwkvfla.models.rwkv7 import RWKV7ForCausalLM, RWKV7Config


# ─── Apply compatibility patches ─────────────────────────────────────────

def _apply_patches():
    """Apply monkey patches for transformers 4.57+ compatibility."""
    import rwkvfla.models.utils as fla_utils
    import rwkvfla.modules.token_shift as fla_ts
    from packaging import version

    # Patch NewStyleCache
    if hasattr(fla_utils, 'NewStyleCache'):
        NC = fla_utils.NewStyleCache

        # Fix __init__
        orig_init = NC.__init__
        def patched_init(self, seen_tokens=0, **kwargs):
            from rwkvfla.models.utils import FlashLinearLayer
            try:
                orig_init(self, seen_tokens=seen_tokens, **kwargs)
            except TypeError:
                # transformers >= 4.57
                super(NC, self).__init__(layer_class_to_replicate=FlashLinearLayer, **kwargs)
                self._seen_tokens = int(seen_tokens)
        NC.__init__ = patched_init

        # Backport append_new_layers
        if not hasattr(NC, 'append_new_layers') or 'append_new_layers' not in NC.__dict__:
            def append_new_layers(self, n):
                for _ in range(len(self.layers), n + 1):
                    self.layers.append(self.layer_class_to_replicate())
            NC.append_new_layers = append_new_layers

        # Fill missing abstract methods in FlashLinearLayer
        from rwkvfla.models.utils import FlashLinearLayer
        if not hasattr(FlashLinearLayer, 'lazy_initialization'):
            FlashLinearLayer.lazy_initialization = lambda self: None
        if not hasattr(FlashLinearLayer, 'get_mask_sizes'):
            FlashLinearLayer.get_mask_sizes = lambda self, cp, li: (0, 0)
        if not hasattr(FlashLinearLayer, 'get_max_cache_shape'):
            FlashLinearLayer.get_max_cache_shape = lambda self, li=0: -1
        if not hasattr(FlashLinearLayer, 'get_seq_length'):
            FlashLinearLayer.get_seq_length = lambda self, li=0, cp=None: 0

    # Patch token_shift_fwd for None cache
    orig_fwd = fla_ts.token_shift_fwd
    import triton
    def patched_fwd(x, cu_seqlens=None, cache=None, output_cache=False):
        B, T, D = x.shape
        if cache is None:
            cache = torch.empty(1, D, device=x.device, dtype=x.dtype)
        return orig_fwd(x, cu_seqlens, cache, output_cache)
    fla_ts.token_shift_fwd = patched_fwd


_apply_patches()


# ─── Inference class ─────────────────────────────────────────────────────

class FLAInference:
    """
    Dual-GPU RWKV7 inference using rwkv-fla Triton kernels.

    Token-by-token decode loop using model.forward with past_key_values caching.
    Supports streaming callback, state management (rollback/reset),
    and repetition penalty.

    Model is split: first split_layer layers on GPU 0, rest on GPU 1.
    """

    def __init__(
        self,
        model_dir: str,
        dtype: torch.dtype = torch.float16,
        split_layer: int = 31,
    ):
        self.dtype = dtype

        config = RWKV7Config.from_pretrained(model_dir)
        self.n_layer = config.num_hidden_layers
        self.n_embd = config.hidden_size
        self.n_head = config.num_heads
        self.head_size = config.head_dim
        self.vocab_size = config.vocab_size

        device_map = {"model.embeddings": 0}
        for i in range(self.n_layer):
            device_map[f"model.layers.{i}"] = 0 if i < split_layer else 1
        device_map["model.norm"] = 1
        device_map["lm_head"] = 1

        self.model = RWKV7ForCausalLM.from_pretrained(
            model_dir,
            dtype=dtype,
            device_map=device_map,
        )
        self.model.eval()

        self._sessions: Dict[str, Dict] = {}

    def _get_session(self, key: str) -> Dict:
        if key not in self._sessions:
            self._sessions[key] = {
                "past_key_values": None,
                "checkpoint_pkv": None,
                "occurrence": {},
                "round_count": 0,
            }
        return self._sessions[key]

    @staticmethod
    def _sample_logits(
        logits: torch.Tensor,
        temperature: float = 1.0,
        top_p: float = 0.85,
        top_k: int = 0,
    ) -> int:
        if temperature <= 0:
            temperature = 1.0
            top_p = 0.0
        probs = F.softmax(logits.float(), dim=-1)

        if top_k > 0 and top_k < len(probs):
            topk_vals, topk_idx = torch.topk(probs, top_k)
            probs = torch.zeros_like(probs)
            probs.scatter_(0, topk_idx, topk_vals)

        if top_p > 0 and top_p < 1.0:
            sorted_probs, sorted_idx = torch.sort(probs, descending=True)
            cumsum = torch.cumsum(sorted_probs, dim=-1)
            cutoff_idx = (cumsum >= top_p).nonzero(as_tuple=True)[0]
            if len(cutoff_idx) > 0:
                probs[probs < sorted_probs[cutoff_idx[0]]] = 0.0

        if probs.sum() == 0:
            return torch.argmax(logits).item()

        probs = probs / probs.sum()
        return torch.multinomial(probs, 1).item()

    def generate(
        self,
        prompt: str,
        tokenizer,
        callback: Callable[[str, Optional[float]], None],
        max_tokens: int = 2048,
        temperature: float = 1.0,
        top_p: float = 0.85,
        top_k: int = 0,
        alpha_frequency: float = 0.2,
        alpha_presence: float = 0.2,
        alpha_decay: float = 0.996,
        token_stop: Optional[List[int]] = None,
        session: str = "default",
    ) -> Tuple[str, bool]:
        if token_stop is None:
            token_stop = [0]

        sd = self._get_session(session)

        # Save checkpoint
        sd["checkpoint_pkv"] = copy.deepcopy(sd["past_key_values"])

        # Encode prompt
        tokens = tokenizer.encode(prompt)
        emb_device = str(self.model.model.embeddings.weight.device)

        with torch.no_grad():
            # Prefill: process full prompt, get initial pkv and first logits
            input_ids = torch.tensor([tokens], dtype=torch.long, device=emb_device)
            outputs = self.model(
                input_ids=input_ids,
                past_key_values=sd["past_key_values"],
                use_cache=True,
            )
            pkv = outputs.past_key_values
            logits = outputs.logits[0, -1, :]  # [vocab_size]

        sd["past_key_values"] = pkv

        # Decode loop
        output_tokens: List[int] = []
        out_last = 0
        out_str = ""
        occurrence = sd["occurrence"]
        is_truncated = False

        for step in range(max_tokens):
            # Apply repetition penalty
            for tok_id in list(occurrence.keys()):
                logits[tok_id] -= alpha_presence + occurrence[tok_id] * alpha_frequency
                occurrence[tok_id] *= alpha_decay
                if occurrence[tok_id] < 0.01:
                    del occurrence[tok_id]

            token = self._sample_logits(logits, temperature, top_p, top_k)

            if token in token_stop:
                break

            output_tokens.append(token)

            decoded_char = tokenizer.decode([token])
            weight = 0 if decoded_char in " \t0123456789" else 1
            occurrence[token] = occurrence.get(token, 0) + weight

            # Streaming output
            tmp = tokenizer.decode(output_tokens[out_last:])
            if "\ufffd" not in tmp:
                try:
                    callback(tmp, None)
                except StopIteration:
                    is_truncated = True
                    break
                out_str += tmp
                out_last = step + 1

            if is_truncated:
                break

            # Forward next token
            with torch.no_grad():
                next_id = torch.tensor([[token]], dtype=torch.long, device=emb_device)
                outputs = self.model(
                    input_ids=next_id,
                    past_key_values=pkv,
                    use_cache=True,
                )
                pkv = outputs.past_key_values
                logits = outputs.logits[0, -1, :]

        sd["past_key_values"] = pkv
        sd["occurrence"] = occurrence
        sd["round_count"] += 1

        # Flush remaining
        if not is_truncated and out_last < len(output_tokens):
            tmp = tokenizer.decode(output_tokens[out_last:])
            if "\ufffd" not in tmp and tmp:
                try:
                    callback(tmp, None)
                except StopIteration:
                    pass
                out_str += tmp

        return out_str, is_truncated

    def rollback(self, session: str = "default"):
        sd = self._get_session(session)
        if sd["checkpoint_pkv"] is not None:
            sd["past_key_values"] = sd["checkpoint_pkv"]
            sd["checkpoint_pkv"] = None

    def reset_state(self, session: str = "default"):
        if session in self._sessions:
            del self._sessions[session]

    def cleanup(self):
        del self.model
        self._sessions.clear()
        gc.collect()
        torch.cuda.empty_cache()
