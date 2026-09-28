# Checkpoint 2：Transformer 自测

每题先自己作答，再展开答案对照。对 8/10 以上算通过。

> 答案不只是结论——每题附推理过程和论文出处，答错了回头看推理。

## 1. 写出 scaled dot-product attention 公式。
<details><summary>答案</summary>

**结论**：`Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) V`

**推理**：Q（查询）、K（键）、V（值）都是输入序列的线性投影。QK^T 算的是每个位置对其他位置的"关注强度"（相似度），除以 sqrt(d_k) 缩放，softmax 归一化成权重，最后加权求和 V 得到新表示。整个操作是**全并行的**——没有循环，没有时序依赖。

**出处**：3.2.1 节式 (1)。
</details>

## 2. 为什么要除以 sqrt(d_k)？
<details><summary>答案</summary>

**结论**：q·k 的方差随 d_k 增大而增大，softmax 会进入饱和区导致梯度过小。除以 sqrt(d_k) 把方差拉回 1。

**推理**：设 q 和 k 的每个分量独立同分布、均值为 0 方差为 1，则 `q·k = Σ q_i·k_i` 的方差是 d_k。d_k=512 时，点积的绝对值可能到几百。softmax 对大数值会饱和（梯度趋近 0），训练停滞。除以 sqrt(d_k) 后，方差回到 1，softmax 工作在线性区。

**出处**：3.2.1 节脚注 4。
</details>

## 3. 多头的计算量比单头大吗？为什么？
<details><summary>答案</summary>

**结论**：基本相当。因为总维度不变，多头把 d_model 切成 h 份并行，每头维度 d_k = d_model/h。

**推理**：单头注意力在 d_model 维上做一次 QK^T，计算量正比于 `n^2 · d_model`。多头把 d_model 拆成 h 个头，每头在 d_model/h 维上做 QK^T，计算量是 `h · n^2 · (d_model/h) = n^2 · d_model`。总计算量几乎不变，但模型能学到 h 种不同的"关注模式"。

**出处**：3.2.2 节（"the total computational cost is similar to that of single-head attention with full dimensionality"）。
</details>

## 4. 位置编码为什么必需？
<details><summary>答案</summary>

**结论**：自注意力对输入置换等变，没有位置就丢失顺序信息。需要显式注入位置。

**推理**：自注意力的计算是集合操作——`Attention(Q,K,V)` 的输出只取决于 Q、K、V 的内容，和它们的排列顺序无关。你把句子打乱，注意力矩阵的行也会跟着乱，但每个词的新表示完全一样。语言里"狗咬人" ≠ "人咬狗"，顺序信息必须显式注入。

**出处**：3.5 节（"we must inject some information about the relative or absolute position of the tokens"）。
</details>

## 5. 论文用正弦位置编码有什么好处？
<details><summary>答案</summary>

**结论**：无需学习参数，且相对位置可由线性变换表示，理论上可外推到更长序列。

**推理**：正弦编码 `PE(pos, 2i) = sin(pos / 10000^(2i/d_model))` 是固定函数，不增加可学习参数。更关键的是：对任意偏移 k，`PE(pos+k)` 可以表示为 `PE(pos)` 的线性函数——模型容易学到"相对位置"。此外，正弦函数是连续的，理论上可以外推到训练时没见过的更长序列。

**出处**：3.5 节。
</details>

## 6. self-attention 的复杂度？瓶颈？
<details><summary>答案</summary>

**结论**：O(n^2 · d)。瓶颈是 n^2 部分——序列长度平方，长序列时内存和计算爆炸。

**推理**：QK^T 是 n×n 矩阵，存储和计算都是 O(n^2)。d（特征维）是线性的，n（序列长）是平方的。当 n=10000 时，注意力矩阵有 1 亿个元素，显存和计算都吃不消。这是 Transformer 处理长文本的根本瓶颈。

**出处**：3.2.1 节（提到"for large values of d_k"）+ 后续 Efficient Transformers 综述。
</details>

## 7. 为什么用 LayerNorm 不用 BatchNorm？
<details><summary>答案</summary>

**结论**：序列任务 batch 内长度不一、统计量随序列变化，BN 不稳定；LN 对每个样本在特征维归一化，不依赖 batch。

**推理**：BN 在 batch 维上归一化，假设 batch 内所有样本的统计量一致。但序列任务里，batch 内句子长度不同，padding 位置会污染均值/方差。LN 改为对每个样本在特征维（d_model）上归一化，完全不依赖 batch，不受长度不齐影响。

**出处**：论文未明说，但这是后续研究的共识；可参考 LayerNorm 原论文（Ba et al., 2016）。
</details>

## 8. padding mask 和 causal mask 分别用在哪？
<details><summary>答案</summary>

**结论**：padding mask 屏蔽补齐的无效位置，encoder/decoder 都用；causal mask 屏蔽未来位置，只用在 decoder。

**推理**：padding mask 是为了让注意力忽略 batch 内为了对齐长度而补的 `<pad>` token——这些位置没有实际意义。causal mask 是为了防止 decoder 在预测第 t 个词时"偷看"到第 t+1 个词——这在训练时必须屏蔽，否则模型直接抄答案。encoder 没有这个问题，因为它看到整个输入序列。

**出处**：3.2.3 节（"We also modify the self-attention sub-layer in the decoder stack to prevent positions from attending to subsequent positions"）。
</details>

## 9. 复现代码里注意力矩阵上三角为什么是 0？
<details><summary>答案</summary>

**结论**：causal mask 把未来位置置为 -inf，softmax 后变 0，保证位置 t 只看到 ≤t 的 token。

**推理**：在 `tiny_attention.py` 里，causal mask 是一个上三角矩阵，上半部分（j > i 的位置）被设为 -inf。softmax(-inf) = 0，所以注意力矩阵的上三角全是 0——位置 i 对所有未来位置 j 的注意力权重为 0，实现了"只看过去"的约束。

**出处**：复现代码 `code/transformer/tiny_attention.py` + 3.2.3 节。
</details>

## 10. 陷阱：注意力能建模所有长距离依赖吗？
<details><summary>答案</summary>

**结论**：能一步覆盖任意距离，但权重是数据学出来的，可能过度平滑/分散；复杂度也限制了实际长度。

**推理**：理论上，自注意力的任意两个位置之间都有直接连接，距离为 1。但实践中：(1) 注意力权重是 softmax 归一化的，如果序列很长，权重会被摊薄，真正的长距离依赖可能被稀释；(2) O(n^2) 复杂度让你无法处理无限长的序列；(3) 学习到的权重模式依赖数据，不保证捕捉到所有依赖关系。

**出处**：这是对注意力机制的理论分析，论文 4 节的实验（长距离依赖任务上表现好）只是经验证据。
</details>
