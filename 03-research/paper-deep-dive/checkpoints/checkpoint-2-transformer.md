# Checkpoint 2：Transformer 自测

每题先自己作答，再展开答案对照。对 8/10 以上算通过。

## 1. 写出 scaled dot-product attention 公式。
<details><summary>答案</summary>
Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) V
</details>

## 2. 为什么要除以 sqrt(d_k)？
<details><summary>答案</summary>
q·k 的方差随 d_k 增大而增大，softmax 会进入饱和区导致梯度过小。除以 sqrt(d_k) 把方差拉回 1。
</details>

## 3. 多头的计算量比单头大吗？为什么？
<details><summary>答案</summary>
基本相当。因为总维度不变，多头把 d_model 切成 h 份并行，每头维度 d_k = d_model/h。
</details>

## 4. 位置编码为什么必需？
<details><summary>答案</summary>
自注意力对输入置换等变，没有位置就丢失顺序信息。需要显式注入位置。
</details>

## 5. 论文用正弦位置编码有什么好处？
<details><summary>答案</summary>
无需学习参数，且相对位置可由线性变换表示，理论上可外推到更长序列。
</details>

## 6. self-attention 的复杂度？瓶颈？
<details><summary>答案</summary>
O(n^2 · d)。瓶颈是 n^2 部分——序列长度平方，长序列时内存和计算爆炸。
</details>

## 7. 为什么用 LayerNorm 不用 BatchNorm？
<details><summary>答案</summary>
序列任务 batch 内长度不一、统计量随序列变化，BN 不稳定；LN 对每个样本在特征维归一化，不依赖 batch。
</details>

## 8. padding mask 和 causal mask 分别用在哪？
<details><summary>答案</summary>
padding mask 屏蔽补齐的无效位置，encoder/decoder 都用；causal mask 屏蔽未来位置，只用在 decoder。
</details>

## 9. 复现代码里注意力矩阵上三角为什么是 0？
<details><summary>答案</summary>
causal mask 把未来位置置为 -inf，softmax 后变 0，保证位置 t 只看到 ≤t 的 token。
</details>

## 10. 陷阱：注意力能建模所有长距离依赖吗？
<details><summary>答案</summary>
能一步覆盖任意距离，但权重是数据学出来的，可能过度平滑/分散；复杂度也限制了实际长度。
</details>
