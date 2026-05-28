"""
Modified RWKV_x070 with dual-GPU layer-level distribution.

RWKV v7 model class that supports `cuda:0 fp16 -> cuda:1 fp16` strategy syntax.
Based on rwkv.model.RWKV_x070 (v0.8.30), with JIT disabled for device switching.

Usage:
    from rwkv_x070_dual import RWKV_x070_Dual
    model = RWKV_x070_Dual(model_path, strategy='cuda:0 fp16 -> cuda:1 fp16')
"""

import os, re, gc, types
import torch
import torch.nn as nn
from torch.nn import functional as F

torch.backends.cudnn.benchmark = True
torch.backends.cudnn.allow_tf32 = True
torch.backends.cuda.matmul.allow_tf32 = True


def _parse_strategy(strategy: str):
    """Parse strategy like 'cuda:0 fp16 -> cuda:1 fp16' → (segments, DTYPE)."""
    REGEX = r"^(?:(?:^|->) *(?:cuda(?::[\d]+)?|cpu|mps|dml) (?:fp(?:16|32)|bf16)(?:i8|i4|i3)?(?: \*[\d]+\+?)? *)+$"
    if not re.match(REGEX, strategy):
        raise ValueError(f"Invalid strategy: {strategy}")
    
    segments = [x.strip().split(' ') for x in strategy.split('->')]
    
    dtype_map = {'fp16': torch.half, 'fp32': torch.float32, 'bf16': torch.bfloat16}
    dtype_str = segments[0][1]
    for suf in ['i8', 'i4', 'i3']:
        if dtype_str.endswith(suf):
            dtype_str = dtype_str[:-len(suf)]
            break
    DTYPE = dtype_map.get(dtype_str, torch.half)
    
    return segments, DTYPE


def _compute_device_map(segments, n_layer):
    """Compute per-layer device → device_string, e.g. {0: 'cuda:0', ..., 61: 'cuda:1'}."""
    N = len(segments)
    to_allocate = n_layer + 1
    plan = [0] * N
    free_slots = 0
    allocated = 0
    for i in range(N):
        si = segments[i]
        if len(si) > 2:
            ss = si[2]
            assert ss.startswith('*')
            plan[i] = int(ss[1:])
            allocated += plan[i]
        else:
            free_slots += 1
    if free_slots > 0 and to_allocate > allocated:
        for i in range(N):
            if plan[i] == 0:
                plan[i] = (to_allocate - allocated) // free_slots
                allocated += plan[i]
                free_slots -= 1
    if to_allocate > allocated:
        plan[-1] += to_allocate - allocated
    for i in range(1, N):
        plan[i] += plan[i-1]
    
    dev_map = {}
    for n in range(n_layer + 1):
        for i in range(N):
            if n < plan[i]:
                dev_map[n] = segments[i][0]
                break
    return dev_map


def _layer_id(key: str) -> int:
    if 'blocks.' in key:
        return int(key.split('.')[1])
    if 'head.' in key or 'ln_out.' in key:
        return 9999  # mapped to n_layer later
    return 0


# ─── Single-token TMix (pure torch, no CUDA op needed) ────────────────────

def _tmix_one(layer_id, H, N, x, x_prev, v_first, state,
              x_r, x_w, x_k, x_v, x_a, x_g, w0, w1, w2, a0, a1, a2,
              v0, v1, v2, g1, g2, k_k, k_a, r_k,
              R_, K_, V_, O_, ln_w, ln_b):
    xx = x_prev - x
    xr = x + xx * x_r; xw = x + xx * x_w; xk = x + xx * x_k
    xv = x + xx * x_v; xa = x + xx * x_a; xg = x + xx * x_g
    r = xr @ R_
    w = torch.tanh(xw @ w1) @ w2
    k = xk @ K_
    v = xv @ V_
    a = torch.sigmoid(a0 + (xa @ a1) @ a2)
    g = torch.sigmoid(xg @ g1) @ g2
    kk = F.normalize((k * k_k).view(H, N), dim=-1, p=2.0).view(H*N)
    k = k * (1 + (a-1) * k_a)
    if layer_id == 0:
        v_first = v
    else:
        v = v + (v_first - v) * torch.sigmoid(v0 + (xv @ v1) @ v2)
    w = torch.exp(-0.606531 * torch.sigmoid((w0 + w).float()))
    vk = v.view(H, N, 1) @ k.view(H, 1, N)
    ab = (-kk).view(H, N, 1) @ (kk*a).view(H, 1, N)
    state = state * w.view(H, 1, N) + state @ ab.float() + vk.float()
    xx = (state.to(dtype=x.dtype) @ r.view(H, N, 1))
    xx = F.group_norm(xx.view(1, H*N), H, weight=ln_w, bias=ln_b, eps=64e-5).view(H*N)
    xx = xx + ((r * k * r_k).view(H, N).sum(-1, keepdim=True) * v.view(H, N)).view(H*N)
    return (xx * g) @ O_, x, state, v_first


def _cmix_one(x, x_prev, x_k, K_, V_):
    xx = x_prev - x
    xk = x + xx * x_k
    k = F.relu(xk @ K_) ** 2
    return k @ V_, x


# ─── Model class ───────────────────────────────────────────────────────────

class RWKV_x070_Dual(nn.Module):
    def __init__(self, model, strategy):
        super().__init__()
        self.eval()
        print(f'[Dual-GPU] Loading {model} ({strategy})\n')
        
        segments, self.dtype = _parse_strategy(strategy)
        self.is_multi = len(segments) > 1
        default_dev = segments[0][0]
        
        # Load to CPU first
        path = model if model.endswith('.pth') else model + '.pth'
        raw = torch.load(path, map_location='cpu', mmap=True)
        
        # Dimensions
        self.n_head, self.head_size = raw['blocks.0.att.r_k'].shape
        self.vocab_size, self.n_embd = raw['emb.weight'].shape
        n_layer = 0
        for k in raw:
            if 'blocks.' in k:
                n_layer = max(n_layer, int(k.split('.')[1]) + 1)
        self.n_layer = n_layer
        print(f'[Dual-GPU] {n_layer} layers, {self.n_embd} dim, {self.vocab_size} vocab')
        
        # Device map
        if self.is_multi:
            self.dev_map = _compute_device_map(segments, n_layer)
            for d in set(self.dev_map.values()):
                cnt = sum(1 for v in self.dev_map.values() if v == d)
                print(f'  {d}: {cnt} layers')
            # Verify
            emb_dev = self.dev_map.get(0, default_dev)
            head_dev = self.dev_map.get(n_layer, default_dev)
            print(f'  emb.weight → {emb_dev}, head → {head_dev}')
        else:
            self.dev_map = {}
        
        def _dev(lid):
            return self.dev_map.get(lid, default_dev) if self.is_multi else default_dev
        
        # Load weights
        self.z = {}
        keys = list(raw.keys())
        for k in keys:
            lid = _layer_id(k)
            if lid == 9999:
                lid = n_layer
            t = raw[k]
            if any(x in k for x in ['key.weight','value.weight','receptance.weight','output.weight','head.weight']):
                t = t.t().contiguous()
            t = t.squeeze()
            if k.endswith('att.r_k'):
                t = t.flatten()
            self.z[k] = t.to(_dev(lid)).to(self.dtype)
            del raw[k]
            if keys.index(k) % 5 == 0:
                torch.cuda.empty_cache()
        
        # Precompute embedding
        self.z['emb.weight'] = F.layer_norm(
            self.z['emb.weight'], (self.n_embd,),
            weight=self.z['blocks.0.ln0.weight'], bias=self.z['blocks.0.ln0.bias'])
        
        # Placeholder tensors
        for vk in ['v0', 'v1', 'v2']:
            self.z[f'blocks.0.att.{vk}'] = torch.empty(0, device=_dev(0), dtype=self.dtype)
        
        # Summary
        if self.is_multi:
            dc = {}
            for n, p in self.z.items():
                if hasattr(p, 'device'):
                    d = str(p.device)
                    dc[d] = dc.get(d, 0) + 1
            print(f'[Dual-GPU] Weights: {dc}')
            for i in range(torch.cuda.device_count()):
                try:
                    f, t = torch.cuda.mem_get_info(i)
                    print(f'  GPU {i}: used={(t-f)/1024**3:.2f}GiB / {t/1024**3:.2f}GiB')
                except: pass
        
        torch.cuda.empty_cache()
        print(f'[Dual-GPU] Done\n')
    
    # ─── Forward ────────────────────────────────────────────────────────
    
    def forward(self, idx, state=None, full_output=False):
        if state is None:
            state = [None] * (self.n_layer * 3)
            for i in range(self.n_layer):
                dev = self.dev_map.get(i, str(self.z['emb.weight'].device)) if self.is_multi else str(self.z['emb.weight'].device)
                stype = self.dtype
                state[i*3+0] = torch.zeros(self.n_embd, dtype=stype, device=dev)
                state[i*3+1] = torch.zeros(
                    (self.n_embd // self.head_size, self.head_size, self.head_size),
                    dtype=torch.float, device=dev)
                state[i*3+2] = torch.zeros(self.n_embd, dtype=stype, device=dev)
        
        if isinstance(idx, list):
            if len(idx) > 1:
                # Sequential mode: fall back to one-by-one
                # (avoids RWKV7 CUDA op that's hardcoded to single device)
                if not full_output:
                    for token in idx:
                        out, state = self._forward_one(token, state)
                    return out, state
                else:
                    outs = []
                    for token in idx:
                        out, state = self._forward_one(token, state)
                        outs.append(out)
                    return torch.stack(outs), state
            else:
                return self._forward_one(idx[0], state)
        else:
            return self._forward_one(idx, state)
    
    def _forward_one(self, idx: int, state):
        with torch.no_grad():
            z = self.z
            x = z['emb.weight'][idx]
            v_first = torch.empty_like(x)
            cur_dev = str(x.device)
            
            for i in range(self.n_layer):
                tgt = self.dev_map.get(i, cur_dev) if self.is_multi else cur_dev
                if tgt != cur_dev:
                    x = x.to(device=tgt)
                    v_first = v_first.to(device=tgt)
                    cur_dev = tgt
                
                b = f'blocks.{i}.'
                a = f'blocks.{i}.att.'
                f = f'blocks.{i}.ffn.'
                
                xx = F.layer_norm(x, (self.n_embd,), weight=z[b+'ln1.weight'], bias=z[b+'ln1.bias'])
                xx, state[i*3+0], state[i*3+1], v_first = _tmix_one(
                    i, self.n_head, self.head_size, xx, state[i*3+0], v_first, state[i*3+1],
                    z[a+'x_r'],z[a+'x_w'],z[a+'x_k'],z[a+'x_v'],z[a+'x_a'],z[a+'x_g'],
                    z[a+'w0'],z[a+'w1'],z[a+'w2'],z[a+'a0'],z[a+'a1'],z[a+'a2'],
                    z[a+'v0'],z[a+'v1'],z[a+'v2'],z[a+'g1'],z[a+'g2'],z[a+'k_k'],z[a+'k_a'],z[a+'r_k'],
                    z[a+'receptance.weight'],z[a+'key.weight'],z[a+'value.weight'],z[a+'output.weight'],
                    z[a+'ln_x.weight'],z[a+'ln_x.bias'])
                x = x + xx
                
                xx = F.layer_norm(x, (self.n_embd,), weight=z[b+'ln2.weight'], bias=z[b+'ln2.bias'])
                xx, state[i*3+2] = _cmix_one(xx, state[i*3+2], z[f+'x_k'], z[f+'key.weight'], z[f+'value.weight'])
                x = x + xx
            
            # Head
            hd = self.dev_map.get(self.n_layer, cur_dev) if self.is_multi else cur_dev
            if str(x.device) != hd:
                x = x.to(device=hd)
            x = F.layer_norm(x, (self.n_embd,), weight=z['ln_out.weight'], bias=z['ln_out.bias'])
            x = x @ z['head.weight']
            return x, state