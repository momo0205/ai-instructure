# apk-project — Mira WebView 壳（已归档）

最小的 Android WebView 壳，把 `mira-pwa` 包成 APK。功能已被 `mira-flutter` 取代，保留仅为追溯。

> 状态：**已归档，不再演进**。

## 结构

```
apk-project/
├── app/src/main/         # Activity + WebView
├── app/build.gradle.kts
├── settings.gradle.kts
└── mira.keystore         # 本地签名文件（已从 git 移除，仅存在于开发机）
```

## 构建

⚠️ 没有 gradle wrapper，需要系统 Gradle。

```bash
cd 05-mobile/apk-project
gradle assembleRelease
```

签名参数从 `key.properties` 读取（不入库）：

```properties
storeFile=mira.keystore
storePassword=...
keyAlias=mira
keyPassword=...
```

没有 `key.properties` 时构建仍可完成，但产物未签名。

## 注意

- 这个壳加载的是远程 URL，不是本地打包资源；离线不可用。
- 不要再往这里加功能，新需求去 `mira-flutter`。
