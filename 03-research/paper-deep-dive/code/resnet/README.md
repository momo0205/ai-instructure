# ResNet 最小复现：Plain vs Residual

## 目的

验证 Q1：深层 plain 网络浅层梯度消失，残差连接提供梯度直通路。

## 运行

    python3 resnet/plain_vs_residual.py

## 实现要点

- 20 层全连接 MLP，隐藏维 128，Xavier 初始化，sigmoid 激活。
- `residual=False`：每层 y = σ(Wx)。
- `residual=True`：每 2 层一个恒等 shortcut，y = σ(Wx) + 块输入。
- 全部用 NumPy 手写反向传播，`test_gradient.py` 用有限差分校验正确性。

## 观察

实跑结果（真实 MNIST，n_train=6000，500 step，batch=64，lr=0.1，seed=0）：

| 配置 | 起始 loss | 结束 loss | 浅层梯度范数均值 |
|------|----------|----------|----------------|
| plain | 2.3819 | 2.3186 | 4.567e-13 |
| residual | 9.1520 | 2.0245 | 8.155e-02 |

浅层梯度范数比 residual/plain = **1.786e+11**

- plain 网络的第 0 层梯度（4.6e-13）已到浮点噪声量级，500 步后 loss 几乎不动
  （2.3819 → 2.3186），是典型的梯度消失：链式乘积穿过 20 层 sigmoid 后指数衰减。
- residual 网络浅层梯度（8.2e-2）比 plain 高 11 个数量级，且 loss 明显下降
  （9.1520 → 2.0245），说明恒等 shortcut 为梯度提供了直通路径。

## 结论

20 层 plain sigmoid MLP 会因梯度消失而无法训练：误差信号逐层乘以
`σ'(z) ≤ 0.25`，深层的局部梯度乘积指数趋近 0，浅层几乎收不到更新信号。

残差连接把 `h[i+1] = a[i]` 改成 `h[i+1] = a[i] + h[i-1]`，反向时给 `G[i]`
额外加回 `G[i+2]` 这一恒等项，梯度可以不经过任何非线性层直达浅层。因此浅层梯度
被保住（本实验差 11 个数量级），loss 得以正常下降。

这正是 ResNet 的核心动机：**让优化本身变简单，而不是只让表达能力变强**。

> 实现注记：本实现中第 0 层是 `in_dim -> hidden` 的 stem，`h[0]` 宽度为
> `in_dim` 而 `a[1]` 宽度为 `hidden`，故 `i=1` 处的恒等 shortcut 宽度不匹配、
> 无法相加，被跳过（真实 ResNet 在该位置用一个 1×1 卷积做投影）。
> 其余所有 block 的 shortcut 均保留。`forward` 与 `backward` 共用同一个
> `_block_skip` 判定，保证计算图与梯度索引一致——这一点由有限差分校验兜底
> （全配置最大误差 3.8e-10，tolerance 1e-6）。

## 动手实验（改一处参数再做一次）

1. 把激活函数换成 ReLU，梯度消失现象还明显吗？
2. 把层数改成 4 层，plain 和 residual 还有区别吗？
3. 把 `hidden` 改成 32，观察差异是否变化。
