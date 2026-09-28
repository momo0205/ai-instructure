# Transformer 精读笔记

## 元信息

- 标题：Attention Is All You Need
- 作者：Vaswani et al.
- 年份 / 会议：2017 / NeurIPS
- 本地原文：[attention_is_all_you_need.pdf](attention_is_all_you_need.pdf)

## 速读记录（Week 1）

### 三段式结构图

_画出 Intro -> Method -> Experiments 的逻辑流。_

### Introduction 的关键句

> _摘录 2-3 句最关键的话，并翻译。_

### 我的 3 个困惑点

1.
2.
3.

## 精读记录（Week 2）

### 3.2.1 Scaled Dot-Product Attention

### 3.2.2 Multi-Head Attention

### 3.3 Position-wise Feed-Forward

### 3.5 Positional Encoding

## 公式推导（手写稿索引）

| 公式 | 含义 | 手写稿路径 |
|------|------|-----------|
| softmax(QK^T/√d_k)V | 注意力输出 | derivations/01.png |
| 为什么除以 √d_k | 方差分析 | derivations/02.png |
| PE(pos,2i) | 位置编码 | derivations/03.png |

## 我的理解

_用自己的话写，不许抄论文。_
