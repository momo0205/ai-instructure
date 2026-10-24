# mira-pwa — Mira 投研终端（Web / WebView）

单文件 PWA：不依赖构建工具，直接打开就能用；外面套一层 Android WebView 壳可以打包成 APK。

> 状态：**维护**。功能上已被 `mira-flutter` 取代，保留作为"免安装、秒开"的入口。

## 结构

```
mira-pwa/
├── index.html        # 整个应用（HTML + CSS + JS）
├── manifest.json     # PWA 清单
├── sw.js             # Service Worker（离线缓存）
├── icon-192.png / icon-512.png
├── android/          # WebView 壳工程（Gradle）
└── mira.apk          # 已构建产物（本地文件，不入库）
```

## 本地预览

```bash
cd 05-mobile/mira-pwa
python3 -m http.server 8000
# 打开 http://localhost:8000
```

> 用 `file://` 打开会限制 Service Worker 和 fetch，务必用 http。

## 打包 APK

```bash
cd 05-mobile/mira-pwa/android
./gradlew assembleRelease
```

## 注意

- 服务器地址在 `index.html` 里硬编码，换环境要改。
- `mira.apk` 已被 `.gitignore` 排除（发布包走 Releases）。
