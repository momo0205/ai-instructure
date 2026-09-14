# Checkpoint 3：DDPM 自测

每题先自己作答，再展开答案对照。对 8/10 以上算通过。

## 1. 写出前向一步采样公式。
<details><summary>答案</summary>
q(x_t | x_0) = N(sqrt(alpha_bar_t) x_0, (1 - alpha_bar_t) I)，即 x_t = sqrt(ᾱ_t) x_0 + sqrt(1-ᾱ_t) ε。
</details>

## 2. 为什么前向过程可以直接采样 x_t，不用一步步加噪？
<details><summary>答案</summary>
因为高斯分布相加仍是高斯，T 次条件高斯的复合有解析闭式，可一步得到。
</details>

## 3. 为什么预测噪声 eps 而不是直接预测 x_0？
<details><summary>答案</summary>
t 很小时 eps 和 x_0 关系近似线性、容易学；且简化损失对应去噪得分匹配，训练更稳定。
</details>

## 4. 简化损失函数是什么？它从哪来？
<details><summary>答案</summary>
L_simple = E_{t,x_0,ε} ‖ε - ε_θ(x_t, t)‖²。从 ELBO 逐项化简，丢掉与 t 相关的加权系数得到。
</details>

## 5. beta 调度是什么？linear schedule 指什么？
<details><summary>答案</summary>
每步加的噪声方差 β_t。linear 指 β_t 从 1e-4 线性增到 0.02，使 ᾱ_T≈0。
</details>

## 6. 采样时为什么 t>0 要再加一次噪声？
<details><summary>答案</summary>
反向过程是随机过程，均值 + β_t 方差采样才对应 q(x_{t-1}|x_t)；t=0 时不再加，直接输出均值。
</details>

## 7. 反向过程为什么要用 U-Net？
<details><summary>答案</summary>
去噪需要在多个尺度上处理细节和全局结构，U-Net 的下采样-上采样 + 跳连能同时保留两者。
</details>

## 8. 时间步 t 怎么注入网络？
<details><summary>答案</summary>
正弦位置嵌入 + MLP 得到时间向量，加到每个残差块的特征上。
</details>

## 9. 复现测试里 t=0 和 t=T-1 分别验证了什么？
<details><summary>答案</summary>
t=0 时 ᾱ≈1，x_t≈x_0（干净）；t=T-1 时 ᾱ≈0，x_t≈ε（纯噪声），验证前向公式正确。
</details>

## 10. 陷阱：DDPM 采样为什么慢？
<details><summary>答案</summary>
需要 T 次网络前向（如 1000 步）串行执行，无法一次生成；DDIM 等后续工作用来加速。
</details>
