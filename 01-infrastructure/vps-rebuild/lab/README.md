# FlClash / REALITY 隔离实验

给维护文档的人使用，不是用户部署入口。部署按 `../FlClash与VPS代理部署实测教程.html`。

`flclash_probe.py` 启动本机已安装 FlClash 0.8.94 的原始 Core，以私有 IPC socket 和新 home 调用官方生命周期。它不启动 Flutter 应用，不修改用户 profile、系统代理或网络接口。它仅接受一条 `127.0.0.1:32000–32999` 的 VLESS TCP REALITY 节点；重建代理组和 MATCH 规则，禁用 TUN/DNS/额外监听/控制器/提供商，不接受节点的文件引用。传入凭据必须是自行生成的一次性实验凭据。

```bash
python3 -m unittest discover -s 01-infrastructure/vps-rebuild/lab -p test_flclash_probe.py -v
python3 01-infrastructure/vps-rebuild/lab/flclash_probe.py \
  --config /private/tmp/one-lab-node.json --port 28791 \
  --url https://www.gstatic.com/generate_204 \
  --url 'https://speed.cloudflare.com/__down?bytes=1048576' --timeout 25
```

JSON 可是一条节点或 `{"proxies":[node]}`。节点格式：

```json
{
  "name":"probe", "type":"vless", "server":"127.0.0.1", "port":32643,
  "uuid":"临时实验UUID", "network":"tcp", "tls":true, "udp":false,
  "flow":"xtls-rprx-vision", "servername":"dl.google.com", "client-fingerprint":"chrome",
  "reality-opts":{
    "public-key":"临时实验X25519公钥", "short-id":"16位实验十六进制",
    "support-x25519mlkem768":false
  }
}
```

macOS sandbox 中 socket / 子进程可能需要明确授权。探针输出最终 HTTP 状态、curl 退出码、下载字节数、内核退出码和监听关闭状态；`ok:true` 的 startup_smoke 只表示启动/退出，不能算网络成功。私有 `/private/tmp/fcprobe-*` 含临时凭据，不提交。请求使用 curl 首参数 `-q`，去除环境代理变量并明确指定实验回环代理；不跳过 TLS 验证。超时覆盖 IPC 分片读取和解码。错误凭据负例必须失败，才能排除直连绕过。

2026-10-09 对照服务端：Ubuntu24.04 linux/amd64 容器，各自原生 TCP443 映射到 Mac127.0.0.1：Xray26.3.27→32443、Xray26.9.9→32543、sing-box1.14.2→32643。下载资产、核对摘要、提取二进制；生成新的实验 UUID / keypair / short ID，采用教程中的服务端配置（容器监听0.0.0.0:443）。不要挂载真实 VPS 配置。每个容器只挂载实验目录，未暴露公网端口。需要运行 Docker 与真实外网目标可达。

`results-2026-10-09.json` 保存了无凭据的实际矩阵数据。背景、SHA256、来源、安装包验证和实验边界见 `docs/superpowers/acceptance-2026-10-09-vps-proxy-route.md`。这些实验不能证明运营商到 VPS 的链路、长期抗干扰能力、GUI 的配置覆盖、TUN/UDP 或公网证书签发。
