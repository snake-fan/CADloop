# SOTA reproduction workspace

这里用于记录上游方法复现，目前没有克隆或安装任何上游项目。候选来源见 `docs/benchmark_matrix.md`。

上游代码放在本地 `checkouts/<method>/`，独立创建环境。不要直接向公共 smoke 环境安装所有项目的依赖。正式开始某项复现时，复制 `reproduction.template.json` 为 `<method>.json`，填写固定 commit、原文任务与预算、安装命令、官方评测命令、数据版本和实际状态。

状态建议：`candidate → source_verified → environment_ready → smoke_passed → reproduced`。只有完成指定 split 的官方 scorer 并核对原文差距后，才使用 `reproduced`。完成统一协议的迁移实验不自动等于复现原论文。
