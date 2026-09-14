"""Plain vs Residual 深层 MLP，手写前向与反向传播。

回答 Q1：为什么网络越深越难训练？残差连接如何缓解？

Run:  python3 resnet/plain_vs_residual.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.mnist import load_mnist


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def xavier(rng, fan_in, fan_out):
    return rng.normal(0.0, np.sqrt(1.0 / fan_in), size=(fan_in, fan_out)).astype(np.float32)


class DeepMLP:
    """全连接深层网络；residual=True 时每 2 层加一个恒等 shortcut。

    记 h[0]=x，第 i 层 a[i]=sigmoid(h[i] @ W[i])，则
      h[i+1] = a[i]                （普通层）
      h[i+1] = a[i] + h[i-1]       （i 为奇数时为残差块出口）
    输出 logits = h[L] @ W[L]。

    维度说明（与朴素公式的唯一差异）：
    第 0 层是 stem（in_dim -> hidden），故 h[0] 宽度为 in_dim，而 a[1] 宽度为
    hidden。当 in_dim != hidden 时 i=1 的恒等 shortcut 宽度不匹配、无法相加。
    这里只在 h[i-1] 与 a[i] 宽度一致时才加 shortcut（真实 ResNet 中该位置对应
    需要 1x1 投影的 stem 层；本实现为保持手写反向的简洁，直接跳过该 shortcut，
    其余 block 的 shortcut 全部保留）。forward/backward 使用完全相同的判定。
    """

    def __init__(self, in_dim=784, hidden=128, n_layers=20, n_classes=10,
                 residual=False, seed=0):
        assert n_layers % 2 == 0, "n_layers must be even (residual blocks of 2)"
        self.residual = residual
        self.n_layers = n_layers
        rng = np.random.default_rng(seed)
        dims = [in_dim] + [hidden] * n_layers + [n_classes]
        self.W = [xavier(rng, dims[i], dims[i + 1]) for i in range(len(dims) - 1)]

    def _block_skip(self, j, h, a):
        """第 j 层（j 为奇数，残差块出口）是否使用恒等 shortcut。

        j=1 是 stem block：h[0] 宽度为 in_dim，而 a[1] 宽度为 hidden，当
        in_dim != hidden 时二者无法相加，只能退化为普通层。forward 与 backward
        共用此判定，确保梯度索引（+G[i+2]）与真实计算图完全一致。
        """
        return (
            self.residual
            and j % 2 == 1
            and j - 1 < len(h)
            and j < len(a)
            and h[j - 1].shape == a[j].shape
        )

    def forward(self, x, cache):
        L = self.n_layers
        h = [x]
        a = []
        for i in range(L):
            ai = sigmoid(h[i] @ self.W[i])
            a.append(ai)
            if self._block_skip(i, h, a):
                h.append(ai + h[i - 1])
            else:
                h.append(ai)
        logits = h[L] @ self.W[L]
        cache["h"] = h
        cache["a"] = a
        return logits

    def backward(self, cache, dlogits):
        h = cache["h"]
        a = cache["a"]
        L = self.n_layers
        grads = [None] * (L + 1)
        G = [None] * (L + 2)
        grads[L] = h[L].T @ dlogits
        G[L] = dlogits @ self.W[L].T
        for i in range(L - 1, -1, -1):
            dz = G[i + 1] * a[i] * (1.0 - a[i])
            grads[i] = h[i].T @ dz
            gi = dz @ self.W[i].T
            if self.residual and (i % 2 == 0) and (i + 2 <= L) and self._block_skip(i + 1, h, a):
                gi = gi + G[i + 2]
            G[i] = gi
        return grads


def train(residual, steps=500, batch=64, lr=0.1, seed=0):
    x_tr, y_tr, x_te, y_te = load_mnist(n_train=6000, n_test=1000)
    net = DeepMLP(residual=residual, seed=seed)
    rng = np.random.default_rng(seed)
    losses, g0 = [], []
    for _ in range(steps):
        idx = rng.integers(0, len(x_tr), batch)
        xb, yb = x_tr[idx], y_tr[idx]
        cache = {}
        logits = net.forward(xb, cache)
        p = softmax(logits)
        loss = -np.log(p[np.arange(batch), yb] + 1e-12).mean()
        dlogits = p.copy()
        dlogits[np.arange(batch), yb] -= 1.0
        dlogits /= batch
        grads = net.backward(cache, dlogits)
        for i in range(len(net.W)):
            net.W[i] -= lr * grads[i]
        losses.append(float(loss))
        g0.append(float(np.linalg.norm(grads[0])))
    return net, losses, g0


def main():
    result = {}
    for name, res in [("plain", False), ("residual", True)]:
        net, losses, g0 = train(res)
        result[name] = (losses, g0)
        print(f"[{name:8s}] loss {losses[0]:.4f} -> {losses[-1]:.4f} | "
              f"mean |grad layer-0| = {np.mean(g0[10:]):.3e}")
    g_plain = np.mean(result["plain"][1][10:])
    g_res = np.mean(result["residual"][1][10:])
    print(f"\n浅层梯度范数比 residual/plain = {g_res / (g_plain + 1e-30):.3e}")
    print("结论：plain 网络浅层梯度趋近于 0（梯度消失），残差连接保住了梯度通路。")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(10, 4))
        for name in result:
            ax[0].plot(result[name][0], label=name)
            ax[1].plot(result[name][1], label=name)
        ax[0].set_title("training loss")
        ax[1].set_title("|grad| at layer 0")
        ax[1].set_yscale("log")
        for a in ax:
            a.legend()
            a.grid(alpha=0.3)
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.png")
        fig.tight_layout()
        fig.savefig(out, dpi=120)
        print(f"图已保存: {out}")
    except Exception as e:
        print(f"[plot skipped] {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
