# DDPM 精读笔记

## 元信息

- 标题：Denoising Diffusion Probabilistic Models
- 作者：Jonathan Ho, Ajay Jain, Pieter Abbeel
- 年份 / 会议：2020 / NeurIPS
- 本地原文：[ddpm.pdf](ddpm.pdf)

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

### 2 前向过程 q(x_t|x_{t-1})

### 3 反向过程与 ELBO

### 3.2 简化损失 L_simple

### 4 模型架构与 beta 调度

## 公式推导（手写稿索引）

| 公式 | 含义 | 手写稿路径 |
|------|------|-----------|
| q(x_t|x_0)=N(√ᾱ_t x_0, (1-ᾱ_t)I) | 前向一步采样 | derivations/01.png |
| L_simple = E‖ε-ε_θ(x_t,t)‖² | 简化损失 | derivations/02.png |
| x_{t-1} 采样公式 | 反向去噪 | derivations/03.png |

## 我的理解

_用自己的话写，不许抄论文。_
