# VPS 代理实测路线 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为用户交付有实际 FlClash 内核握手证据、从现有服务器或全新系统均可照做的中文 HTML 代理部署教程。

**Architecture:** 实验与生产分开。Mac 上的 FlClash 0.8.94 原始内核用独立临时目录和回环代理监听，对 Ubuntu 24.04 amd64 容器中的固定版本服务端做 A/B；不改变运行中的应用、系统代理或真实 VPS。主教程先用完整文件验证节点，随后提供正常 HTTPS 订阅；服务器迁移由用户手动执行，保留旧服务回退。

**Tech Stack:** FlClashCore JSON IPC、Python 标准库、Docker、sing-box / Xray、Mihomo YAML、Caddy、单文件 HTML。

### Task 1: 固定来源与实验环境

- [x] 恢复已有记录，核对工作区和本机 FlClash 版本；只处理本任务文件。
- [x] 核对固定版本官方发布资产、哈希、systemd 权限及配置语义，记录 Mihomo 与新 Xray 的已知兼容性边界。
- [x] 恢复三个独立服务端：Xray 26.3.27、Xray 26.9.9、sing-box 1.14.2；只绑定 Mac 回环地址，生成全新实验凭据。

### Task 2: 验证真实客户端内核

**Files:** `01-infrastructure/vps-rebuild/lab/flclash_probe.py` 与对应安全测试。

- [x] TDD 验证仅允许实验回环节点、拒绝文件引用及禁用 TUN/DNS/外部控制器；再实现 IPC 生命周期与显式 curl。
- [x] 运行六组合的 REALITY 握手 / HTTPS 内容实验，记录 MLKEM 开关、curl 退出码、最终 HTTP 响应及服务端日志；配置导入不能替代此验收。
- [x] 重复主候选成功请求，并加入错误凭据负例，验证没有直连绕过。
- [x] 测试 Ubuntu 包安装 / 服务用户读取配置，以及 Caddy 订阅路由；公网 ACME 与实际运营商路径标为用户现场验收。

### Task 3: 沉淀可操作的 HTML

**Files:** 新建 `01-infrastructure/vps-rebuild/FlClash与VPS代理部署实测教程.html`；更新旧教程、维护手册与 `docs/superpowers/acceptance-2026-10-09-vps-proxy-route.md`。

- [x] 根据实验选择一条主路线；说明选择原因、固定版本和实际已测 / 尚未现场验收范围。
- [x] 连续写明网站入口、Mac / 服务器执行地点、基础环境入口、备份、安装、配置、启动、文件下载、FlClash 导入和真实联网验收。
- [x] 提供正常 HTTPS 订阅、停止旧服务的时机、443 与网站后续共存限制、回退及日常维护；不保存真实凭据，不要求重装已初始化服务器。
- [x] 每一步有明确成功条件和故障定位，首次关闭 TUN 与系统代理，完成显式代理测试后再打开系统代理。

### Task 4: 验证与同步

- [x] 执行实验工具安全测试、现有 7 项教程测试、HTML 链接 / 锚点 / 脚本 / 命令语法检查，并审阅部署顺序。
- [x] 请求范围明确的独立审查，修复重要问题；关闭本任务的测试进程和容器。
- [x] 保存证据，尝试 Mem0，按范围提交 / 同步；不包含其它项目的工作。

用户已明确要求继续摸清路线并生成 HTML，路线选择与实验细节在该授权内由代理判断；不新增设计批准或真实 VPS 写入流程。

### 现场跟进：已有 Caddy 源返回 HTTP 402

- [x] 在第 3 步补充仅停用官方 Caddy 更新源的可逆恢复命令；保留 Caddy 服务、配置和签名校验。
- [x] 安装失败明确停止并指向恢复说明；第 5 步先核对二进制与服务账户，缺失时提示返回第 3 步。
- [x] 在临时目录验证源文件停用、重复执行与拒绝覆盖行为，检查 HTML 命令语法；记录用户日志中的失败链并仅同步本任务文件。
