import numpy as np
from common.mnist import load_mnist


def test_load_mnist_shapes_and_range():
    x_tr, y_tr, x_te, y_te = load_mnist(n_train=100, n_test=20)
    assert x_tr.shape == (100, 784)
    assert y_tr.shape == (100,)
    assert x_te.shape == (20, 784)
    assert y_te.shape == (20,)
    assert x_tr.dtype == np.float32
    assert y_tr.dtype == np.int64
    assert x_tr.min() >= 0.0 and x_tr.max() <= 1.0
    assert y_tr.min() >= 0 and y_tr.max() <= 9
