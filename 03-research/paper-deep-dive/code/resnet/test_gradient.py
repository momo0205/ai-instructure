import numpy as np
from resnet.plain_vs_residual import DeepMLP, softmax


def _loss(net, x, y):
    logits = net.forward(x, {})
    p = softmax(logits)
    return -np.log(p[np.arange(len(y)), y] + 1e-12).mean()


def _numeric_grad(net, x, y, layer, r, c, eps=1e-5):
    orig = net.W[layer][r, c]
    net.W[layer][r, c] = orig + eps
    lp = _loss(net, x, y)
    net.W[layer][r, c] = orig - eps
    lm = _loss(net, x, y)
    net.W[layer][r, c] = orig
    return (lp - lm) / (2 * eps)


def _analytic_grad(net, x, y):
    cache = {}
    logits = net.forward(x, cache)
    p = softmax(logits)
    dlogits = p.copy()
    dlogits[np.arange(len(y)), y] -= 1.0
    dlogits /= len(y)
    return net.backward(cache, dlogits)


def test_backward_matches_finite_difference():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(4, 8)).astype(np.float64)
    y = rng.integers(0, 3, size=4)
    for residual in (False, True):
        net = DeepMLP(in_dim=8, hidden=6, n_layers=4, n_classes=3,
                      residual=residual, seed=1)
        net.W = [w.astype(np.float64) for w in net.W]
        grads = _analytic_grad(net, x, y)
        for (layer, r, c) in [(0, 0, 0), (2, 1, 3), (4, 0, 1)]:
            num = _numeric_grad(net, x, y, layer, r, c)
            ana = grads[layer][r, c]
            assert abs(num - ana) < 1e-6, (residual, layer, r, c, num, ana)
