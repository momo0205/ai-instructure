# Git Tools 变更日志

所有重要的变更都会记录在此文件中。

---

## [1.0.1] - 2026-01-20

### commit-msg

- **docs**: 优化 description，增加触发词说明（「生成 commit」「写 commit message」「提交代码」「帮我 commit」）
- **docs**: 明确支持智能推断 type 和 scope，输出英文 subject + body

---

## [1.0.0] - 2026-01-18

### commit-msg

- 初始版本
- 支持基于 staged diff 生成 Conventional Commits 规范的 commit message
- 实现 Type 和 Scope 智能推断
- 支持 `--paths` 参数指定文件路径
- 完整的异常处理流程
