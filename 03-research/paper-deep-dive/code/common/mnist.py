"""MNIST 加载器，三级降级保证离线可跑。

优先级：
1. torchvision（首次运行下载到 code/data/mnist）
2. sklearn fetch_openml（需联网）
3. 合成高斯团数据（纯离线兜底，会打印警告）
"""
import os
import numpy as np

CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mnist"
)


def _synthetic(n_train, n_test, dim=784, classes=10, seed=0):
    rng = np.random.default_rng(seed)
    centers = rng.normal(0.0, 1.0, size=(classes, dim)).astype(np.float32)

    def make(n, s):
        r = np.random.default_rng(s)
        y = r.integers(0, classes, size=n)
        x = centers[y] + r.normal(0.0, 1.2, size=(n, dim)).astype(np.float32)
        x = 1.0 / (1.0 + np.exp(-x))
        return x.astype(np.float32), y.astype(np.int64)

    xa, ya = make(n_train, seed + 1)
    xb, yb = make(n_test, seed + 2)
    return xa, ya, xb, yb


def load_mnist(n_train=2000, n_test=500, allow_synthetic=True):
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        import torchvision

        tr = torchvision.datasets.MNIST(root=CACHE_DIR, train=True, download=True)
        te = torchvision.datasets.MNIST(root=CACHE_DIR, train=False, download=True)
        x_tr = tr.data.numpy().reshape(-1, 784).astype(np.float32) / 255.0
        y_tr = tr.targets.numpy().astype(np.int64)
        x_te = te.data.numpy().reshape(-1, 784).astype(np.float32) / 255.0
        y_te = te.targets.numpy().astype(np.int64)
        print("[mnist] loaded real MNIST via torchvision")
        return x_tr[:n_train], y_tr[:n_train], x_te[:n_test], y_te[:n_test]
    except Exception as e:
        print(f"[mnist] torchvision unavailable ({type(e).__name__}), trying sklearn")

    try:
        from sklearn.datasets import fetch_openml

        d = fetch_openml("mnist_784", version=1, as_frame=False, parser="auto")
        x = d.data.astype(np.float32) / 255.0
        y = d.target.astype(np.int64)
        print("[mnist] loaded real MNIST via sklearn")
        return x[:n_train], y[:n_train], x[60000:60000 + n_test], y[60000:60000 + n_test]
    except Exception as e:
        print(f"[mnist] sklearn unavailable ({type(e).__name__}), using synthetic blobs")

    if not allow_synthetic:
        raise RuntimeError("No MNIST source available")
    print("[mnist] WARNING: using synthetic data, results are not real MNIST")
    return _synthetic(n_train, n_test)
