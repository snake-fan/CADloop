# Experiment registry

正式实验前，从 `experiment.template.md` 建立一份实验卡片；运行后补充 manifest 路径、偏差、失败分析与决策。实验卡片可以提交到 Git，原始运行产物写入 `runs/`。当前初始化仅包含合成 smoke 配置。

建议顺序：上游原协议复现 → 固定模型与预算的基线对照 → 自研机制试验 → 单因素消融 → 跨任务验证 → 按官方要求整理提交。

正式配置应命名为 `<benchmark>__<method>__<model>__<budget>.json`，并记录重复 seeds；在相同 task ID 上做配对比较。先保留逐题输出，再从输出生成表格，禁止手工填写未经运行支持的成绩。
