# drawio-generator

> 用自然语言描述，让 AI 自动生成符合规范样式的 `.drawio` 文件。

## 功能特性

- ✅ **自然语言驱动**：通过 AI Skill 将自然语言转为 .drawio 文件
- ✅ **规范样式内置**：Action 蓝色圆角、流程方框、折角连线、注意便签黄色
- ✅ **自动类型推断**：根据节点名称关键词自动判断节点类型和样式
- ✅ **自动层级布局**：BFS 算法自动计算节点坐标，无需手动定位
- ✅ **多图类型支持**：流程图、架构图、时序图等
- ✅ **CLI + stdin**：支持文件输入和 pipe 流式输入

## 快速开始

### 安装依赖

```bash
npm install
npm run build
```

### 从 JSON 文件生成

```bash
node dist/index.js --input examples/payment-flow.json --output output.drawio
```

### 通过 stdin pipe

```bash
echo '{"title":"简单流程","nodes":[{"id":"a","label":"开始","type":"start"},{"id":"b","label":"处理","type":"process"},{"id":"c","label":"结束","type":"end"}],"edges":[{"source":"a","target":"b"},{"source":"b","target":"c"}]}' | node dist/index.js --output simple.drawio
```

## 使用 AI Skill（推荐方式）

在 CodeFlicker 中，直接用自然语言描述图的内容即可：

```
帮我画一个支付流程图，包括：
- 客户端调用 applyPay RPC 接口
- CorePayCheckBizAction 校验支付单是否存在
  - 已存在且成功 → 返回 ALREADY_PAYED
  - 不存在 → 继续后续流程
- MerchantCheckBizAction 校验商户
- MemberCheckBizAction 校验会员
- PayAntispamCheckBizAction 风控校验
  - 拒绝 → 返回风控拒绝
  - 通过 → CorePayBuildAction 构建支付单
```

AI 会自动生成对应的 .drawio 文件。

## 输入 JSON 格式

```json
{
  "title": "图标题",
  "type": "flowchart",
  "nodes": [
    { "id": "n1", "label": "节点文字\n可以换行", "type": "start" },
    { "id": "n2", "label": "1. XxxAction\n功能描述", "type": "action" },
    { "id": "n3", "label": "是否满足条件?", "type": "decision" },
    { "id": "n4", "label": "处理逻辑", "type": "process" },
    { "id": "n5", "label": "返回成功", "type": "end" },
    { "id": "n6", "label": "重要说明", "type": "note" },
    { "id": "n7", "label": "异步消费", "type": "async" }
  ],
  "edges": [
    { "source": "n1", "target": "n2" },
    { "source": "n2", "target": "n3", "label": "条件说明" },
    { "source": "n3", "target": "n4", "label": "是" },
    { "source": "n3", "target": "n5", "label": "否", "style": "dashed" }
  ],
  "layout": {
    "direction": "TB",
    "horizontalPadding": 60,
    "verticalPadding": 80
  }
}
```

## 节点类型与样式

| 类型 | 形状 | 颜色 | 适用场景 |
|------|------|------|---------|
| `process` | 方框 | 白色 | Helper、Service、处理逻辑 |
| `action` | 圆角矩形 | 蓝色 `#dae8fc` | BizAction、校验步骤 |
| `decision` | 菱形 | 白色 | 条件判断、分支 |
| `start` | 圆角矩形 | 绿色 `#d5e8d4` | RPC 接口、流程入口 |
| `end` | 椭圆 | 白色 | 返回值、流程终止 |
| `note` | 便签 | 黄色 `#ffffc0` | 重要说明、注意事项 |
| `async` | 虚线方框 | 灰色 `#f5f5f5` | 异步流程、MQ、Task |

**自动推断**：如果不指定 `type`，工具会根据 `label` 关键词自动推断（参考 `.codeflicker/skills/drawio-generator/references/node-type-guide.md`）。

## 连线样式

所有连线默认使用**折角模式（orthogonal）**：

| 样式 | 说明 |
|------|------|
| `default` | 普通折角连线 |
| `dashed` | 虚线连线（可选路径） |
| `async` | 异步连线（灰色虚线，开放箭头） |
| `thick` | 粗线（主干流程强调） |

## CLI 参数

```
node dist/index.js [options] [input-file]

OPTIONS:
  -i, --input <file>    输入 JSON 文件（不指定则从 stdin 读取）
  -o, --output <file>   输出 .drawio 文件路径（默认：output.drawio）
  -h, --help            显示帮助
  -v, --version         显示版本
```

## 项目结构

```
drawio-generator/
├── src/
│   ├── index.ts                  # CLI 入口
│   ├── generator/
│   │   ├── index.ts              # Generator 主逻辑
│   │   ├── style-resolver.ts     # 节点类型 → 样式字符串
│   │   ├── xml-builder.ts        # 构建 draw.io XML
│   │   └── layout-engine.ts      # 层级布局计算
│   └── types/
│       └── index.ts              # TypeScript 类型定义
├── .codeflicker/
│   └── skills/
│       └── drawio-generator/     # AI Skill（使用本工具）
│           ├── SKILL.md
│           └── references/
│               ├── style-guide.md
│               ├── node-type-guide.md
│               └── examples/
├── examples/
│   ├── payment-flow.json         # 示例输入
│   └── payment-flow.drawio       # 示例输出
├── package.json
└── tsconfig.json
```

## 打开生成的文件

- **VS Code**：安装 [Draw.io Integration](https://marketplace.visualstudio.com/items?itemName=hediet.vscode-drawio) 插件，直接在 VS Code 预览
- **在线**：上传到 https://app.diagrams.net/
- **桌面版**：使用 draw.io 桌面客户端打开
