# 论文精读工作空间 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建一个"问题驱动 + 最小复现"的论文精读工作空间，包含三篇论文原文、核心问题文档、可离线运行的最小复现代码与自测题库。

**Architecture:** 在 `03-research/paper-deep-dive/` 下建立独立工作空间。文档层（questions/papers/checkpoints）与代码层（code/）分离。三个复现脚本共用 `code/common/mnist.py` 数据加载器，每个脚本独立可运行、CPU 友好、带离线降级。

**Tech Stack:** Python 3.8+、NumPy（手写反向传播）、PyTorch（CPU）、torchvision/sklearn（数据）、matplotlib（可选可视化）

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `03-research/paper-deep-dive/README.md` | 计划总览、进度表、运行说明 |
| `03-research/paper-deep-dive/.gitignore` | 忽略数据缓存和输出图片 |
| `03-research/paper-deep-dive/questions/q1-why-deep-networks-fail.md` | Q1 问题文档 |
| `03-research/paper-deep-dive/questions/q2-why-attention-works.md` | Q2 问题文档 |
| `03-research/paper-deep-dive/questions/q3-why-diffusion-generates.md` | Q3 问题文档 |
| `03-research/paper-deep-dive/papers/resnet/notes.md` | ResNet 精读笔记模板 |
| `03-research/paper-deep-dive/papers/resnet/summary.md` | ResNet 一页纸总结模板 |
| `03-research/paper-deep-dive/papers/transformer/notes.md` | Transformer 精读笔记模板 |
| `03-research/paper-deep-dive/papers/transformer/summary.md` | Transformer 一页纸总结模板 |
| `03-research/paper-deep-dive/papers/ddpm/notes.md` | DDPM 精读笔记模板 |
| `03-research/paper-deep-dive/papers/ddpm/summary.md` | DDPM 一页纸总结模板 |
| `03-research/paper-deep-dive/code/requirements.txt` | 依赖清单 |
| `03-research/paper-deep-dive/code/common/__init__.py` | 包标记 |
| `03-research/paper-deep-dive/code/common/mnist.py` | MNIST 加载器（三级降级） |
| `03-research/paper-deep-dive/code/common/test_mnist.py` | 加载器测试 |
| `03-research/paper-deep-dive/code/resnet/plain_vs_residual.py` | Plain vs Residual 对比 |
| `03-research/paper-deep-dive/code/resnet/test_gradient.py` | 手写反向传播梯度校验 |
| `03-research/paper-deep-dive/code/resnet/README.md` | 复现说明与结果分析 |
| `03-research/paper-deep-dive/code/transformer/tiny_attention.py` | 单头注意力语言模型 |
| `03-research/paper-deep-dive/code/transformer/test_attention.py` | 因果掩码与形状测试 |
| `03-research/paper-deep-dive/code/transformer/README.md` | 复现说明与结果分析 |
| `03-research/paper-deep-dive/code/ddpm/simple_ddpm.py` | 简化版扩散模型 |
| `03-research/paper-deep-dive/code/ddpm/test_diffusion.py` | 前向加噪公式测试 |
| `03-research/paper-deep-dive/code/ddpm/README.md` | 复现说明与结果分析 |
| `03-research/paper-deep-dive/checkpoints/checkpoint-1-resnet.md` | ResNet 自测题 + 答案 |
| `03-research/paper-deep-dive/checkpoints/checkpoint-2-transformer.md` | Transformer 自测题 + 答案 |
| `03-research/paper-deep-dive/checkpoints/checkpoint-3-ddpm.md` | DDPM 自测题 + 答案 |

---

### Task 1: 工作空间引导文件

**Files:**
- Create: `03-research/paper-deep-dive/README.md`
- Create: `03-research/paper-deep-dive/.gitignore`
- Create: `03-research/paper-deep-dive/code/requirements.txt`

- [ ] **Step 1: 写 README.md**

```markdown
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
```

- [ ] **Step 2: 写 .gitignore**

```
data/
*.png
__pycache__/
*.pyc
```

- [ ] **Step 3: 写 requirements.txt**

```
numpy>=1.21
torch>=2.0
torchvision>=0.15
scikit-learn>=1.0
matplotlib>=3.5
pytest>=7.0
```

- [ ] **Step 4: 提交**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure
git add 03-research/paper-deep-dive/README.md 03-research/paper-deep-dive/.gitignore 03-research/paper-deep-dive/code/requirements.txt
git commit -m "docs(paper-deep-dive): bootstrap workspace with README and deps"
```

---

### Task 2: 核心问题文档

**Files:**
- Create: `03-research/paper-deep-dive/questions/q1-why-deep-networks-fail.md`
- Create: `03-research/paper-deep-dive/questions/q2-why-attention-works.md`
- Create: `03-research/paper-deep-dive/questions/q3-why-diffusion-generates.md`

- [ ] **Step 1: 写 Q1 问题文档**

```markdown
# Q1：为什么网络越深越难训练？

## 一句话问题

按理说更深的网络表达能力更强，为什么单纯堆叠层数反而让训练更难？

## 为什么这个问题重要

这是 ResNet 的出发点。理解它，才能理解残差连接到底解决了什么。

## 我的初始理解（学习前先写，不要看论文）

_在这里写下你现在的猜测。_

## 需要区分的两个概念

| 概念 | 含义 | 现象 |
|------|------|------|
| 梯度消失/爆炸 | 反向传播时梯度逐层相乘导致过大或过小 | 浅层几乎不更新 |
| 退化问题 (degradation) | 深层网络训练误差反而比浅层高 | 不是过拟合，训练集误差也更高 |

## 论文的核心主张

ResNet 提出：让网络学习残差 F(x) = H(x) - x，而不是直接学 H(x)，
则"恒等映射"变成把 F(x) 学成 0，比直接学 H(x)=x 容易。

## 子问题

1. 退化问题为什么不是过拟合导致的？论文用哪张图证明？
2. 一个残差块的公式是什么？shortcut 上有没有参数？
3. 当输入输出维度不一致时，shortcut 怎么处理？
4. 梯度通过 shortcut 回传时，为什么会"不衰减"？
5. 论文的 bottleneck 结构为什么要 1x1 -> 3x3 -> 1x1？

## 证据位置（读论文时填）

| 论点 | 论文位置 | 原文摘录 |
|------|---------|---------|
| 退化现象 | 图 1 | |
| 残差公式 | 式 (1)(2) | |
| 维度不匹配处理 | 3.3 节 | |
| 梯度流分析 | （后续论文/博客） | |

## 复现验证

跑 `code/resnet/plain_vs_residual.py`，对比 plain 与 residual 的浅层梯度范数。

## 我的结论（读完后写）

_待填。_
```

- [ ] **Step 2: 写 Q2 问题文档**

```markdown
# Q2：为什么注意力能替代序列建模？

## 一句话问题

RNN 必须按顺序计算，注意力为什么能打破这个限制，同时还建模得更好？

## 为什么这个问题重要

这是 Transformer 的出发点。理解它，才能理解为什么它成为大模型的基础架构。

## 我的初始理解（学习前先写）

_在这里写下你现在的猜测。_

## 论文要解决的两个痛点

| 痛点 | RNN 的问题 | 注意力的解法 |
|------|-----------|-------------|
| 顺序依赖 | 时刻 t 必须等 t-1 算完，无法并行 | 所有位置同时计算 |
| 长距离依赖 | 信息要经过多步传递，路径长度 O(n) | 任意两位置路径长度 O(1) |

## 论文的核心主张

只用注意力（不用循环、不用卷积）就能构建更强的序列模型，
关键是 Scaled Dot-Product Attention：

    Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V

## 子问题

1. 为什么要除以 sqrt(d_k)？不除会怎样？
2. 为什么要多头（multi-head）？单头不够吗？
3. 位置编码（Positional Encoding）为什么必需？它怎么加进去？
4. self-attention 的计算复杂度是多少？瓶颈在哪？
5. 为什么用 LayerNorm 而不是 BatchNorm？
6. 训练时的 mask 有哪两种，分别用在哪？

## 证据位置（读论文时填）

| 论点 | 论文位置 | 原文摘录 |
|------|---------|---------|
| 缩放因子解释 | 3.2.1 节脚注 | |
| 多头结构 | 3.2.2 节 | |
| 位置编码公式 | 3.5 节 | |
| 复杂度对比表 | 表 1 | |

## 复现验证

跑 `code/transformer/tiny_attention.py`，可视化注意力矩阵，验证因果掩码。

## 我的结论（读完后写）

_待填。_
```

- [ ] **Step 3: 写 Q3 问题文档**

```markdown
# Q3：为什么扩散模型能生成高质量样本？

## 一句话问题

从纯噪声直接生成图像很难，为什么"分很多小步去噪"反而能做到高质量？

## 为什么这个问题重要

这是 DDPM 的出发点。理解它，才能理解扩散模型为什么取代 GAN 成为主流生成模型。

## 我的初始理解（学习前先写）

_在这里写下你现在的猜测。_

## 论文的核心洞察

把"一步生成"拆成"T 步去噪"：
- 前向过程 q：对图像逐步加噪声，直到变成纯高斯噪声（无需学习，固定公式）
- 反向过程 p：训练网络逐步预测并减去噪声，还原图像

## 子问题

1. 前向过程为什么可以一步到位采样 x_t？公式是什么？
2. 为什么网络预测噪声 eps，而不是直接预测 x_0？
3. 损失函数为什么就是简单的 MSE？ELBO 推导到哪一步变成 MSE？
4. beta 调度（linear schedule）的作用是什么？
5. 采样公式里为什么 t>0 时要再加一次随机噪声？
6. 为什么反向过程需要 U-Net 这种带跳连的结构？

## 证据位置（读论文时填）

| 论点 | 论文位置 | 原文摘录 |
|------|---------|---------|
| 前向一步采样 | 式 (4) | |
| 简化损失 | 式 (14) | |
| 采样算法 | Algorithm 2 | |
| 训练算法 | Algorithm 1 | |

## 复现验证

跑 `code/ddpm/simple_ddpm.py`，观察加噪/去噪过程，生成数字图像。

## 我的结论（读完后写）

_待填。_
```

- [ ] **Step 4: 提交**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure
git add 03-research/paper-deep-dive/questions
git commit -m "docs(paper-deep-dive): add three core question documents"
```

---

### Task 3: 论文笔记与总结模板

**Files:**
- Create: `03-research/paper-deep-dive/papers/resnet/notes.md`
- Create: `03-research/paper-deep-dive/papers/resnet/summary.md`
- Create: `03-research/paper-deep-dive/papers/transformer/notes.md`
- Create: `03-research/paper-deep-dive/papers/transformer/summary.md`
- Create: `03-research/paper-deep-dive/papers/ddpm/notes.md`
- Create: `03-research/paper-deep-dive/papers/ddpm/summary.md`

- [ ] **Step 1: 写 ResNet notes.md 与 summary.md**

`papers/resnet/notes.md`：

```markdown
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
```

`papers/resnet/summary.md`：

```markdown
# ResNet 一页纸总结

## 一句话

## 解决的问题

## 核心方法

## 关键结果

## 对我的启发

## 仍然不懂的地方
```

- [ ] **Step 2: 写 Transformer notes.md 与 summary.md**

`papers/transformer/notes.md` 与 ResNet 同构，章节替换为：

```markdown
# Transformer 精读笔记

## 元信息

- 标题：Attention Is All You Need
- 作者：Vaswani et al.
- 年份 / 会议：2017 / NeurIPS
- 本地原文：[attention_is_all_you_need.pdf](attention_is_all_you_need.pdf)

## 速读记录（Week 1）
### 三段式结构图
### Introduction 的关键句
### 我的 3 个困惑点

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
```

`papers/transformer/summary.md` 复用与 ResNet 相同的六段结构。

- [ ] **Step 3: 写 DDPM notes.md 与 summary.md**

`papers/ddpm/notes.md` 章节替换为：

```markdown
# DDPM 精读笔记

## 元信息

- 标题：Denoising Diffusion Probabilistic Models
- 作者：Jonathan Ho, Ajay Jain, Pieter Abbeel
- 年份 / 会议：2020 / NeurIPS
- 本地原文：[ddpm.pdf](ddpm.pdf)

## 速读记录（Week 1）
### 三段式结构图
### Introduction 的关键句
### 我的 3 个困惑点

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
```

`papers/ddpm/summary.md` 复用六段结构。

- [ ] **Step 4: 提交**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure
git add 03-research/paper-deep-dive/papers
git commit -m "docs(paper-deep-dive): add reading note and summary templates"
```

---

### Task 4: MNIST 加载器（共用模块）

**Files:**
- Create: `03-research/paper-deep-dive/code/common/__init__.py`
- Create: `03-research/paper-deep-dive/code/common/mnist.py`
- Test: `03-research/paper-deep-dive/code/common/test_mnist.py`

- [ ] **Step 1: 写空包标记**

`common/__init__.py` 内容为空文件。

- [ ] **Step 2: 写失败测试**

`common/test_mnist.py`：

```python
import numpy as np
from common.mnist import load_mnist


def test_load_mnist_shapes_and_range():
    x_tr, y_tr, x_te, y_te = load_mnist(n_train=100, n_test=20)
    assert x_tr.shape == (100, 784)
    assert y_tr.shape == (100,)
    assert x_te.shape == (20, 784)
    assert y_te.shape == (20,)
    assert x_tr.dtype == np.float32
    assert y_tr.dtype == np.int64
    assert x_tr.min() >= 0.0 and x_tr.max() <= 1.0
    assert y_tr.min() >= 0 and y_tr.max() <= 9
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd 03-research/paper-deep-dive/code && python3 -m pytest common/test_mnist.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'common.mnist'`

- [ ] **Step 4: 实现加载器**

`common/mnist.py`：

```python
"""MNIST 加载器，三级降级保证离线可跑。

优先级：
1. torchvision（首次运行下载到 code/data/mnist）
2. sklearn fetch_openml（需联网）
3. 合成高斯团数据（纯离线兜底，会打印警告）
"""
import os
import numpy as np

CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mnist"
)


def _synthetic(n_train, n_test, dim=784, classes=10, seed=0):
    rng = np.random.default_rng(seed)
    centers = rng.normal(0.0, 1.0, size=(classes, dim)).astype(np.float32)

    def make(n, s):
        r = np.random.default_rng(s)
        y = r.integers(0, classes, size=n)
        x = centers[y] + r.normal(0.0, 1.2, size=(n, dim)).astype(np.float32)
        x = 1.0 / (1.0 + np.exp(-x))
        return x.astype(np.float32), y.astype(np.int64)

    xa, ya = make(n_train, seed + 1)
    xb, yb = make(n_test, seed + 2)
    return xa, ya, xb, yb


def load_mnist(n_train=2000, n_test=500, allow_synthetic=True):
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        import torchvision

        tr = torchvision.datasets.MNIST(root=CACHE_DIR, train=True, download=True)
        te = torchvision.datasets.MNIST(root=CACHE_DIR, train=False, download=True)
        x_tr = tr.data.numpy().reshape(-1, 784).astype(np.float32) / 255.0
        y_tr = tr.targets.numpy().astype(np.int64)
        x_te = te.data.numpy().reshape(-1, 784).astype(np.float32) / 255.0
        y_te = te.targets.numpy().astype(np.int64)
        print("[mnist] loaded real MNIST via torchvision")
        return x_tr[:n_train], y_tr[:n_train], x_te[:n_test], y_te[:n_test]
    except Exception as e:
        print(f"[mnist] torchvision unavailable ({type(e).__name__}), trying sklearn")

    try:
        from sklearn.datasets import fetch_openml

        d = fetch_openml("mnist_784", version=1, as_frame=False, parser="auto")
        x = d.data.astype(np.float32) / 255.0
        y = d.target.astype(np.int64)
        print("[mnist] loaded real MNIST via sklearn")
        return x[:n_train], y[:n_train], x[60000:60000 + n_test], y[60000:60000 + n_test]
    except Exception as e:
        print(f"[mnist] sklearn unavailable ({type(e).__name__}), using synthetic blobs")

    if not allow_synthetic:
        raise RuntimeError("No MNIST source available")
    print("[mnist] WARNING: using synthetic data, results are not real MNIST")
    return _synthetic(n_train, n_test)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd 03-research/paper-deep-dive/code && python3 -m pytest common/test_mnist.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure
git add 03-research/paper-deep-dive/code/common 03-research/paper-deep-dive/code/requirements.txt
git commit -m "feat(paper-deep-dive): add offline-tolerant MNIST loader"
```

---

### Task 5: ResNet 最小复现（Plain vs Residual）

**Files:**
- Create: `03-research/paper-deep-dive/code/resnet/plain_vs_residual.py`
- Test: `03-research/paper-deep-dive/code/resnet/test_gradient.py`
- Create: `03-research/paper-deep-dive/code/resnet/README.md`

- [ ] **Step 1: 写梯度校验测试（TDD）**

`resnet/test_gradient.py`：

```python
import numpy as np
from resnet.plain_vs_residual import DeepMLP, softmax


def _loss(net, x, y):
    logits = net.forward(x, {})
    p = softmax(logits)
    return -np.log(p[np.arange(len(y)), y] + 1e-12).mean()


def _numeric_grad(net, x, y, layer, r, c, eps=1e-5):
    orig = net.W[layer][r, c]
    net.W[layer][r, c] = orig + eps
    lp = _loss(net, x, y)
    net.W[layer][r, c] = orig - eps
    lm = _loss(net, x, y)
    net.W[layer][r, c] = orig
    return (lp - lm) / (2 * eps)


def _analytic_grad(net, x, y):
    cache = {}
    logits = net.forward(x, cache)
    p = softmax(logits)
    dlogits = p.copy()
    dlogits[np.arange(len(y)), y] -= 1.0
    dlogits /= len(y)
    return net.backward(cache, dlogits)


def test_backward_matches_finite_difference():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(4, 8)).astype(np.float64)
    y = rng.integers(0, 3, size=4)
    for residual in (False, True):
        net = DeepMLP(in_dim=8, hidden=6, n_layers=4, n_classes=3,
                      residual=residual, seed=1)
        net.W = [w.astype(np.float64) for w in net.W]
        grads = _analytic_grad(net, x, y)
        for (layer, r, c) in [(0, 0, 0), (2, 1, 3), (4, 0, 1)]:
            num = _numeric_grad(net, x, y, layer, r, c)
            ana = grads[layer][r, c]
            assert abs(num - ana) < 1e-6, (residual, layer, r, c, num, ana)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd 03-research/paper-deep-dive/code && python3 -m pytest resnet/test_gradient.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'resnet.plain_vs_residual'`

- [ ] **Step 3: 实现 DeepMLP 与训练脚本**

`resnet/plain_vs_residual.py`：

```python
"""Plain vs Residual 深层 MLP，手写前向与反向传播。

回答 Q1：为什么网络越深越难训练？残差连接如何缓解？

Run:  python3 resnet/plain_vs_residual.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.mnist import load_mnist


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def xavier(rng, fan_in, fan_out):
    return rng.normal(0.0, np.sqrt(1.0 / fan_in), size=(fan_in, fan_out)).astype(np.float32)


class DeepMLP:
    """全连接深层网络；residual=True 时每 2 层加一个恒等 shortcut。

    记 h[0]=x，第 i 层 a[i]=sigmoid(h[i] @ W[i])，则
      h[i+1] = a[i]                （普通层）
      h[i+1] = a[i] + h[i-1]       （i 为奇数时为残差块出口）
    输出 logits = h[L] @ W[L]。

    维度说明（实现时发现的必要修正）：
    第 0 层是 stem（in_dim -> hidden），故 h[0] 宽度为 in_dim，而 a[1] 宽度为 hidden。
    当 in_dim != hidden 时 i=1 的恒等 shortcut 宽度不匹配、无法相加。因此只在
    h[i-1] 与 a[i] 宽度一致时才加 shortcut（真实 ResNet 此处用 1x1 投影；本实现
    为保持手写反向简洁而跳过）。forward 与 backward 共用 `_block_skip` 判定，
    确保梯度索引 +G[i+2] 与真实计算图一致。
    """

    def __init__(self, in_dim=784, hidden=128, n_layers=20, n_classes=10,
                 residual=False, seed=0):
        assert n_layers % 2 == 0, "n_layers must be even (residual blocks of 2)"
        self.residual = residual
        self.n_layers = n_layers
        rng = np.random.default_rng(seed)
        dims = [in_dim] + [hidden] * n_layers + [n_classes]
        self.W = [xavier(rng, dims[i], dims[i + 1]) for i in range(len(dims) - 1)]

    def _block_skip(self, j, h, a):
        return (
            self.residual
            and j % 2 == 1
            and j - 1 < len(h)
            and j < len(a)
            and h[j - 1].shape == a[j].shape
        )

    def forward(self, x, cache):
        L = self.n_layers
        h = [x]
        a = []
        for i in range(L):
            ai = sigmoid(h[i] @ self.W[i])
            a.append(ai)
            if self._block_skip(i, h, a):
                h.append(ai + h[i - 1])
            else:
                h.append(ai)
        logits = h[L] @ self.W[L]
        cache["h"] = h
        cache["a"] = a
        return logits

    def backward(self, cache, dlogits):
        h = cache["h"]
        a = cache["a"]
        L = self.n_layers
        grads = [None] * (L + 1)
        G = [None] * (L + 2)
        grads[L] = h[L].T @ dlogits
        G[L] = dlogits @ self.W[L].T
        for i in range(L - 1, -1, -1):
            dz = G[i + 1] * a[i] * (1.0 - a[i])
            grads[i] = h[i].T @ dz
            gi = dz @ self.W[i].T
            if self.residual and (i % 2 == 0) and (i + 2 <= L) and self._block_skip(i + 1, h, a):
                gi = gi + G[i + 2]
            G[i] = gi
        return grads


def train(residual, steps=500, batch=64, lr=0.1, seed=0):
    x_tr, y_tr, x_te, y_te = load_mnist(n_train=6000, n_test=1000)
    net = DeepMLP(residual=residual, seed=seed)
    rng = np.random.default_rng(seed)
    losses, g0 = [], []
    for _ in range(steps):
        idx = rng.integers(0, len(x_tr), batch)
        xb, yb = x_tr[idx], y_tr[idx]
        cache = {}
        logits = net.forward(xb, cache)
        p = softmax(logits)
        loss = -np.log(p[np.arange(batch), yb] + 1e-12).mean()
        dlogits = p.copy()
        dlogits[np.arange(batch), yb] -= 1.0
        dlogits /= batch
        grads = net.backward(cache, dlogits)
        for i in range(len(net.W)):
            net.W[i] -= lr * grads[i]
        losses.append(float(loss))
        g0.append(float(np.linalg.norm(grads[0])))
    return net, losses, g0


def main():
    result = {}
    for name, res in [("plain", False), ("residual", True)]:
        net, losses, g0 = train(res)
        result[name] = (losses, g0)
        print(f"[{name:8s}] loss {losses[0]:.4f} -> {losses[-1]:.4f} | "
              f"mean |grad layer-0| = {np.mean(g0[10:]):.3e}")
    g_plain = np.mean(result["plain"][1][10:])
    g_res = np.mean(result["residual"][1][10:])
    print(f"\n浅层梯度范数比 residual/plain = {g_res / (g_plain + 1e-30):.3e}")
    print("结论：plain 网络浅层梯度趋近于 0（梯度消失），残差连接保住了梯度通路。")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(10, 4))
        for name in result:
            ax[0].plot(result[name][0], label=name)
            ax[1].plot(result[name][1], label=name)
        ax[0].set_title("training loss")
        ax[1].set_title("|grad| at layer 0")
        ax[1].set_yscale("log")
        for a in ax:
            a.legend()
            a.grid(alpha=0.3)
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.png")
        fig.tight_layout()
        fig.savefig(out, dpi=120)
        print(f"图已保存: {out}")
    except Exception as e:
        print(f"[plot skipped] {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd 03-research/paper-deep-dive/code && python3 -m pytest resnet/test_gradient.py -v`
Expected: PASS（梯度校验通过，说明手写反向传播正确）

- [ ] **Step 5: 运行训练脚本**

Run: `cd 03-research/paper-deep-dive/code && python3 resnet/plain_vs_residual.py`
Expected: 打印两行 loss 与梯度范数，`residual/plain` 比值远大于 1（通常 > 1e6）

- [ ] **Step 6: 写复现说明**

`resnet/README.md`：

```markdown
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

记录你跑出来的：
| 配置 | 起始 loss | 结束 loss | 浅层梯度范数均值 |
|------|----------|----------|----------------|
| plain | | | |
| residual | | | |

## 结论

_待你填写。_

## 动手实验（改一处参数再做一次）

1. 把激活函数换成 ReLU，梯度消失现象还明显吗？
2. 把层数改成 4 层，plain 和 residual 还有区别吗？
3. 把 `hidden` 改成 32，观察差异是否变化。
```

- [ ] **Step 7: 提交**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure
git add 03-research/paper-deep-dive/code/resnet
git commit -m "feat(paper-deep-dive): add plain-vs-residual demo with gradient check"
```

---

### Task 6: Transformer 最小复现（单头注意力）

**Files:**
- Create: `03-research/paper-deep-dive/code/transformer/tiny_attention.py`
- Test: `03-research/paper-deep-dive/code/transformer/test_attention.py`
- Create: `03-research/paper-deep-dive/code/transformer/README.md`

- [ ] **Step 1: 写测试（TDD）**

`transformer/test_attention.py`：

```python
import torch
from transformer.tiny_attention import SingleHeadAttention, load_text, CharTokenizer


def test_attention_shape_and_causality():
    torch.manual_seed(0)
    attn = SingleHeadAttention(n_embd=16, block_size=8)
    x = torch.randn(2, 5, 16)
    out, att = attn(x, return_attn=True)
    assert out.shape == (2, 5, 16)
    assert att.shape == (2, 5, 5)
    for b in range(2):
        for i in range(5):
            for j in range(i + 1, 5):
                assert att[b, i, j].item() == 0.0, "future position must be masked"
    assert torch.allclose(att.sum(dim=-1), torch.ones(2, 5), atol=1e-5)


def test_tokenizer_roundtrip():
    text = load_text()
    tok = CharTokenizer(text)
    s = text[:50]
    assert tok.decode(tok.encode(s)) == s
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd 03-research/paper-deep-dive/code && python3 -m pytest transformer/test_attention.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'transformer.tiny_attention'`

- [ ] **Step 3: 实现注意力语言模型**

`transformer/tiny_attention.py`：

```python
"""单头自注意力字符级语言模型（Tiny Shakespeare）。

回答 Q2：为什么注意力能替代序列建模？

Run:  python3 transformer/tiny_attention.py
"""
import math
import os
import sys
import urllib.request

import torch
import torch.nn as nn
import torch.nn.functional as F

DATA_URL = ("https://raw.githubusercontent.com/karpathy/char-rnn/"
            "master/data/tinyshakespeare/input.txt")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input.txt")
FALLBACK = ("to be or not to be that is the question\n"
            "whether tis nobler in the mind to suffer\n") * 200


def load_text():
    if os.path.exists(CACHE):
        with open(CACHE, "r", encoding="utf-8") as f:
            return f.read()
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        urllib.request.urlretrieve(DATA_URL, CACHE)
        with open(CACHE, "r", encoding="utf-8") as f:
            print("[text] downloaded Tiny Shakespeare")
            return f.read()
    except Exception as e:
        print(f"[text] download failed ({type(e).__name__}), using fallback text")
        return FALLBACK


class CharTokenizer:
    def __init__(self, text):
        self.chars = sorted(set(text))
        self.stoi = {c: i for i, c in enumerate(self.chars)}
        self.itos = {i: c for c, i in self.stoi.items()}

    @property
    def vocab_size(self):
        return len(self.chars)

    def encode(self, s):
        return [self.stoi[c] for c in s]

    def decode(self, ids):
        return "".join(self.itos[i] for i in ids)


class SingleHeadAttention(nn.Module):
    def __init__(self, n_embd, block_size):
        super().__init__()
        self.Wq = nn.Linear(n_embd, n_embd, bias=False)
        self.Wk = nn.Linear(n_embd, n_embd, bias=False)
        self.Wv = nn.Linear(n_embd, n_embd, bias=False)
        self.scale = n_embd ** -0.5
        self.register_buffer("mask", torch.tril(torch.ones(block_size, block_size)).bool())

    def forward(self, x, return_attn=False):
        B, T, C = x.shape
        q, k, v = self.Wq(x), self.Wk(x), self.Wv(x)
        att = (q @ k.transpose(-2, -1)) * self.scale
        att = att.masked_fill(~self.mask[:T, :T], float("-inf"))
        att = F.softmax(att, dim=-1)
        out = att @ v
        return (out, att) if return_attn else out


class Block(nn.Module):
    def __init__(self, n_embd, block_size):
        super().__init__()
        self.ln1 = nn.LayerNorm(n_embd)
        self.attn = SingleHeadAttention(n_embd, block_size)
        self.ln2 = nn.LayerNorm(n_embd)
        self.ff = nn.Sequential(
            nn.Linear(n_embd, 4 * n_embd), nn.GELU(), nn.Linear(4 * n_embd, n_embd)
        )

    def forward(self, x, return_attn=False):
        if return_attn:
            a, att = self.attn(self.ln1(x), return_attn=True)
            x = x + a
            x = x + self.ff(self.ln2(x))
            return x, att
        x = x + self.attn(self.ln1(x))
        x = x + self.ff(self.ln2(x))
        return x


class TinyTransformer(nn.Module):
    def __init__(self, vocab_size, n_embd=64, block_size=32, n_layer=2):
        super().__init__()
        self.block_size = block_size
        self.tok_emb = nn.Embedding(vocab_size, n_embd)
        self.pos_emb = nn.Embedding(block_size, n_embd)
        self.blocks = nn.ModuleList([Block(n_embd, block_size) for _ in range(n_layer)])
        self.ln_f = nn.LayerNorm(n_embd)
        self.head = nn.Linear(n_embd, vocab_size)

    def forward(self, idx, return_attn=False):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device)
        x = self.tok_emb(idx) + self.pos_emb(pos)[None, :, :]
        att_last = None
        for blk in self.blocks:
            if return_attn:
                x, att_last = blk(x, return_attn=True)
            else:
                x = blk(x)
        x = self.ln_f(x)
        logits = self.head(x)
        return (logits, att_last) if return_attn else logits


def get_batch(data, block_size, batch, rng):
    ix = torch.randint(len(data) - block_size - 1, (batch,), generator=rng)
    x = torch.stack([data[i:i + block_size] for i in ix])
    y = torch.stack([data[i + 1:i + block_size + 1] for i in ix])
    return x, y


def main():
    torch.manual_seed(0)
    text = load_text()
    tok = CharTokenizer(text)
    data = torch.tensor(tok.encode(text), dtype=torch.long)
    n = int(0.9 * len(data))
    train_data = data[:n]

    model = TinyTransformer(tok.vocab_size)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
    rng = torch.Generator().manual_seed(0)

    steps, block_size, batch = 500, 32, 32
    for step in range(1, steps + 1):
        x, y = get_batch(train_data, block_size, batch, rng)
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, tok.vocab_size), y.reshape(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step % 100 == 0:
            print(f"step {step:4d}  loss {loss.item():.4f}")

    model.eval()
    with torch.no_grad():
        idx = torch.zeros((1, 1), dtype=torch.long)
        for _ in range(200):
            idx_cond = idx[:, -block_size:]
            logits, att = model(idx_cond, return_attn=True)
            probs = F.softmax(logits[:, -1, :], dim=-1)
            nxt = torch.multinomial(probs, 1)
            idx = torch.cat([idx, nxt], dim=1)
    print("\n生成样本:\n" + tok.decode(idx[0].tolist()))

    with torch.no_grad():
        x, _ = get_batch(train_data, block_size, 1, rng)
        _, att = model(x, return_attn=True)
    print("\n注意力矩阵（前 5x5，行=query，列=key，上三角应为 0）:")
    print(att[0, :5, :5].numpy().round(2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd 03-research/paper-deep-dive/code && python3 -m pytest transformer/test_attention.py -v`
Expected: PASS

- [ ] **Step 5: 运行训练脚本**

Run: `cd 03-research/paper-deep-dive/code && python3 transformer/tiny_attention.py`
Expected: loss 从 ~4.2 降到 ~2.0 以下，打印生成样本与注意力矩阵（上三角全 0）

- [ ] **Step 6: 写复现说明**

`transformer/README.md`：

```markdown
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
| 起始 loss | |
| 结束 loss | |
| 生成样本是否像英文 | |

## 动手实验

1. 把 `n_embd` 从 64 改成 16，看 loss 下降变慢多少。
2. 去掉 `masked_fill`，让模型能看到未来，生成质量如何变化？
3. 把注意力换成 2 头（复制一份 Wq/Wk/Wv 后拼接），观察效果。
4. 直接把 `att`（softmax 后）打印出来，验证每一行和为 1。
```

- [ ] **Step 7: 提交**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure
git add 03-research/paper-deep-dive/code/transformer
git commit -m "feat(paper-deep-dive): add single-head attention language model"
```

---

### Task 7: DDPM 最小复现（简化版扩散）

**Files:**
- Create: `03-research/paper-deep-dive/code/ddpm/simple_ddpm.py`
- Test: `03-research/paper-deep-dive/code/ddpm/test_diffusion.py`
- Create: `03-research/paper-deep-dive/code/ddpm/README.md`

- [ ] **Step 1: 写测试（TDD）**

`ddpm/test_diffusion.py`：

```python
import torch
from ddpm.simple_ddpm import Diffusion


def test_q_sample_limits():
    # T=1000（标准 DDPM horizon）使 alpha_bar[T-1] ~ 4e-5，"纯噪声"才成立；
    # T=100 时 alpha_bar[99] ~ 0.36，仅约 64% 噪声。t=0 用 atol=0.05 因
    # beta_start=1e-4 会注入 sqrt(1e-4)*noise = 0.01*noise。
    torch.manual_seed(0)
    diff = Diffusion(T=1000)
    x0 = torch.randn(8, 1, 28, 28)
    noise = torch.randn_like(x0)

    t0 = torch.zeros(8, dtype=torch.long)
    xt0 = diff.q_sample(x0, t0, noise)
    assert torch.allclose(xt0, x0, atol=0.05), "t=0 should be (almost) clean"

    tT = torch.full((8,), 999, dtype=torch.long)
    xtT = diff.q_sample(x0, tT, noise)
    assert torch.allclose(xtT, noise, atol=0.05), "t=T-1 should be (almost) pure noise"


def test_alpha_bar_monotonic():
    diff = Diffusion(T=100)
    ab = diff.alpha_bars
    assert torch.all(ab[1:] <= ab[:-1])
    assert ab[0] < 1.0 and ab[-1] > 0.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd 03-research/paper-deep-dive/code && python3 -m pytest ddpm/test_diffusion.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'ddpm.simple_ddpm'`

- [ ] **Step 3: 实现扩散模型**

`ddpm/simple_ddpm.py`：

```python
"""简化版 DDPM：在 MNIST 上做前向加噪与反向去噪。

回答 Q3：为什么扩散模型能生成高质量样本？

Run:  python3 ddpm/simple_ddpm.py
"""
import math
import os
import sys

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.mnist import load_mnist


class SinusoidalPosEmb(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, t):
        half = self.dim // 2
        freqs = torch.exp(torch.arange(half, device=t.device) * (-math.log(10000.0) / (half - 1)))
        emb = t[:, None].float() * freqs[None, :]
        return torch.cat([emb.sin(), emb.cos()], dim=-1)


class DoubleConv(nn.Module):
    def __init__(self, cin, cout, t_dim):
        super().__init__()
        self.conv1 = nn.Conv2d(cin, cout, 3, padding=1)
        self.conv2 = nn.Conv2d(cout, cout, 3, padding=1)
        self.norm1 = nn.GroupNorm(4, cout)
        self.norm2 = nn.GroupNorm(4, cout)
        self.t_proj = nn.Linear(t_dim, cout)

    def forward(self, x, t):
        h = self.norm1(F.silu(self.conv1(x)))
        h = h + self.t_proj(t)[:, :, None, None]
        h = self.norm2(F.silu(self.conv2(h)))
        return h


class TinyUNet(nn.Module):
    def __init__(self, base=32, t_dim=64):
        super().__init__()
        self.t_mlp = nn.Sequential(
            SinusoidalPosEmb(t_dim), nn.Linear(t_dim, t_dim), nn.SiLU(),
            nn.Linear(t_dim, t_dim),
        )
        self.inc = DoubleConv(1, base, t_dim)
        self.down1 = DoubleConv(base, base, t_dim)
        self.down2 = DoubleConv(base, base * 2, t_dim)
        self.mid = DoubleConv(base * 2, base * 2, t_dim)
        self.up2 = DoubleConv(base * 3, base, t_dim)
        self.up1 = DoubleConv(base * 2, base, t_dim)
        self.outc = nn.Conv2d(base, 1, 1)
        self.pool = nn.MaxPool2d(2)

    def forward(self, x, t):
        t = self.t_mlp(t)
        h0 = self.inc(x, t)
        h1 = self.down1(self.pool(h0), t)
        h2 = self.down2(self.pool(h1), t)
        m = self.mid(h2, t)
        u2 = F.interpolate(m, scale_factor=2, mode="nearest")
        u2 = self.up2(torch.cat([u2, h1], dim=1), t)
        u1 = F.interpolate(u2, scale_factor=2, mode="nearest")
        u1 = self.up1(torch.cat([u1, h0], dim=1), t)
        return self.outc(u1)


class Diffusion:
    def __init__(self, T=100, beta_start=1e-4, beta_end=0.02, device="cpu"):
        self.T = T
        self.device = device
        self.betas = torch.linspace(beta_start, beta_end, T, device=device)
        self.alphas = 1.0 - self.betas
        self.alpha_bars = torch.cumprod(self.alphas, dim=0)

    def q_sample(self, x0, t, noise):
        ab = self.alpha_bars[t].view(-1, 1, 1, 1)
        return ab.sqrt() * x0 + (1.0 - ab).sqrt() * noise

    def loss(self, model, x0):
        B = x0.shape[0]
        t = torch.randint(0, self.T, (B,), device=x0.device)
        noise = torch.randn_like(x0)
        xt = self.q_sample(x0, t, noise)
        pred = model(xt, t.float())
        return F.mse_loss(pred, noise)

    @torch.no_grad()
    def sample(self, model, n):
        x = torch.randn(n, 1, 28, 28, device=self.device)
        for t in reversed(range(self.T)):
            tt = torch.full((n,), t, device=self.device, dtype=torch.float)
            pred = model(x, tt)
            beta = self.betas[t]
            alpha = self.alphas[t]
            ab = self.alpha_bars[t]
            mean = (1.0 / alpha.sqrt()) * (x - (beta / (1.0 - ab).sqrt()) * pred)
            x = mean if t == 0 else mean + beta.sqrt() * torch.randn_like(x)
        return x


def main():
    torch.manual_seed(0)
    x_tr, _, _, _ = load_mnist(n_train=8000, n_test=100)
    x = torch.tensor(x_tr[:8000]).reshape(-1, 1, 28, 28)

    diff = Diffusion(T=100)
    model = TinyUNet()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)

    steps, batch = 800, 64
    for step in range(1, steps + 1):
        idx = torch.randint(0, len(x), (batch,))
        loss = diff.loss(model, x[idx])
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step % 100 == 0:
            print(f"step {step:4d}  mse {loss.item():.4f}")

    model.eval()
    samples = diff.sample(model, 16).clamp(-1, 1)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples.png")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        grid = samples.squeeze(1).cpu().numpy()
        fig, axes = plt.subplots(4, 4, figsize=(5, 5))
        for i, ax in enumerate(axes.flat):
            ax.imshow((grid[i] + 1) / 2, cmap="gray")
            ax.axis("off")
        fig.tight_layout()
        fig.savefig(out, dpi=120)
        print(f"生成样本已保存: {out}")
    except Exception as e:
        print(f"[plot skipped] {type(e).__name__}: {e}")
        torch.save(samples, os.path.join(os.path.dirname(out), "samples.pt"))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd 03-research/paper-deep-dive/code && python3 -m pytest ddpm/test_diffusion.py -v`
Expected: PASS（t=0 接近原图，t=T-1 接近噪声，符合式 (4)）

- [ ] **Step 5: 运行训练脚本**

Run: `cd 03-research/paper-deep-dive/code && python3 ddpm/simple_ddpm.py`
Expected: mse 从 ~1.0 降到 ~0.2 以下，生成 `ddpm/samples.png`（16 张数字）

- [ ] **Step 6: 写复现说明**

`ddpm/README.md`：

```markdown
# DDPM 最小复现：简化版扩散模型

## 目的

验证 Q3：逐步去噪可以学会生成；网络预测噪声 eps 等价于预测 x_{t-1} 的均值。

## 运行

    python3 ddpm/simple_ddpm.py

## 实现要点

- 前向：x_t = sqrt(alpha_bar_t) x_0 + sqrt(1 - alpha_bar_t) eps（一步到位，式 4）。
- 训练：随机 t，MSE(eps_pred, eps)（简化损失，式 14）。
- 采样：按式 (7) 递推 x_{t-1}，t>0 时再加 sqrt(beta_t) 噪声。
- U-Net：3 层下采样 + 3 层上采样 + 跳连，正弦时间嵌入注入每层。

## 观察

| 指标 | 数值 |
|------|------|
| 起始 mse | |
| 结束 mse | |
| 生成样本是否像数字 | |

## 动手实验

1. 把 T 从 100 改成 300，采样质量是否更好？耗时增加多少？
2. 把 `pred` 改成直接预测 x0，损失改成 MSE(x0_pred, x0)，对比效果。
3. 采样时永远不加噪声（DDIM 的确定性版本），看结果有何不同。
4. 只训练 100 步就采样，观察"欠训练"的模糊结果。
```

- [ ] **Step 7: 提交**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure
git add 03-research/paper-deep-dive/code/ddpm
git commit -m "feat(paper-deep-dive): add simplified DDPM on MNIST"
```

---

### Task 8: 自测题库（Checkpoints）

**Files:**
- Create: `03-research/paper-deep-dive/checkpoints/checkpoint-1-resnet.md`
- Create: `03-research/paper-deep-dive/checkpoints/checkpoint-2-transformer.md`
- Create: `03-research/paper-deep-dive/checkpoints/checkpoint-3-ddpm.md`

- [ ] **Step 1: 写 ResNet 自测**

```markdown
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
```

- [ ] **Step 2: 写 Transformer 自测**

```markdown
# Checkpoint 2：Transformer 自测

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
```

- [ ] **Step 3: 写 DDPM 自测**

```markdown
# Checkpoint 3：DDPM 自测

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
```

- [ ] **Step 4: 提交**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure
git add 03-research/paper-deep-dive/checkpoints
git commit -m "docs(paper-deep-dive): add three self-test checkpoints"
```

---

### Task 9: 全量验证与收尾

- [ ] **Step 1: 跑全部测试**

Run: `cd 03-research/paper-deep-dive/code && python3 -m pytest common resnet transformer ddpm -v`
Expected: 全部 PASS（7 个测试）

- [ ] **Step 2: 冒烟运行三个脚本（各自加超时保护）**

Run: `cd 03-research/paper-deep-dive/code && python3 resnet/plain_vs_residual.py 2>&1 | tail -5`
Expected: 打印 `residual/plain` 比值 > 1

Run: `cd 03-research/paper-deep-dive/code && python3 transformer/tiny_attention.py 2>&1 | tail -12`
Expected: loss 明显下降 + 注意力矩阵上三角为 0

Run: `cd 03-research/paper-deep-dive/code && python3 ddpm/simple_ddpm.py 2>&1 | tail -5`
Expected: mse 下降 + 生成 samples.png

- [ ] **Step 3: 回写记忆**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure
python3 .memory/mem.py add "【paper-deep-dive】搭建论文精读工作空间：ResNet/Transformer/DDPM 三篇原文已下载到 03-research/paper-deep-dive/papers/。采用问题驱动+最小复现模式，三份 CPU 可跑复现代码（NumPy 手写反向传播对比 plain/residual；单头注意力字符语言模型；简化 DDPM+TinyUNet）均在 code/ 下，配 pytest 测试与三级降级数据加载器。关键决策：复现聚焦核心机制而非完整论文规模，保证笔记本与离线可用。"
```

- [ ] **Step 4: 更新进度表占位并提交**

Run: `cd /Users/chenmao/Desktop/workspace/ai-instructure && git add 03-research/paper-deep-dive .memory && git commit -m "chore(paper-deep-dive): finalize workspace scaffold and memory"`
Expected: 提交成功

---

## 自检记录

**Spec 覆盖检查：**
- 三篇论文原文 → Task 1 README 索引 + 已下载 PDF ✅
- 核心问题树（3 个问题文档）→ Task 2 ✅
- 精读笔记 + 一页纸总结 → Task 3 ✅
- 最小复现 1（ResNet NumPy 手写）→ Task 5 + Task 4（数据）✅
- 最小复现 2（Transformer 单头注意力）→ Task 6 ✅
- 最小复现 3（DDPM 简化版）→ Task 7 ✅
- 自测验证（讲/推/复现/答）→ Task 8 ✅
- 进度追踪表 → Task 1 ✅
- 依赖环境 → Task 1 requirements + README ✅
- 风险缓解（离线降级、CPU 友好、数据最小化）→ Task 4 三级降级 + 各脚本小规模 ✅

**占位符扫描：** 无 TBD/TODO；所有代码步骤含完整代码。

**类型一致性：** `DeepMLP.forward(x, cache)` / `backward(cache, dlogits)` 在实现与测试中一致；`SingleHeadAttention(n_embd, block_size)` 与 `forward(x, return_attn)` 一致；`Diffusion(T)` / `q_sample(x0, t, noise)` / `loss(model, x0)` / `sample(model, n)` 一致；`load_mnist(n_train, n_test)` 返回 4 元组，全流程一致。
