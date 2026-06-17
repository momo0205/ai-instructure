# Mira Flutter 客户端设计文档

## 目标

为 Mira 投研系统（及未来服务）构建一个 Android 客户端，Flutter 技术栈，用于浏览和阅读服务端产出的 Markdown 报告。

## 整体架构

```
┌──────────────────┐       HTTP        ┌─────────────────────┐
│  Flutter 客户端   │ ◄──────────────► │  服务器              │
│  (Android APK)   │                   │  ┌───────────────┐  │
│                  │                   │  │ Mira 服务      │  │
│  · 服务列表       │  GET /api/...    │  │ (cron/手动)    │  │
│  · 报告列表       │                   │  │ → 产出 MD 文件 │  │
│  · MD 渲染阅读    │                   │  └──────┬────────┘  │
│  · 收藏/搜索/缓存 │                   │         ↓           │
│                  │                   │  /data/reports/     │
│                  │                   │  ┌───────────────┐  │
│                  │                   │  │ FastAPI 接口层  │  │
│                  │                   │  │ → 暴露 API      │  │
│                  │                   │  └───────────────┘  │
└──────────────────┘                   └─────────────────────┘
```

## 服务端设计

### 报告存储规范

```
/data/reports/
  {service}/
    {YYYY-MM-DD}/
      {report-id}.md
      meta.json              ← 可选，报告元信息
    index.json               ← 服务级报告索引
  services.json              ← 服务注册表
```

### API 端点

| 方法 | 路径 | 返回 |
|------|------|------|
| GET | `/api/services` | `[{id, name, description, report_count}]` |
| GET | `/api/services/{id}/reports` | `[{id, title, date, tags?, summary?}]` |
| GET | `/api/services/{id}/reports/{report_id}` | 原始 MD 文本 |

### 索引维护

服务端 cron / 手动脚本负责扫描 `/data/reports/` 目录，自动生成/更新 `index.json` 和 `services.json`。

### 报告产出流程

1. 服务（Mira cron 或手动触发）将报告写入 `/data/reports/{service}/{date}/{id}.md`
2. 执行索引更新脚本
3. 客户端下次拉取即可看到新报告

## 客户端设计

### 技术栈

| 层 | 选型 | 版本 |
|----|------|------|
| 框架 | Flutter | 3.x stable |
| 状态管理 | Provider + ChangeNotifier | - |
| 网络 | dio | ^5.x |
| Markdown | flutter_markdown | ^0.7.x |
| 本地数据库 | sqflite | ^2.x |
| 键值存储 | shared_preferences | ^2.x |
| UI | Material 3 | 内置 |

### 页面结构

```
MaterialApp
├── SettingsPage          ← 服务器地址配置（首次启动必填）
├── ServiceListPage       ← 展示所有服务，入口首页
│   └── ReportListPage    ← 某服务的报告列表（按时间倒序）
│       └── ReportReadPage ← Markdown 渲染阅读
```

### 数据模型

```dart
class Service {
  final String id;
  final String name;
  final String description;
  final int reportCount;
}

class Report {
  final String id;
  final String serviceId;
  final String title;
  final DateTime date;
  final List<String> tags;
  final String? summary;
}
```

### 状态管理

```
ApiConfig (ChangeNotifier)
  - serverUrl: String

ReportStore (ChangeNotifier)
  - services: List<Service>
  - currentReports: List<Report>
  - loading: bool
  + fetchServices()
  + fetchReports(serviceId)
  + fetchReportContent(serviceId, reportId) → String

FavoritesStore (ChangeNotifier)
  - favorites: Set<String>   // reportId 集合
  + toggle(reportId)
  + isFavorite(reportId) → bool

CacheStore
  + get(serviceId, reportId) → String?
  + put(serviceId, reportId, content)
  + clear()
```

### 功能清单

| 功能 | 说明 |
|------|------|
| 服务器配置 | 首次启动输入服务器地址，保存到 shared_preferences |
| 服务列表 | 展示所有可用服务，显示报告数量 |
| 报告列表 | 按时间倒序，显示标题/日期/标签，支持下拉刷新 |
| Markdown 渲染 | 代码高亮、表格、标题层级 |
| 搜索 | 本地过滤报告标题 |
| 收藏 | 星标报告，收藏页快速访问 |
| 离线缓存 | 阅读过的报告自动缓存，无网络也可查看 |
| 暗色主题 | 默认暗色，与 PWA 风格一致 |

### 错误处理

| 场景 | 处理 |
|------|------|
| 网络不可达 | 提示"无法连接服务器"，展示缓存内容 |
| 服务器返回错误 | 提示具体错误信息，不崩溃 |
| 空列表 | 展示"暂无报告"占位 |
| 首次启动未配置 | 自动跳转设置页 |

## 非功能需求

- APK 目标大小 < 20MB
- 适配 Android 8.0+（minSdk 26）
- 冷启动 < 2 秒
- 页面切换 < 300ms
