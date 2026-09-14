# Transformer 最小复现：单头注意力

## 目的

验证 Q2：注意力可并行计算、因果掩码保证不看到未来。

## 运行

    python3 transformer/tiny_attention.py

## 实现要点

- 单头自注意力：q = Wq x，score = q k^T / sqrt(d_k)，causal mask，softmax，out = att v。
- 每个 Block：LayerNorm -> 注意力 -> 残差 -> LayerNorm -> FFN -> 残差。
- 字符级 tokenizer + 可学习位置嵌入（简化版位置编码）。

## 观察

| 指标 | 数值 |
|------|------|
| 起始 loss | 2.4766 (step 100) |
| 结束 loss | 1.9950 (step 500) |
| 500 步内下降 | -0.4816 (-19.4%) |
| 生成样本是否像英文 | 部分像：含 `would`、`me to you`、`And` 等常见英文短词，但仍多为随机字符（样本量为 500 步，模型未完全收敛） |

## 训练日志

```
step  100  loss 2.4766
step  200  loss 2.2205
step  300  loss 2.1575
step  400  loss 2.0706
step  500  loss 1.9950
```

## 注意力矩阵（前 5x5，验证因果掩码）

```
[[1.   0.   0.   0.   0.  ]
 [0.92 0.08 0.   0.   0.  ]
 [0.22 0.24 0.54 0.   0.  ]
 [0.43 0.34 0.05 0.18 0.  ]
 [0.21 0.02 0.14 0.58 0.05]]
```

上三角全为 0：future token 被正确屏蔽。每行和为 1：softmax 输出为概率分布。

## 动手实验

1. 把 `n_embd` 从 64 改成 16，看 loss 下降变慢多少。
2. 去掉 `masked_fill`，让模型能看到未来，生成质量如何变化？
3. 把注意力换成 2 头（复制一份 Wq/Wk/Wv 后拼接），观察效果。
4. 直接把 `att`（softmax 后）打印出来，验证每一行和为 1。
