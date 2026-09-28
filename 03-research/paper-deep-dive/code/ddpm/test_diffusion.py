import torch
from ddpm.simple_ddpm import Diffusion


def test_q_sample_limits():
    # NOTE: uses T=1000 (standard DDPM horizon) so that alpha_bar[T-1] ~ 4e-5,
    # making "t=T-1 is almost pure noise" true. With T=100, alpha_bar[99] ~ 0.36
    # (only ~64% noise), which would not satisfy a tight tolerance.
    # t=0 uses atol=0.05 because beta_start=1e-4 injects sqrt(1e-4)*noise = 0.01*noise.
    torch.manual_seed(0)
    diff = Diffusion(T=1000)
    x0 = torch.randn(8, 1, 28, 28)
    noise = torch.randn_like(x0)

    t0 = torch.zeros(8, dtype=torch.long)
    xt0 = diff.q_sample(x0, t0, noise)
    assert torch.allclose(xt0, x0, atol=0.05), "t=0 should be (almost) clean"

    tT = torch.full((8,), 999, dtype=torch.long)
    xtT = diff.q_sample(x0, tT, noise)
    assert torch.allclose(xtT, noise, atol=0.05), "t=T-1 should be (almost) pure noise"


def test_alpha_bar_monotonic():
    diff = Diffusion(T=100)
    ab = diff.alpha_bars
    assert torch.all(ab[1:] <= ab[:-1])
    assert ab[0] < 1.0 and ab[-1] > 0.0
