# 论文精读：问题驱动 + 最小复现

精读三篇经典论文，回答三个核心问题，每个问题配套一份能在笔记本上跑通的最小复现代码。

## 三篇论文

| 问题 | 论文 | 原文 |
|------|------|------|
| Q1 为什么网络越深越难训练？ | Deep Residual Learning (ResNet, 2015) | [papers/resnet/resnet.pdf](papers/resnet/resnet.pdf) |
| Q2 为什么注意力能替代序列建模？ | Attention Is All You Need (Transformer, 2017) | [papers/transformer/attention_is_all_you_need.pdf](papers/transformer/attention_is_all_you_need.pdf) |
| Q3 为什么扩散模型能生成高质量样本？ | Denoising Diffusion Probabilistic Models (DDPM, 2020) | [papers/ddpm/ddpm.pdf](papers/ddpm/ddpm.pdf) |

## 学习循环（每篇 2-3 周）

1. **Week 1 问题建立**：读 `questions/` 文档，速读 Abstract/Intro/Conclusion，写出自己的初始理解和 3 个困惑点。
2. **Week 2 精读推导**：逐节精读，手写核心公式推导（拍照存档），读辅助材料验证理解。
3. **Week 3 最小复现**：跑通 `code/` 下的脚本，改一处参数做实验，完成 `checkpoints/` 自测题。

## 完成标准

- [ ] 讲得清：能口头解释核心思想（3 分钟）
- [ ] 推得动：核心公式有手写推导存档
- [ ] 复现得了：代码跑通，理解每行，能改实验
- [ ] 答得对：自测题 80% 正确

## 进度追踪

| 论文 | Week 1 | Week 2 | Week 3 | 状态 |
|------|--------|--------|--------|------|
| ResNet | [ ] | [ ] | [ ] | 未开始 |
| Transformer | [ ] | [ ] | [ ] | 未开始 |
| DDPM | [ ] | [ ] | [ ] | 未开始 |

## 运行复现

```bash
cd code
pip install -r requirements.txt
python3 resnet/plain_vs_residual.py      # ~3 分钟
python3 transformer/tiny_attention.py    # ~5 分钟
python3 ddpm/simple_ddpm.py              # ~8 分钟
```

每个脚本会自动下载数据；无网络时降级为合成数据（会打印提示）。

## 跑测试

```bash
cd code
python3 -m pytest common/test_mnist.py resnet/test_gradient.py transformer/test_attention.py ddpm/test_diffusion.py -v
```
