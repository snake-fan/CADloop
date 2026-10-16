# Data workspace

真实 benchmark 数据尚未下载；当前可运行样例位于 `examples/`。

本地数据按 `raw/<benchmark>/<version>/`、`processed/<benchmark>/<version>/` 和 `cache/` 放置，这些目录均由 Git 忽略。adapter 必须记录来源、版本或 checksum、官方 split 和预处理步骤，并能从原始样本回溯到 task ID。

每次接入先在 `configs/benchmarks/registry.json` 核实记录，再更新 adapter 和 `docs/benchmark_matrix.md`。没有官方 split 时，应先确定独立的开发集与测试集；不得反复在测试集上选择 prompt 或 harness 参数。

参考 CAD、隐藏评分信息与公开输入分离。用于调试的本地子集不等同于完整官方测试集。数据许可、模型许可与仓库代码许可分别按上游实际说明记录。
