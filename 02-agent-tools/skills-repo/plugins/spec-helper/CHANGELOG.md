# Changelog

本文件记录 Spec Helper 插件的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [0.2.0] - 2026-01-19

### Removed

- **tech-doc-organizer**: 移除"技术实施手册"文档类型
  - 从文档类型概览表中移除该项
  - 从 `document-types.md` 详细规范中移除对应章节
  - 更新所有目录结构示例
  - 实施计划将由其他地方承载

### Changed

- **tech-doc-organizer**: 文档类型数量从 8 种调整为 7 种
- **tech-doc-organizer**: 后续文档编号顺延（Task List、CR Issues、验收检查清单、Backlog）

---

## [0.1.0] - 2026-01-18

### Added

- 初始版本发布
- 新增 `tech-doc-organizer` Skill：技术驱动型开发文档组织规范
  - 支持 Overview、需求分析、技术调研、初步设计、ADR、技术设计等文档类型
  - 支持 Task List、CR Issues、验收检查清单、Backlog 等后续文档
  - 提供文件命名规则和层级编号规范
  - 提供详细的文档类型规范参考
