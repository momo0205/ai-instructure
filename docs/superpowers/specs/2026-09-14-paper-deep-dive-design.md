# 论文精读学习计划设计文档

## 背景与目标

用户希望精读三篇经典论文（ResNet、Attention Is All You Need、DDPM），通过"问题驱动 + 最小复现"的方式真正学会算法核心思想。验证标准为"能复现"，时间每周 < 5 小时，硬件仅有笔记本（无 GPU）。

## 核心问题树

| 问题 | 论文 | 论文回答 | 复现验证 |
|------|------|---------|---------|
| **Q1: 为什么网络越深越难训练？** | ResNet | 梯度消失/退化问题 → 残差连接让梯度直接回传 | 手写 plain vs residual 块，对比 20 层网络在 MNIST 上的训练曲线 |
| **Q2: 为什么注意力能替代序列建模？** | Transformer | RNN 的顺序依赖 → 注意力全局并行计算 | 实现单头注意力，可视化注意力权重，验证并行性 |
| **Q3: 为什么扩散模型能生成高质量样本？** | DDPM | 逐步去噪比直接生成更容易学习 | 实现前向加噪 + 反向去噪，在 MNIST 上生成数字 |

## 工作空间结构

```
03-research/paper-deep-dive/
├── README.md                 # 学习计划总览 + 进度追踪
├── papers/                   # 论文原文 + 精读笔记
│   ├── resnet/
│   │   ├── resnet.pdf       # 已下载
│   │   ├── notes.md         # 精读笔记（带个人理解）
│   │   └── summary.md       # 一页纸总结
│   ├── transformer/
│   │   ├── attention_is_all_you_need.pdf  # 已下载
│   │   ├── notes.md
│   │   └── summary.md
│   └── ddpm/
│       ├── ddpm.pdf         # 已下载
│       ├── notes.md
│       └── summary.md
├── questions/                # 核心问题树（每篇一个）
│   ├── q1-why-deep-networks-fail.md
│   ├── q2-why-attention-works.md
│   └── q3-why-diffusion-generates.md
├── code/                     # 最小复现代码
│   ├── resnet/
│   │   ├── plain_vs_residual.py   # NumPy 手写对比
│   │   └── README.md              # 运行说明 + 结果分析
│   ├── transformer/
│   │   ├── tiny_attention.py      # 单头注意力 + Tiny Shakespeare
│   │   └── README.md
│   └── ddpm/
│       ├── simple_ddpm.py         # 简化版扩散模型
│       └── README.md
└── checkpoints/              # 自测验证
    ├── checkpoint-1-resnet.md     # 自测题 + 答案
    ├── checkpoint-2-transformer.md
    └── checkpoint-3-ddpm.md
```

## 三阶段学习循环（每篇论文）

每篇论文遵循相同的 5 步循环，单篇周期 2-3 周，总周期 6-9 周。

### Week 1: 问题建立 + 论文速读（1-1.5 小时）

**目标**：建立问题意识，了解论文全貌

**任务**：
1. 阅读问题文档，写下自己的初始理解（10 分钟）
2. 速读论文 Abstract / Introduction / Conclusion，画出论文结构图（20 分钟）
3. 浏览方法部分图表，猜测核心思想（15 分钟）
4. 记录 3 个最困惑的问题（15 分钟）

**输出物**：
- 问题文档（含初始理解 + 困惑点）
- 论文结构笔记（手绘/文字均可）

### Week 2: 精读 + 核心公式推导（2-2.5 小时）

**目标**：深入理解核心机制，手动推导关键公式

**任务**：
1. 逐节精读，重点公式手动推导（拍照/手写存档）
2. 阅读辅助材料（博客/视频）验证理解
3. 用代码片段验证公式（如用 NumPy 实现注意力分数计算）

**输出物**：
- 精读笔记（含公式推导过程 + 个人理解）
- 辅助材料链接 + 关键截图

### Week 3: 最小复现 + 自测（1.5-2 小时）

**目标**：通过代码复现验证理解，完成自测

**任务**：
1. 运行/调试/理解最小复现代码
2. 修改代码做实验（如换激活函数、调参、改层数）
3. 完成自测题，写总结

**输出物**：
- 可运行代码 + 实验记录
- 自测题答案 + 一页纸总结

## 最小复现详细设计

### 复现 1: ResNet — Plain vs Residual 对比

**文件**：`code/resnet/plain_vs_residual.py`

**核心思路**：用 NumPy 手写前向传播和反向传播，对比 plain block 和 residual block 在 20 层网络中的梯度流动。

**网络结构**：
- 输入：28x28 MNIST 图像（展平为 784 维）
- 隐藏层：20 层全连接层，每层 128 神经元
- 输出：10 类分类

**对比组**：
- Plain Block：标准 Linear → ReLU
- Residual Block：Linear → ReLU → + shortcut（跨 2 层）

**验证点**：
- 训练 1000 步，记录每层的梯度范数
- 绘制训练 loss 曲线
- 观察 plain 网络是否出现梯度消失

**技术栈**：NumPy（手写前向/反向），MNIST（sklearn 加载）

**预计代码量**：~150 行

**CPU 运行时间**：< 5 分钟

### 复现 2: Transformer — 单头注意力

**文件**：`code/transformer/tiny_attention.py`

**核心思路**：用 PyTorch 实现单头注意力机制，在 Tiny Shakespeare 数据集上训练字符级语言模型。

**核心组件**：
- Token Embedding + Positional Encoding
- Single-Head Self-Attention（Q, K, V 计算）
- Feed-Forward Network
- LayerNorm + Residual Connection

**验证点**：
- 训练 500 步，观察 loss 下降
- 可视化注意力权重矩阵（8x8 热力图）
- 生成一段文本，验证模型学会了字符级模式

**技术栈**：PyTorch（高层 API），Tiny Shakespeare（~1MB）

**预计代码量**：~200 行

**CPU 运行时间**：< 10 分钟

### 复现 3: DDPM — 简化版扩散模型

**文件**：`code/ddpm/simple_ddpm.py`

**核心思路**：实现前向加噪过程和反向去噪过程，用简单 U-Net 在 MNIST 上生成数字。

**核心组件**：
- 前向过程：逐步添加高斯噪声（T=100 步）
- 反向过程：训练 U-Net 预测噪声，逐步去噪
- 损失函数：预测噪声与真实噪声的 MSE

**简化点**：
- U-Net 简化为 3 层下采样 + 3 层上采样
- T=100 而非 1000
- 单通道 MNIST 而非 RGB

**验证点**：
- 训练 1000 步，观察 loss 下降
- 从纯噪声生成 16 张 MNIST 数字图像
- 可视化前向加噪和反向去噪过程

**技术栈**：PyTorch（基础张量操作），MNIST

**预计代码量**：~180 行

**CPU 运行时间**：< 15 分钟

## 自测验证标准（每篇完成标志）

每篇论文完成后，需通过以下 4 项验证：

1. **讲得清**：能口头解释核心思想（录音自听或讲给别人，3 分钟）
2. **推得动**：核心公式有手写推导痕迹（拍照存档到 `papers/<paper>/derivations/`）
3. **复现得了**：代码能跑通，理解每行作用，能修改做实验
4. **答得对**：自测题 80% 正确率（`checkpoints/checkpoint-N-<paper>.md`）

## 进度追踪

在 `README.md` 中维护进度表：

| 论文 | Week 1 | Week 2 | Week 3 | 状态 |
|------|--------|--------|--------|------|
| ResNet | ☐ | ☐ | ☐ | 未开始 |
| Transformer | ☐ | ☐ | ☐ | 未开始 |
| DDPM | ☐ | ☐ | ☐ | 未开始 |

## 依赖环境

- Python 3.8+
- NumPy
- PyTorch（CPU 版本即可）
- scikit-learn（加载 MNIST）
- matplotlib（可视化）

安装命令：
```bash
pip install numpy torch scikit-learn matplotlib
```

## 风险与缓解

| 风险 | 概率 | 缓解措施 |
|------|------|---------|
| 公式推导卡住 | 中 | 提供辅助材料链接，允许跳过非核心公式 |
| 代码调试耗时 | 中 | 提供完整可运行代码，用户以理解和修改为主 |
| 时间不足 | 高 | 每篇允许延长 1 周，总周期不超过 12 周 |
| 笔记本性能不足 | 低 | 所有复现代码针对 CPU 优化，数据量最小化 |

## 后续扩展（可选）

完成三篇论文后，可根据兴趣选择：
- 阅读 ResNet 后续工作（ResNeXt、DenseNet、EfficientNet）
- 阅读 Transformer 后续工作（BERT、GPT、ViT）
- 阅读 Diffusion 后续工作（DDIM、Stable Diffusion、DALL-E）
- 将三篇思想结合（如 Diffusion Transformer）
