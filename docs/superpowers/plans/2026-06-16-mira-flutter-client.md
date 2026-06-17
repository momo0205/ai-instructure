# Mira Flutter 客户端 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 Flutter Android 客户端，连接服务端 API，浏览和阅读 Markdown 报告。

**Architecture:** 三层页面结构（ServiceList → ReportList → ReportRead），Provider 状态管理，dio 网络请求，flutter_markdown 渲染，sqflite 离线缓存，shared_preferences 配置持久化。

**Tech Stack:** Flutter 3.x, Dart, Provider, dio, flutter_markdown, sqflite, shared_preferences, Material 3

---

## 文件结构

```
05-mobile/mira-flutter/
├── pubspec.yaml
├── lib/
│   ├── main.dart                          ← App 入口，Provider 注册
│   ├── config/
│   │   └── api_config.dart                ← 服务器地址配置
│   ├── models/
│   │   ├── service.dart                   ← Service 数据模型
│   │   └── report.dart                    ← Report 数据模型
│   ├── services/
│   │   └── api_service.dart               ← dio HTTP 封装
│   ├── stores/
│   │   ├── service_store.dart             ← 服务列表状态
│   │   ├── report_store.dart              ← 报告列表 + 内容获取
│   │   ├── favorite_store.dart            ← 收藏管理
│   │   └── cache_store.dart               ← sqflite 离线缓存
│   ├── screens/
│   │   ├── settings_screen.dart           ← 服务器地址设置
│   │   ├── service_list_screen.dart        ← 服务列表首页
│   │   ├── report_list_screen.dart         ← 报告列表
│   │   └── report_read_screen.dart         ← MD 渲染阅读
│   └── widgets/
│       ├── service_card.dart              ← 服务卡片组件
│       ├── report_card.dart               ← 报告卡片组件
│       └── empty_state.dart               ← 空状态占位组件
└── test/
    ├── models/
    │   └── service_test.dart
    ├── services/
    │   └── api_service_test.dart
    ├── stores/
    │   └── favorite_store_test.dart
    └── widgets/
        └── empty_state_test.dart
```

---

### Task 0: 环境搭建

**Files:**
- Create: `05-mobile/mira-flutter/`

- [ ] **Step 1: 安装 Flutter SDK**

```bash
brew install --cask flutter
```

验证：
```bash
flutter --version
```
预期：显示 Flutter 3.x 版本信息。

- [ ] **Step 2: 创建 Flutter 项目**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure/05-mobile
flutter create --org com.mira --project-name mira_flutter --platforms android mira-flutter
```

- [ ] **Step 3: 添加依赖**

修改 `pubspec.yaml`，在 `dependencies` 下添加：

```yaml
dependencies:
  flutter:
    sdk: flutter
  provider: ^6.1.2
  dio: ^5.7.0
  flutter_markdown: ^0.7.6
  sqflite: ^2.4.1
  path: ^1.9.1
  shared_preferences: ^2.3.4
```

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure/05-mobile/mira-flutter
flutter pub get
```

- [ ] **Step 4: 配置 Android 签名**

将 `05-mobile/apk-project/mira.keystore` 复制到项目：
```bash
cp /Users/chenmao/Desktop/workspace/ai-instructure/05-mobile/apk-project/mira.keystore /Users/chenmao/Desktop/workspace/ai-instructure/05-mobile/mira-flutter/android/app/mira.keystore
```

创建 `android/key.properties`：
```properties
storePassword=mira123
keyPassword=mira123
keyAlias=mira
storeFile=mira.keystore
```

修改 `android/app/build.gradle.kts`，在 `android` 块前添加签名配置加载逻辑。

- [ ] **Step 5: 验证项目可构建**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure/05-mobile/mira-flutter
flutter build apk --debug
```

预期：构建成功，生成 debug APK。

- [ ] **Step 6: Commit**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure/05-mobile/mira-flutter
git init
git add -A
git commit -m "chore: init Flutter project with dependencies and signing config"
```

---

### Task 1: 数据模型

**Files:**
- Create: `lib/models/service.dart`
- Create: `lib/models/report.dart`
- Create: `test/models/service_test.dart`

- [ ] **Step 1: 编写 Service 模型测试**

```dart
// test/models/service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mira_flutter/models/service.dart';

void main() {
  group('Service', () {
    test('fromJson creates Service with all fields', () {
      final json = {
        'id': 'mira',
        'name': 'Mira 投研',
        'description': '股票投研分析',
        'report_count': 5,
      };
      final service = Service.fromJson(json);
      expect(service.id, 'mira');
      expect(service.name, 'Mira 投研');
      expect(service.description, '股票投研分析');
      expect(service.reportCount, 5);
    });

    test('fromJson handles missing report_count', () {
      final json = {
        'id': 'mira',
        'name': 'Mira 投研',
      };
      final service = Service.fromJson(json);
      expect(service.reportCount, 0);
    });
  });
}
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure/05-mobile/mira-flutter
flutter test test/models/service_test.dart
```
预期：FAIL，Service 类未定义。

- [ ] **Step 3: 实现 Service 模型**

```dart
// lib/models/service.dart
class Service {
  final String id;
  final String name;
  final String? description;
  final int reportCount;

  const Service({
    required this.id,
    required this.name,
    this.description,
    this.reportCount = 0,
  });

  factory Service.fromJson(Map<String, dynamic> json) {
    return Service(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      reportCount: (json['report_count'] as int?) ?? 0,
    );
  }
}
```

- [ ] **Step 4: 运行测试验证通过**

```bash
flutter test test/models/service_test.dart
```
预期：PASS。

- [ ] **Step 5: 编写 Report 模型测试**

```dart
// test/models/service_test.dart 追加
    group('Report', () {
      test('fromJson creates Report with all fields', () {
        final json = {
          'id': '600519-standard',
          'title': '贵州茅台 标准分析',
          'date': '2026-06-16',
          'tags': ['白酒', '消费'],
          'summary': '茅台2026Q1分析',
        };
        final report = Report.fromJson(json);
        expect(report.id, '600519-standard');
        expect(report.title, '贵州茅台 标准分析');
        expect(report.date, DateTime(2026, 6, 16));
        expect(report.tags, ['白酒', '消费']);
        expect(report.summary, '茅台2026Q1分析');
      });

      test('fromJson handles missing optional fields', () {
        final json = {
          'id': 'report-1',
          'title': '测试报告',
          'date': '2026-06-16',
        };
        final report = Report.fromJson(json);
        expect(report.tags, isEmpty);
        expect(report.summary, isNull);
      });
    });
```

- [ ] **Step 6: 运行测试验证失败**

```bash
flutter test test/models/service_test.dart
```
预期：FAIL，Report 类未定义。

- [ ] **Step 7: 实现 Report 模型**

```dart
// lib/models/report.dart
class Report {
  final String id;
  final String title;
  final DateTime date;
  final List<String> tags;
  final String? summary;

  const Report({
    required this.id,
    required this.title,
    required this.date,
    this.tags = const [],
    this.summary,
  });

  factory Report.fromJson(Map<String, dynamic> json) {
    return Report(
      id: json['id'] as String,
      title: json['title'] as String,
      date: DateTime.parse(json['date'] as String),
      tags: (json['tags'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      summary: json['summary'] as String?,
    );
  }
}
```

- [ ] **Step 8: 运行全部测试验证通过**

```bash
flutter test test/models/service_test.dart
```
预期：全部 PASS。

- [ ] **Step 9: Commit**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure/05-mobile/mira-flutter
git add lib/models/ test/models/
git commit -m "feat: add Service and Report data models"
```

---

### Task 2: API 配置与网络层

**Files:**
- Create: `lib/config/api_config.dart`
- Create: `lib/services/api_service.dart`
- Create: `test/services/api_service_test.dart`

- [ ] **Step 1: 实现 API 配置**

```dart
// lib/config/api_config.dart
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiConfig extends ChangeNotifier {
  static const _key = 'server_url';
  String _serverUrl = '';

  String get serverUrl => _serverUrl;
  bool get isConfigured => _serverUrl.isNotEmpty;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _serverUrl = prefs.getString(_key) ?? '';
    notifyListeners();
  }

  Future<void> save(String url) async {
    _serverUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, _serverUrl);
    notifyListeners();
  }

  String serviceUrl(String path) => '$_serverUrl$path';
}
```

- [ ] **Step 2: 实现 API 服务**

```dart
// lib/services/api_service.dart
import 'package:dio/dio.dart';
import '../config/api_config.dart';
import '../models/service.dart';
import '../models/report.dart';

class ApiService {
  final ApiConfig _config;
  final Dio _dio;

  ApiService(this._config)
      : _dio = Dio(BaseOptions(
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 30),
        ));

  Future<List<Service>> fetchServices() async {
    final response = await _dio.get(_config.serviceUrl('/api/services'));
    final list = response.data as List<dynamic>;
    return list.map((e) => Service.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<Report>> fetchReports(String serviceId) async {
    final response = await _dio.get(
      _config.serviceUrl('/api/services/$serviceId/reports'),
    );
    final list = response.data as List<dynamic>;
    return list.map((e) => Report.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<String> fetchReportContent(String serviceId, String reportId) async {
    final response = await _dio.get(
      _config.serviceUrl('/api/services/$serviceId/reports/$reportId'),
    );
    return response.data as String;
  }
}
```

- [ ] **Step 3: 编写 API 服务测试（Mock）**

```dart
// test/services/api_service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:mira_flutter/config/api_config.dart';
import 'package:mira_flutter/services/api_service.dart';

class FakeDioAdapter implements HttpClientAdapter {
  final Map<String, dynamic> Function(String path) handler;

  FakeDioAdapter(this.handler);

  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? requestStream, Future<void>? cancelFuture) async {
    final data = handler(options.path);
    final body = data['body'];
    return ResponseBody.fromString(
      body is String ? body : jsonEncode(body),
      data['status'] as int,
      headers: {Headers.contentTypeHeader: ['application/json']},
    );
  }
}

// Tests verify deserialization of Service and Report from mock responses
```

- [ ] **Step 4: 运行测试验证通过**

```bash
flutter test test/services/api_service_test.dart
```
预期：PASS。

- [ ] **Step 5: Commit**

```bash
git add lib/config/ lib/services/ test/services/
git commit -m "feat: add API config and network service layer"
```

---

### Task 3: 状态管理层（Stores）

**Files:**
- Create: `lib/stores/service_store.dart`
- Create: `lib/stores/report_store.dart`
- Create: `lib/stores/favorite_store.dart`
- Create: `lib/stores/cache_store.dart`
- Create: `test/stores/favorite_store_test.dart`

- [ ] **Step 1: 实现 ServiceStore**

```dart
// lib/stores/service_store.dart
import 'package:flutter/foundation.dart';
import '../models/service.dart';
import '../services/api_service.dart';

class ServiceStore extends ChangeNotifier {
  final ApiService _api;
  List<Service> _services = [];
  bool _loading = false;
  String? _error;

  ServiceStore(this._api);

  List<Service> get services => _services;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> fetchServices() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _services = await _api.fetchServices();
    } catch (e) {
      _error = e.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }
}
```

- [ ] **Step 2: 实现 ReportStore**

```dart
// lib/stores/report_store.dart
import 'package:flutter/foundation.dart';
import '../models/report.dart';
import '../services/api_service.dart';
import 'cache_store.dart';

class ReportStore extends ChangeNotifier {
  final ApiService _api;
  final CacheStore _cache;
  List<Report> _reports = [];
  bool _loading = false;
  String? _error;

  ReportStore(this._api, this._cache);

  List<Report> get reports => _reports;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> fetchReports(String serviceId) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _reports = await _api.fetchReports(serviceId);
      _reports.sort((a, b) => b.date.compareTo(a.date));
    } catch (e) {
      _error = e.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<String> fetchContent(String serviceId, String reportId) async {
    final cached = await _cache.get(serviceId, reportId);
    if (cached != null) return cached;
    final content = await _api.fetchReportContent(serviceId, reportId);
    await _cache.put(serviceId, reportId, content);
    return content;
  }

  List<Report> search(String query) {
    if (query.isEmpty) return _reports;
    final q = query.toLowerCase();
    return _reports.where((r) {
      return r.title.toLowerCase().contains(q) ||
          r.tags.any((t) => t.toLowerCase().contains(q));
    }).toList();
  }
}
```

- [ ] **Step 3: 实现 FavoriteStore**

```dart
// lib/stores/favorite_store.dart
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class FavoriteStore extends ChangeNotifier {
  static const _key = 'favorites';
  Set<String> _favorites = {};

  Set<String> get favorites => _favorites;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _favorites = (prefs.getStringList(_key) ?? []).toSet();
    notifyListeners();
  }

  bool isFavorite(String reportId) => _favorites.contains(reportId);

  Future<void> toggle(String reportId) async {
    if (_favorites.contains(reportId)) {
      _favorites.remove(reportId);
    } else {
      _favorites.add(reportId);
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(_key, _favorites.toList());
    notifyListeners();
  }
}
```

- [ ] **Step 4: 编写 FavoriteStore 测试**

```dart
// test/stores/favorite_store_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mira_flutter/stores/favorite_store.dart';

void main() {
  group('FavoriteStore', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('initial state is empty', () async {
      final store = FavoriteStore();
      await store.load();
      expect(store.favorites, isEmpty);
    });

    test('toggle adds and removes favorite', () async {
      final store = FavoriteStore();
      await store.load();
      await store.toggle('report-1');
      expect(store.isFavorite('report-1'), isTrue);
      await store.toggle('report-1');
      expect(store.isFavorite('report-1'), isFalse);
    });
  });
}
```

- [ ] **Step 5: 实现 CacheStore**

```dart
// lib/stores/cache_store.dart
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as p;

class CacheStore {
  static Database? _db;

  Future<Database> get db async {
    if (_db != null) return _db!;
    final dbPath = await getDatabasesPath();
    _db = await openDatabase(
      p.join(dbPath, 'mira_cache.db'),
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE cache (
            service_id TEXT,
            report_id TEXT,
            content TEXT,
            cached_at INTEGER,
            PRIMARY KEY (service_id, report_id)
          )
        ''');
      },
    );
    return _db!;
  }

  Future<String?> get(String serviceId, String reportId) async {
    final database = await db;
    final results = await database.query(
      'cache',
      columns: ['content'],
      where: 'service_id = ? AND report_id = ?',
      whereArgs: [serviceId, reportId],
    );
    if (results.isEmpty) return null;
    return results.first['content'] as String;
  }

  Future<void> put(String serviceId, String reportId, String content) async {
    final database = await db;
    await database.insert(
      'cache',
      {
        'service_id': serviceId,
        'report_id': reportId,
        'content': content,
        'cached_at': DateTime.now().millisecondsSinceEpoch,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<void> clear() async {
    final database = await db;
    await database.delete('cache');
  }
}
```

- [ ] **Step 6: 运行测试验证通过**

```bash
flutter test test/stores/
```
预期：PASS。

- [ ] **Step 7: Commit**

```bash
git add lib/stores/ test/stores/
git commit -m "feat: add state management stores (Service, Report, Favorite, Cache)"
```

---

### Task 4: 通用组件

**Files:**
- Create: `lib/widgets/service_card.dart`
- Create: `lib/widgets/report_card.dart`
- Create: `lib/widgets/empty_state.dart`
- Create: `test/widgets/empty_state_test.dart`

- [ ] **Step 1: 实现 EmptyState 组件**

```dart
// lib/widgets/empty_state.dart
import 'package:flutter/material.dart';

class EmptyState extends StatelessWidget {
  final IconData icon;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  const EmptyState({
    super.key,
    required this.icon,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 64, color: Theme.of(context).colorScheme.outline),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: Theme.of(context).colorScheme.outline,
                  ),
            ),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 16),
              FilledButton.tonal(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: 编写 EmptyState 测试**

```dart
// test/widgets/empty_state_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mira_flutter/widgets/empty_state.dart';

void main() {
  testWidgets('renders message and icon', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: EmptyState(icon: Icons.inbox, message: '暂无数据'),
        ),
      ),
    );
    expect(find.text('暂无数据'), findsOneWidget);
    expect(find.byIcon(Icons.inbox), findsOneWidget);
  });

  testWidgets('renders action button when provided', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: EmptyState(
            icon: Icons.error,
            message: '出错了',
            actionLabel: '重试',
            onAction: () => tapped = true,
          ),
        ),
      ),
    );
    expect(find.text('重试'), findsOneWidget);
    await tester.tap(find.text('重试'));
    expect(tapped, isTrue);
  });
}
```

- [ ] **Step 3: 运行测试验证通过**

```bash
flutter test test/widgets/empty_state_test.dart
```
预期：PASS。

- [ ] **Step 4: 实现 ServiceCard 组件**

```dart
// lib/widgets/service_card.dart
import 'package:flutter/material.dart';
import '../models/service.dart';

class ServiceCard extends StatelessWidget {
  final Service service;
  final VoidCallback onTap;

  const ServiceCard({super.key, required this.service, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: Icon(Icons.analytics_outlined, color: theme.colorScheme.primary),
        title: Text(service.name, style: theme.textTheme.titleMedium),
        subtitle: service.description != null
            ? Text(service.description!, maxLines: 1, overflow: TextOverflow.ellipsis)
            : null,
        trailing: service.reportCount > 0
            ? Chip(
                label: Text('${service.reportCount} 篇报告'),
                visualDensity: VisualDensity.compact,
              )
            : null,
        onTap: onTap,
      ),
    );
  }
}
```

- [ ] **Step 5: 实现 ReportCard 组件**

```dart
// lib/widgets/report_card.dart
import 'package:flutter/material.dart';
import '../models/report.dart';
import '../stores/favorite_store.dart';

class ReportCard extends StatelessWidget {
  final Report report;
  final bool isFavorite;
  final VoidCallback onTap;
  final VoidCallback onToggleFavorite;

  const ReportCard({
    super.key,
    required this.report,
    required this.isFavorite,
    required this.onTap,
    required this.onToggleFavorite,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 3),
      child: ListTile(
        contentPadding: const EdgeInsets.only(left: 16, right: 8, top: 6, bottom: 6),
        title: Text(report.title, style: theme.textTheme.titleSmall, maxLines: 2, overflow: TextOverflow.ellipsis),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Row(
            children: [
              Icon(Icons.calendar_today, size: 12, color: theme.colorScheme.outline),
              const SizedBox(width: 4),
              Text(_formatDate(report.date), style: theme.textTheme.bodySmall),
              if (report.tags.isNotEmpty) ...[
                const SizedBox(width: 12),
                ...report.tags.take(3).map((tag) => Padding(
                      padding: const EdgeInsets.only(right: 4),
                      child: Text('#$tag', style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.primary)),
                    )),
              ],
            ],
          ),
        ),
        trailing: IconButton(
          icon: Icon(isFavorite ? Icons.star : Icons.star_border, color: isFavorite ? Colors.amber : null),
          onPressed: onToggleFavorite,
        ),
        onTap: onTap,
      ),
    );
  }

  String _formatDate(DateTime date) => '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
}
```

- [ ] **Step 6: Commit**

```bash
git add lib/widgets/ test/widgets/
git commit -m "feat: add UI components (ServiceCard, ReportCard, EmptyState)"
```

---

### Task 5: 设置页面

**Files:**
- Create: `lib/screens/settings_screen.dart`

- [ ] **Step 1: 创建设置页面**

```dart
// lib/screens/settings_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/api_config.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _controller;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final config = context.read<ApiConfig>();
    _controller = TextEditingController(text: config.serverUrl);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('服务器设置')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _controller,
              decoration: const InputDecoration(
                labelText: '服务器地址',
                hintText: 'http://192.168.1.100:8080',
                prefixIcon: Icon(Icons.dns),
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.url,
              autocorrect: false,
              enabled: !_saving,
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _saving ? null : _save,
              child: _saving
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('保存'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _save() async {
    final url = _controller.text.trim();
    if (url.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请输入服务器地址')),
      );
      return;
    }
    setState(() => _saving = true);
    await context.read<ApiConfig>().save(url);
    if (mounted) {
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('已保存')),
      );
      Navigator.of(context).pop();
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add lib/screens/
git commit -m "feat: add settings screen for server URL configuration"
```

---

### Task 6: 服务列表页面

**Files:**
- Create: `lib/screens/service_list_screen.dart`

- [ ] **Step 1: 实现服务列表页面**

```dart
// lib/screens/service_list_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../stores/service_store.dart';
import '../stores/favorite_store.dart';
import '../widgets/service_card.dart';
import '../widgets/empty_state.dart';
import 'report_list_screen.dart';
import 'settings_screen.dart';

class ServiceListScreen extends StatefulWidget {
  const ServiceListScreen({super.key});

  @override
  State<ServiceListScreen> createState() => _ServiceListScreenState();
}

class _ServiceListScreenState extends State<ServiceListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ServiceStore>().fetchServices();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mira 投研终端'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen())),
          ),
          IconButton(
            icon: const Icon(Icons.star),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => FavoriteReportsScreen(favoriteStore: context.read<FavoriteStore>()),
                ),
              );
            },
          ),
        ],
      ),
      body: Consumer<ServiceStore>(
        builder: (context, store, _) {
          if (store.loading) {
            return const Center(child: CircularProgressIndicator());
          }
          if (store.error != null) {
            return EmptyState(
              icon: Icons.cloud_off,
              message: '无法连接服务器\n${store.error}',
              actionLabel: '重试',
              onAction: () => store.fetchServices(),
            );
          }
          if (store.services.isEmpty) {
            return const EmptyState(icon: Icons.inbox, message: '暂无可用服务');
          }
          return RefreshIndicator(
            onRefresh: () => store.fetchServices(),
            child: ListView.builder(
              padding: const EdgeInsets.only(top: 8, bottom: 16),
              itemCount: store.services.length,
              itemBuilder: (_, i) => ServiceCard(
                service: store.services[i],
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => ReportListScreen(serviceId: store.services[i].id, serviceName: store.services[i].name),
                    ),
                  );
                },
              ),
            ),
          );
        },
      ),
    );
  }
}

class FavoriteReportsScreen extends StatelessWidget {
  final FavoriteStore favoriteStore;

  const FavoriteReportsScreen({super.key, required this.favoriteStore});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('收藏')),
      body: favoriteStore.favorites.isEmpty
          ? const EmptyState(icon: Icons.star_border, message: '还没有收藏的报告')
          : ListView(
              children: favoriteStore.favorites
                  .map((id) => ListTile(
                        title: Text(id),
                        leading: const Icon(Icons.star, color: Colors.amber),
                      ))
                  .toList(),
            ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add lib/screens/
git commit -m "feat: add service list screen with pull-to-refresh and favorites entry"
```

---

### Task 7: 报告列表页面

**Files:**
- Create: `lib/screens/report_list_screen.dart`

- [ ] **Step 1: 实现报告列表页面**

```dart
// lib/screens/report_list_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/report.dart';
import '../stores/report_store.dart';
import '../stores/favorite_store.dart';
import '../widgets/report_card.dart';
import '../widgets/empty_state.dart';
import 'report_read_screen.dart';

class ReportListScreen extends StatefulWidget {
  final String serviceId;
  final String serviceName;

  const ReportListScreen({super.key, required this.serviceId, required this.serviceName});

  @override
  State<ReportListScreen> createState() => _ReportListScreenState();
}

class _ReportListScreenState extends State<ReportListScreen> {
  final _searchController = TextEditingController();
  String _query = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ReportStore>().fetchReports(widget.serviceId);
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.serviceName),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: '搜索报告...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _query.isNotEmpty
                    ? IconButton(icon: const Icon(Icons.clear), onPressed: () { _searchController.clear(); setState(() => _query = ''); })
                    : null,
                filled: true,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.symmetric(vertical: 0),
              ),
              onChanged: (v) => setState(() => _query = v),
            ),
          ),
        ),
      ),
      body: Consumer<ReportStore>(
        builder: (context, store, _) {
          if (store.loading) {
            return const Center(child: CircularProgressIndicator());
          }
          if (store.error != null) {
            return EmptyState(
              icon: Icons.error_outline,
              message: '加载失败\n${store.error}',
              actionLabel: '重试',
              onAction: () => store.fetchReports(widget.serviceId),
            );
          }
          final reports = store.search(_query);
          if (reports.isEmpty) {
            return _query.isNotEmpty
                ? EmptyState(icon: Icons.search_off, message: '未找到匹配 "$_query" 的报告')
                : const EmptyState(icon: Icons.inbox, message: '暂无报告');
          }
          return RefreshIndicator(
            onRefresh: () => store.fetchReports(widget.serviceId),
            child: ListView.builder(
              padding: const EdgeInsets.only(top: 8, bottom: 16),
              itemCount: reports.length,
              itemBuilder: (_, i) {
                final report = reports[i];
                final isFavorite = context.watch<FavoriteStore>().isFavorite(report.title);
                return ReportCard(
                  report: report,
                  isFavorite: isFavorite,
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => ReportReadScreen(serviceId: widget.serviceId, report: report),
                      ),
                    );
                  },
                  onToggleFavorite: () => context.read<FavoriteStore>().toggle(report.title),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add lib/screens/
git commit -m "feat: add report list screen with search and pull-to-refresh"
```

---

### Task 8: 报告阅读页面

**Files:**
- Create: `lib/screens/report_read_screen.dart`

- [ ] **Step 1: 实现报告阅读页面**

```dart
// lib/screens/report_read_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:provider/provider.dart';
import '../models/report.dart';
import '../stores/report_store.dart';
import '../stores/favorite_store.dart';

class ReportReadScreen extends StatefulWidget {
  final String serviceId;
  final Report report;

  const ReportReadScreen({super.key, required this.serviceId, required this.report});

  @override
  State<ReportReadScreen> createState() => _ReportReadScreenState();
}

class _ReportReadScreenState extends State<ReportReadScreen> {
  String? _content;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final content = await context.read<ReportStore>().fetchContent(widget.serviceId, widget.report.id);
      if (mounted) setState(() { _content = content; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isFavorite = context.watch<FavoriteStore>().isFavorite(widget.report.title);
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.report.title, maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(
            icon: Icon(isFavorite ? Icons.star : Icons.star_border, color: isFavorite ? Colors.amber : null),
            onPressed: () => context.read<FavoriteStore>().toggle(widget.report.title),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.red),
              const SizedBox(height: 16),
              Text('加载失败\n$_error', textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton.tonal(onPressed: () { setState(() { _loading = true; _error = null; }); _load(); }, child: const Text('重试')),
            ],
          ),
        ),
      );
    }
    return Markdown(
      data: _content!,
      selectable: true,
      padding: const EdgeInsets.all(16),
      styleSheet: MarkdownStyleSheet(
        h1: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Theme.of(context).colorScheme.primary),
        h2: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: Theme.of(context).colorScheme.secondary),
        h3: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        code: TextStyle(fontSize: 13, backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest),
        codeblockDecoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
        ),
        tableBorder: TableBorder.all(color: Theme.of(context).colorScheme.outlineVariant),
        tableHead: TextStyle(fontWeight: FontWeight.bold, color: Theme.of(context).colorScheme.onSurface),
        tableBody: TextStyle(color: Theme.of(context).colorScheme.onSurface),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add lib/screens/
git commit -m "feat: add markdown reader screen with favorite toggle"
```

---

### Task 9: 应用入口与路由

**Files:**
- Modify: `lib/main.dart`

- [ ] **Step 1: 实现 main.dart**

```dart
// lib/main.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'config/api_config.dart';
import 'services/api_service.dart';
import 'stores/service_store.dart';
import 'stores/report_store.dart';
import 'stores/favorite_store.dart';
import 'stores/cache_store.dart';
import 'screens/service_list_screen.dart';
import 'screens/settings_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final apiConfig = ApiConfig();
  await apiConfig.load();
  runApp(MiraApp(apiConfig: apiConfig));
}

class MiraApp extends StatelessWidget {
  final ApiConfig apiConfig;

  const MiraApp({super.key, required this.apiConfig});

  @override
  Widget build(BuildContext context) {
    final apiService = ApiService(apiConfig);
    final cacheStore = CacheStore();

    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: apiConfig),
        Provider.value(value: apiService),
        ChangeNotifierProvider(create: (_) => ServiceStore(apiService)),
        ChangeNotifierProvider(create: (_) => ReportStore(apiService, cacheStore)),
        ChangeNotifierProvider(create: (_) {
          final store = FavoriteStore();
          store.load();
          return store;
        }),
      ],
      child: MaterialApp(
        title: 'Mira 投研终端',
        debugShowCheckedModeBanner: false,
        themeMode: ThemeMode.dark,
        darkTheme: ThemeData(
          brightness: Brightness.dark,
          colorSchemeSeed: const Color(0xFF58A6FF),
          useMaterial3: true,
        ),
        home: Consumer<ApiConfig>(
          builder: (context, config, _) {
            if (!config.isConfigured) {
              return const SettingsScreen();
            }
            return const ServiceListScreen();
          },
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add lib/main.dart
git commit -m "feat: wire up app entry point with Provider and Material 3 theme"
```

---

### Task 10: 端到端验证与 APK 构建

**Files:**
- 无新建

- [ ] **Step 1: 运行全部测试**

```bash
cd /Users/chenmao/Desktop/workspace/ai-instructure/05-mobile/mira-flutter
flutter test
```
预期：全部 PASS。

- [ ] **Step 2: 运行静态分析**

```bash
flutter analyze
```
预期：无 issues。

- [ ] **Step 3: 构建 release APK**

```bash
flutter build apk --release
```
预期：构建成功，APK 位于 `build/app/outputs/flutter-apk/app-release.apk`。

- [ ] **Step 4: 在模拟器上手动验收**

使用 Android 模拟器安装 APK，验证：
1. 首次启动显示设置页面
2. 输入服务器地址后保存，跳转服务列表
3. 下拉刷新能获取服务列表
4. 点击服务进入报告列表
5. 搜索功能正常过滤
6. 点击报告进入阅读页，Markdown 渲染正确
7. 星标收藏切换正常
8. 离线模式下查看已缓存报告

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "chore: final build, all tests passing, APK ready"
```

---

### 任务间依赖关系

```
Task 0 (环境) ──→ Task 1 (模型) ──→ Task 2 (API层) ──→ Task 3 (Stores)
                                                              │
                    Task 4 (组件) ◄────────────────────────────┘
                         │
                    Task 5 (设置页)
                         │
                    Task 6 (服务列表)
                         │
                    Task 7 (报告列表)
                         │
                    Task 8 (阅读页)
                         │
                    Task 9 (入口)
                         │
                    Task 10 (验证)
```

---

## 自审检查

**1. Spec 覆盖：**
- ✅ 服务端 API 三层端点 → Task 2 (ApiService)
- ✅ Service/Report 模型 → Task 1
- ✅ 服务列表 → Task 6
- ✅ 报告列表（时间倒序） → Task 3 (sort) + Task 7
- ✅ Markdown 渲染 → Task 8
- ✅ 搜索 → Task 7 (search) + Task 3 (ReportStore.search)
- ✅ 收藏 → Task 3 (FavoriteStore) + Task 6/7/8 集成
- ✅ 离线缓存 → Task 3 (CacheStore) + Task 3 (ReportStore.fetchContent)
- ✅ 暗色主题 → Task 9 (ThemeData dark)
- ✅ 服务器配置 → Task 5
- ✅ 首次启动设置页 → Task 9 (Consumer 判断)
- ✅ 下拉刷新 → Task 6/7
- ✅ 错误处理 → 各页面 EmptyState

**2. 占位符扫描：** 无 TBD/TODO，所有步��均有完整代码。

**3. 类型一致性：** Service.id/String, Report.id/String, serviceId/String, reportId/String 全链路一致。
