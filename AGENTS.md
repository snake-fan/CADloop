# CADloop working conventions

这是 CAD harness 研究与论文仓库。研究主线是参数化 3D CAD 的建模、修改与执行反馈；具体任务轨道、benchmark 与投稿目标以研究计划和冻结协议为准。

## Project map

- `paper/`：论文源文件；`docs/`：研究决策、协议和调研。
- `src/cadloop/`：公共实验接口与自研 harness。
- `configs/`：实验配置和候选 registry；`examples/`：可提交的小型合成样例。
- `tests/`：离线验证；`experiments/`：预注册实验与实验日志模板。
- `data/`：数据接入说明；`third_party/`：复现入口与上游版本记录。
- `results/`：人工审阅后的论文结果；`runs/`：本地生成且不纳入 Git 的运行产物。

## Research integrity

1. 不编造引用、SOTA 身份、复现完成状态或实验结果。候选方法必须有原始来源，SOTA 比较必须绑定任务、split、版本和预算。
2. smoke 使用合成任务、脚本 agent 和 mock backend，只验证工程链路；不得作为 CAD 几何指标或排行榜成绩。
3. 真实评测必须保留官方 split、scorer 版本、数据版本、模型版本、prompt、运行配置和逐题产物。不得静默替换官方 scorer。
4. agent 只能看到公开任务输入；参考答案与评估数据归 evaluator，不能通过 prompt、工具或日志回流到 agent。
5. 复现遵循上游固定 commit 的独立环境。原始论文协议复现与统一预算比较分别报告。
6. 失败、超时和预算耗尽保留在分母中。不能只汇报成功样本；预算口径、重复次数和筛选规则在正式实验前确定。
7. 新框架机制先提出可证伪假设，再设计消融；论文结论必须能追溯到运行产物。

## Development

- 用中文解释研究决策；Python 标识符、论文正文和源码注释可使用英文。
- 保持轻量 smoke 可用，不让 CAD 内核、GPU、API key 或大数据下载成为初始化测试依赖。
- 在本仓库修改后运行 `make check`；涉及实验链路时再运行 `make smoke`。
- 不提交 API key、私有 prompt、大型数据、模型权重、上游 checkout 或未经审阅的运行目录。
- 不自动替用户提交排行榜、发送消息或发布论文。
