# Mira 踩坑记忆 · CodeWhale 会话记录

> 2026-06-18 · ironmao · investment-research 项目

## 项目全景

```
ai-instructure/
├── 04-applications/investment-research/
│   ├── Mira/               ← 投研协议 (submodule: byteseek/Mira)
│   ├── a-stock-data/       ← A股数据工具包 (submodule: simonlin1212/a-stock-data)
│   ├── mira-server/        ← HTTP API 服务端 (自己写的，非 git 管理)
│   └── deploy-guide.html   ← 部署指南
└── 05-mobile/
    ├── mira-flutter/       ← Flutter App (submodule: momo0205/mira-flutter)
    └── mira-pwa/           ← PWA 版本
```

## 两个客户端，两套 API

| | Flutter App | PWA |
|------|------|------|
| 定位 | 正式原生客户端 (已构建 APK) | 轻量 WebView 验证工具 |
| API 风格 | REST 报告浏览器 | 即席 POST 查询 |
| 需要 | `GET /api/services` → `GET /api/services/{id}/reports` → `GET /api/services/{id}/reports/{id}` | `POST /research` / `POST /briefing` |

mira-server 同时支持两套，报告持久化在 `reports/` 目录。

## 环境依赖

### Python 3.9 兼容性
- **不支持 `dict | None` 语法** → 必须用 `Optional[dict]` 或 `Union[dict, None]`
- **pip 装包要用清华镜像**：`pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple mootdx fastapi uvicorn openai`

### macOS 沙箱限制
- CodeWhale 的 `exec_shell` **不能写** `.git/`、`~/android-sdk/`（被 sdkmanager 标记过的目录）、`/opt/homebrew/`
- **可以写** 项目目录、`/tmp/`
- Flutter 构建**必须在终端直接跑**，CodeWhale 内跑不了

### Git submodule 恢复
- `.gitmodules` 丢失时，从 `https://raw.githubusercontent.com/momo0205/ai-instructure/main/.gitmodules` 获取
- 之前手建过 `.gitmodules` → git pull 冲突 → `mv .gitmodules .gitmodules.bak` + `git pull`

### 网络
- `dl.google.com` 国内**可直连**，走代理反而可能导致文件损坏 (CRC 错误)
- `repo.maven.apache.org` 需要代理
- sdkmanager **不认 `http_proxy` 环境变量**，必须用 `--proxy=http --proxy_host=127.0.0.1 --proxy_port=7890`
- Gradle 代理必须写入 `~/.gradle/gradle.properties`：`systemProp.http[s].proxyHost/Port`

### Android SDK
- **不要手拼 SDK 目录**！用 `sdkmanager` 正式安装
- 安装命令（终端内）：`sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0" "ndk;28.2.13676358"`
- NDK 许可不能伪造，必须 `yes | sdkmanager --licenses`
- NDK 非必需可删：`android/app/build.gradle.kts` 中去掉 `ndkVersion = flutter.ndkVersion`

## Flutter App 变动
- `AndroidManifest.xml`：加了 `INTERNET` 权限 + `usesCleartextTraffic`
- App 名称改为 `ironmao`
- 服务器地址：`https://mira.ironmao.win` (cloudflared tunnel)

## 启动步骤

```bash
# 1. 启动 mira-server
cd ~/code/ai-instructure/04-applications/investment-research/mira-server
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
python3 server.py

# 2. 触发第一个报告 (另一个终端)
curl -X POST http://localhost:8080/research \
  -H "Content-Type: application/json" \
  -d '{"ticker":"600519","depth":"quick_map"}'

# 3. Flutter 构建 (需要 Android SDK + 代理)
export ANDROID_HOME=$HOME/android-sdk JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH=$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH
cd ~/code/ai-instructure/05-mobile/mira-flutter
flutter build apk --release

# 4. 分发 APK
cp build/app/outputs/flutter-apk/app-release.apk ~/code/ai-instructure/01-infrastructure/hello-page/
# 手机访问: https://hello.ironmao.win/app-release.apk
```

## 服务端端点

| 端点 | 用途 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /api/services` | Flutter: 服务列表 |
| `GET /api/services/{id}/reports` | Flutter: 报告列表 |
| `GET /api/services/{id}/reports/{reportId}` | Flutter: 报告内容 |
| `POST /research` | PWA: 个股研究 |
| `POST /briefing` | PWA: 市场简报 |
| `POST /industry` | PWA: 行业分析 |
| `POST /api/trigger` | cron 触发生成报告 |
