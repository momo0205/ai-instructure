# mira-automation

`Mira` 是第三方上游仓库（`byteseek/Mira`）。本目录存放**我们自己写的、原本放在 `Mira/scripts/` 下的脚本**，
用于在换机器或上游重置后快速恢复。

## 为什么单独放一份

这些脚本是在 submodule 的工作区里直接写的，既没有提交到上游，也不属于上游。
一旦执行 `git -C Mira checkout .` 或重新 `submodule update`，就会丢失。

## 恢复方式

```bash
cp mira-automation/scripts/*.py 04-applications/investment-research/Mira/scripts/
```

脚本以 `Mira/` 为工作目录，通过 `Path(__file__).parent.parent` 定位项目根，
所以必须放回 `Mira/scripts/` 才能直接运行。

## 脚本清单

| 文件 | 用途 |
|---|---|
| `daily_scan.py` | 同花顺热点扫描 → 去重 → 排队研究，交易日 15:30 由 launchd 触发 |
| `mira_runner.py` | 批量拉数据 / 跑单只标的的研究流水线 |
| `auto_cleaner.py` | 自动清理过期案例与中间产物 |
| `test_data_pull.py` | 数据拉取的冒烟测试 |

## 长期方案

把 `byteseek/Mira` fork 到自己名下，把这几个脚本提交到 fork 的 `main`，
再把 submodule 指向 fork —— 这样它们才真正进入版本控制。
在此之前，本目录是唯一的备份。
