# Skill Generator 🛠️

> 每日自动爬取互联网上实用的技能/工具资讯，并通过 AI 生成结构化中文文档。

## 项目简介

**Skill Generator** 是一个轻量化的全栈 Demo 项目，核心功能包括：

1. **定时爬取** — 每天定时从多个数据源爬取当日热门技能/工具
2. **AI 文档生成** — 调用 LLM API 自动生成详细中文文档（含功能介绍、最佳实践等）
3. **Web 展示** — 提供现代化的前端界面浏览和检索技能
4. **手动触发** — 支持一键触发爬取，灵活控制

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端 | Python 3.11 + FastAPI + SQLModel |
| 数据库 | SQLite（零配置） |
| 爬虫 | httpx + BeautifulSoup4 |
| 调度器 | APScheduler |
| AI | OpenAI / DeepSeek API |
| 前端 | Vue 3 + TypeScript + Vite |
| UI | Naive UI |

## 数据来源

| 来源 | 说明 |
|------|------|
| GitHub Trending | 当日趋势开源项目 |
| Hacker News | 当日热门技术新闻 |
| Dev.to | 当日热门技术文章 |
| Product Hunt | 当日热门产品/工具 |

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- npm / pnpm

### 1. 克隆项目

```bash
git clone <repo-url>
cd skill-generator
```

### 2. 配置环境变量

```bash
cp .env.example backend/.env
# 编辑 backend/.env，填入你的 LLM API Key
```

### 3. 启动后端

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

后端将在 `http://localhost:8000` 启动，API 文档自动生成在 `http://localhost:8000/docs`。

### 4. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 `http://localhost:5173` 启动，已配置代理到后端 API。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/skills` | 获取技能列表（支持分页/搜索/过滤） |
| GET | `/api/skills/{id}` | 获取技能详情（含 AI 文档） |
| GET | `/api/jobs` | 获取爬取任务历史 |
| POST | `/api/jobs/trigger` | 手动触发一次爬取 |
| GET | `/api/health` | 健康检查 |

完整 API 文档访问：`http://localhost:8000/docs`

## 项目结构

```
skill-generator/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── models.py            # 数据模型
│   ├── database.py          # 数据库连接
│   ├── scheduler.py         # 定时任务
│   ├── crawler/             # 爬虫模块
│   │   ├── base.py          # 爬虫基类
│   │   ├── github_trending.py
│   │   ├── hackernews.py
│   │   ├── devto.py
│   │   └── producthunt.py
│   ├── doc_generator/       # AI 文档生成
│   │   ├── generator.py
│   │   └── prompts.py
│   ├── api/                 # API 路由
│   │   ├── skills.py
│   │   └── jobs.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── api/             # API 封装
│   │   ├── components/      # 组件
│   │   ├── pages/           # 页面
│   │   ├── router/          # 路由
│   │   └── stores/          # 状态管理
│   └── package.json
├── .env.example
└── README.md
```

## 配置说明

通过环境变量控制行为，详见 `.env.example`。关键配置：

- **LLM 配置**：支持 OpenAI 和 DeepSeek，通过 `OPENAI_BASE_URL` 切换
- **爬虫开关**：可单独启用/禁用各数据源
- **调度器**：可配置每日爬取时间和时区

## 使用流程

1. 启动后端和前端
2. 访问 `http://localhost:5173`
3. 点击「立即爬取」触发首次爬取
4. 等待爬取完成后，浏览技能列表
5. 点击任一技能查看 AI 生成的中文文档

## License

MIT
