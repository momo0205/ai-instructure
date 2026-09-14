# Checkpoint 1：ResNet 自测

每题先自己作答，再展开答案对照。对 8/10 以上算通过。

## 1. 退化问题的定义是什么？
<details><summary>答案</summary>
层数增加时，训练误差（不是测试误差）反而变大。说明不是过拟合，而是优化变难。
</details>

## 2. 为什么不能简单认为"加深网络最差也就是退化成浅层网络"？
<details><summary>答案</summary>
因为恒等映射对多层非线性堆叠来说很难学——理论上存在解（多余的层学恒等），但优化器找不到。
</details>

## 3. 写出一个残差块的公式。
<details><summary>答案</summary>
y = F(x, {W_i}) + x，其中 F 是两层卷积 + BN + ReLU；F(x)=0 时即恒等映射。
</details>

## 4. shortcut 上有参数吗？为什么？
<details><summary>答案</summary>
恒等 shortcut 无参数。这样不增加参数量，且梯度可无损直通。
</details>

## 5. 输入输出通道不一致时怎么处理？
<details><summary>答案</summary>
用 1x1 卷积投影 W_s x 对齐维度（式 2），论文发现恒等映射已足够，投影只在需要时用。
</details>

## 6. 从梯度角度解释 shortcut 为什么缓解梯度消失。
<details><summary>答案</summary>
∂L/∂x = ∂L/∂y · (1 + ∂F/∂x)。那个"+1"是恒等通路，保证梯度至少原样回传一层，不会被 ∂F/∂x 完全衰减。
</details>

## 7. bottleneck 结构是什么？为什么用？
<details><summary>答案</summary>
1x1 降维 -> 3x3 -> 1x1 升维。减少 3x3 卷积的通道数，控制深层网络的参数量和计算量。
</details>

## 8. 论文在 CIFAR-10 上做了消融，说明了什么？
<details><summary>答案</summary>
plain-34 比 plain-18 训练误差更高（退化），residual-34 反而更好，证明残差结构解决的是优化问题。
</details>

## 9. 复现代码里 plain 网络的浅层梯度为什么接近 0？
<details><summary>答案</summary>
20 层 sigmoid，每层导数相乘（<1），梯度指数衰减；残差网络的恒等通路提供"+1"，梯度不衰减。
</details>

## 10. 一个陷阱：残差连接一定有用吗？
<details><summary>答案</summary>
不一定。网络不够深、存在 BN 或良好初始化时，退化不明显，残差收益有限；极深时才显著。
</details>
