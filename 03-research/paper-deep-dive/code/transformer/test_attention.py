import torch
from transformer.tiny_attention import SingleHeadAttention, load_text, CharTokenizer


def test_attention_shape_and_causality():
    torch.manual_seed(0)
    attn = SingleHeadAttention(n_embd=16, block_size=8)
    x = torch.randn(2, 5, 16)
    out, att = attn(x, return_attn=True)
    assert out.shape == (2, 5, 16)
    assert att.shape == (2, 5, 5)
    for b in range(2):
        for i in range(5):
            for j in range(i + 1, 5):
                assert att[b, i, j].item() == 0.0, "future position must be masked"
    assert torch.allclose(att.sum(dim=-1), torch.ones(2, 5), atol=1e-5)


def test_tokenizer_roundtrip():
    text = load_text()
    tok = CharTokenizer(text)
    s = text[:50]
    assert tok.decode(tok.encode(s)) == s
