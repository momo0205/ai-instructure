"""简化版 DDPM：在 MNIST 上做前向加噪与反向去噪。

回答 Q3：为什么扩散模型能生成高质量样本？

Run:  python3 ddpm/simple_ddpm.py
"""
import math
import os
import sys

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.mnist import load_mnist


class SinusoidalPosEmb(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, t):
        half = self.dim // 2
        freqs = torch.exp(torch.arange(half, device=t.device) * (-math.log(10000.0) / (half - 1)))
        emb = t[:, None].float() * freqs[None, :]
        return torch.cat([emb.sin(), emb.cos()], dim=-1)


class DoubleConv(nn.Module):
    def __init__(self, cin, cout, t_dim):
        super().__init__()
        self.conv1 = nn.Conv2d(cin, cout, 3, padding=1)
        self.conv2 = nn.Conv2d(cout, cout, 3, padding=1)
        self.norm1 = nn.GroupNorm(4, cout)
        self.norm2 = nn.GroupNorm(4, cout)
        self.t_proj = nn.Linear(t_dim, cout)

    def forward(self, x, t):
        h = self.norm1(F.silu(self.conv1(x)))
        h = h + self.t_proj(t)[:, :, None, None]
        h = self.norm2(F.silu(self.conv2(h)))
        return h


class TinyUNet(nn.Module):
    def __init__(self, base=32, t_dim=64):
        super().__init__()
        self.t_mlp = nn.Sequential(
            SinusoidalPosEmb(t_dim), nn.Linear(t_dim, t_dim), nn.SiLU(),
            nn.Linear(t_dim, t_dim),
        )
        self.inc = DoubleConv(1, base, t_dim)
        self.down1 = DoubleConv(base, base, t_dim)
        self.down2 = DoubleConv(base, base * 2, t_dim)
        self.mid = DoubleConv(base * 2, base * 2, t_dim)
        self.up2 = DoubleConv(base * 3, base, t_dim)
        self.up1 = DoubleConv(base * 2, base, t_dim)
        self.outc = nn.Conv2d(base, 1, 1)
        self.pool = nn.MaxPool2d(2)

    def forward(self, x, t):
        t = self.t_mlp(t)
        h0 = self.inc(x, t)
        h1 = self.down1(self.pool(h0), t)
        h2 = self.down2(self.pool(h1), t)
        m = self.mid(h2, t)
        u2 = F.interpolate(m, scale_factor=2, mode="nearest")
        u2 = self.up2(torch.cat([u2, h1], dim=1), t)
        u1 = F.interpolate(u2, scale_factor=2, mode="nearest")
        u1 = self.up1(torch.cat([u1, h0], dim=1), t)
        return self.outc(u1)


class Diffusion:
    def __init__(self, T=100, beta_start=1e-4, beta_end=0.02, device="cpu"):
        self.T = T
        self.device = device
        self.betas = torch.linspace(beta_start, beta_end, T, device=device)
        self.alphas = 1.0 - self.betas
        self.alpha_bars = torch.cumprod(self.alphas, dim=0)

    def q_sample(self, x0, t, noise):
        ab = self.alpha_bars[t].view(-1, 1, 1, 1)
        return ab.sqrt() * x0 + (1.0 - ab).sqrt() * noise

    def loss(self, model, x0):
        B = x0.shape[0]
        t = torch.randint(0, self.T, (B,), device=x0.device)
        noise = torch.randn_like(x0)
        xt = self.q_sample(x0, t, noise)
        pred = model(xt, t.float())
        return F.mse_loss(pred, noise)

    @torch.no_grad()
    def sample(self, model, n):
        x = torch.randn(n, 1, 28, 28, device=self.device)
        for t in reversed(range(self.T)):
            tt = torch.full((n,), t, device=self.device, dtype=torch.float)
            pred = model(x, tt)
            beta = self.betas[t]
            alpha = self.alphas[t]
            ab = self.alpha_bars[t]
            mean = (1.0 / alpha.sqrt()) * (x - (beta / (1.0 - ab).sqrt()) * pred)
            x = mean if t == 0 else mean + beta.sqrt() * torch.randn_like(x)
        return x


def main():
    torch.manual_seed(0)
    x_tr, _, _, _ = load_mnist(n_train=8000, n_test=100)
    x = torch.tensor(x_tr[:8000]).reshape(-1, 1, 28, 28)

    diff = Diffusion(T=100)
    model = TinyUNet()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)

    steps, batch = 800, 64
    for step in range(1, steps + 1):
        idx = torch.randint(0, len(x), (batch,))
        loss = diff.loss(model, x[idx])
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step % 100 == 0:
            print(f"step {step:4d}  mse {loss.item():.4f}")

    model.eval()
    samples = diff.sample(model, 16).clamp(-1, 1)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples.png")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        grid = samples.squeeze(1).cpu().numpy()
        fig, axes = plt.subplots(4, 4, figsize=(5, 5))
        for i, ax in enumerate(axes.flat):
            ax.imshow((grid[i] + 1) / 2, cmap="gray")
            ax.axis("off")
        fig.tight_layout()
        fig.savefig(out, dpi=120)
        print(f"生成样本已保存: {out}")
    except Exception as e:
        print(f"[plot skipped] {type(e).__name__}: {e}")
        torch.save(samples, os.path.join(os.path.dirname(out), "samples.pt"))


if __name__ == "__main__":
    main()
