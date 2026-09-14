# ResNet 精读笔记

## 元信息

- 标题：Deep Residual Learning for Image Recognition
- 作者：Kaiming He, Xiangyu Zhang, Shaoqing Ren, Jian Sun
- 年份 / 会议：2015 / CVPR 2016
- 本地原文：[resnet.pdf](resnet.pdf)

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

### 3.1 残差学习

_核心公式：y = F(x, {Wi}) + x_

### 3.2 恒等映射的 shortcut

### 3.3 网络架构（bottleneck）

### 3.4 实现细节

## 公式推导（手写稿索引）

| 公式 | 含义 | 手写稿路径 |
|------|------|-----------|
| y = F(x) + x | 残差块前向 | derivations/01.png |
| ∂L/∂x = ∂L/∂y (1 + ∂F/∂x) | 梯度回传（为什么缓解消失） | derivations/02.png |

## 我的理解

_用自己的话写，不许抄论文。_
