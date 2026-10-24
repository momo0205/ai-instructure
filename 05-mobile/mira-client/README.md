# mira-client — 原生 Android 客户端

Kotlin + Gradle 的原生实现，直连 mira-server。

> 状态：**维护**。日常使用请优先 `mira-flutter`；这个工程用于验证原生实现与低版本兼容。

## 结构

```
mira-client/
├── app/src/main/java/com/...   # 源码
├── app/src/main/res/           # 资源
├── gradle/                     # Gradle 配置
├── build.gradle.kts
└── settings.gradle.kts
```

## 构建

⚠️ **没有 gradle wrapper**，需要系统已装 Gradle（或先 `gradle wrapper` 生成）。

```bash
cd 05-mobile/mira-client
gradle assembleDebug
# 产物：app/build/outputs/apk/debug/
```

安装到手机：

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## 注意

- 需要 JDK 17 与 Android SDK（`compileSdk` 见 `app/build.gradle.kts`）。
- 签名配置在工程里的 `key.properties`（不入库）；没有它时跳过 release 签名。
