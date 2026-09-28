"""单头自注意力字符级语言模型（Tiny Shakespeare）。

回答 Q2：为什么注意力能替代序列建模？

Run:  python3 transformer/tiny_attention.py
"""
import math
import os
import sys
import urllib.request

import torch
import torch.nn as nn
import torch.nn.functional as F

DATA_URL = ("https://raw.githubusercontent.com/karpathy/char-rnn/"
            "master/data/tinyshakespeare/input.txt")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input.txt")
FALLBACK = ("to be or not to be that is the question\n"
            "whether tis nobler in the mind to suffer\n") * 200


def load_text():
    if os.path.exists(CACHE):
        with open(CACHE, "r", encoding="utf-8") as f:
            return f.read()
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        urllib.request.urlretrieve(DATA_URL, CACHE)
        with open(CACHE, "r", encoding="utf-8") as f:
            print("[text] downloaded Tiny Shakespeare")
            return f.read()
    except Exception as e:
        print(f"[text] download failed ({type(e).__name__}), using fallback text")
        return FALLBACK


class CharTokenizer:
    def __init__(self, text):
        self.chars = sorted(set(text))
        self.stoi = {c: i for i, c in enumerate(self.chars)}
        self.itos = {i: c for c, i in self.stoi.items()}

    @property
    def vocab_size(self):
        return len(self.chars)

    def encode(self, s):
        return [self.stoi[c] for c in s]

    def decode(self, ids):
        return "".join(self.itos[i] for i in ids)


class SingleHeadAttention(nn.Module):
    def __init__(self, n_embd, block_size):
        super().__init__()
        self.Wq = nn.Linear(n_embd, n_embd, bias=False)
        self.Wk = nn.Linear(n_embd, n_embd, bias=False)
        self.Wv = nn.Linear(n_embd, n_embd, bias=False)
        self.scale = n_embd ** -0.5
        self.register_buffer("mask", torch.tril(torch.ones(block_size, block_size)).bool())

    def forward(self, x, return_attn=False):
        B, T, C = x.shape
        q, k, v = self.Wq(x), self.Wk(x), self.Wv(x)
        att = (q @ k.transpose(-2, -1)) * self.scale
        att = att.masked_fill(~self.mask[:T, :T], float("-inf"))
        att = F.softmax(att, dim=-1)
        out = att @ v
        return (out, att) if return_attn else out


class Block(nn.Module):
    def __init__(self, n_embd, block_size):
        super().__init__()
        self.ln1 = nn.LayerNorm(n_embd)
        self.attn = SingleHeadAttention(n_embd, block_size)
        self.ln2 = nn.LayerNorm(n_embd)
        self.ff = nn.Sequential(
            nn.Linear(n_embd, 4 * n_embd), nn.GELU(), nn.Linear(4 * n_embd, n_embd)
        )

    def forward(self, x, return_attn=False):
        if return_attn:
            a, att = self.attn(self.ln1(x), return_attn=True)
            x = x + a
            x = x + self.ff(self.ln2(x))
            return x, att
        x = x + self.attn(self.ln1(x))
        x = x + self.ff(self.ln2(x))
        return x


class TinyTransformer(nn.Module):
    def __init__(self, vocab_size, n_embd=64, block_size=32, n_layer=2):
        super().__init__()
        self.block_size = block_size
        self.tok_emb = nn.Embedding(vocab_size, n_embd)
        self.pos_emb = nn.Embedding(block_size, n_embd)
        self.blocks = nn.ModuleList([Block(n_embd, block_size) for _ in range(n_layer)])
        self.ln_f = nn.LayerNorm(n_embd)
        self.head = nn.Linear(n_embd, vocab_size)

    def forward(self, idx, return_attn=False):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device)
        x = self.tok_emb(idx) + self.pos_emb(pos)[None, :, :]
        att_last = None
        for blk in self.blocks:
            if return_attn:
                x, att_last = blk(x, return_attn=True)
            else:
                x = blk(x)
        x = self.ln_f(x)
        logits = self.head(x)
        return (logits, att_last) if return_attn else logits


def get_batch(data, block_size, batch, rng):
    ix = torch.randint(len(data) - block_size - 1, (batch,), generator=rng)
    x = torch.stack([data[i:i + block_size] for i in ix])
    y = torch.stack([data[i + 1:i + block_size + 1] for i in ix])
    return x, y


def main():
    torch.manual_seed(0)
    text = load_text()
    tok = CharTokenizer(text)
    data = torch.tensor(tok.encode(text), dtype=torch.long)
    n = int(0.9 * len(data))
    train_data = data[:n]

    model = TinyTransformer(tok.vocab_size)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
    rng = torch.Generator().manual_seed(0)

    steps, block_size, batch = 500, 32, 32
    for step in range(1, steps + 1):
        x, y = get_batch(train_data, block_size, batch, rng)
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, tok.vocab_size), y.reshape(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step % 100 == 0:
            print(f"step {step:4d}  loss {loss.item():.4f}")

    model.eval()
    with torch.no_grad():
        idx = torch.zeros((1, 1), dtype=torch.long)
        for _ in range(200):
            idx_cond = idx[:, -block_size:]
            logits, att = model(idx_cond, return_attn=True)
            probs = F.softmax(logits[:, -1, :], dim=-1)
            nxt = torch.multinomial(probs, 1)
            idx = torch.cat([idx, nxt], dim=1)
    print("\n生成样本:\n" + tok.decode(idx[0].tolist()))

    with torch.no_grad():
        x, _ = get_batch(train_data, block_size, 1, rng)
        _, att = model(x, return_attn=True)
    print("\n注意力矩阵（前 5x5，行=query，列=key，上三角应为 0）:")
    print(att[0, :5, :5].numpy().round(2))


if __name__ == "__main__":
    main()
