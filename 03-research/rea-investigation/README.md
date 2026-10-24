# REA 逆向工具实跑记

一篇研究文章：拿 REA（Reverse Engineer Anything）分析自己构造的正确版/缺陷版程序，
记录它的实际表现与边界。配 8 张架构与流程图。

## 文件

```
docs/kstack/
├── rea-ai-reverse-engineering.md   正文
└── assets/*.svg                    数据流、证据链、分工、请求流水线等
```

## 看

```bash
open 03-research/rea-investigation/docs/kstack/rea-ai-reverse-engineering.md
```

## 要点

文章的核心结论不是"REA 很强"，而是**它在证据不足时会老实说不知道**——
这对 Agent 工具的设计比准确率更有参考价值。适合在评估任何"自动分析"工具时对照阅读。
