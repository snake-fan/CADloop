# CADloop

面向 **CAD agent harness** 的研究与论文仓库，统一承载文献调研、现有框架复现、多基准评测、自研框架和论文产物。

研究主线已确定为 **参数化 3D CAD 的建模与修改**：研究在固定基础模型、任务输入和预算下，工具接口、状态管理、执行反馈与修复策略如何影响结果。具体 benchmark、基础模型、CAD 内核和投稿目标仍待冻结。

## 当前状态

项目初始化已包含：

- 研究计划、复现协议、benchmark / 方法候选清单和论文提纲。
- 独立的论文目录、实验记录模板、上游复现记录模板与数据接入约定。
- 可运行的 Python harness 骨架：任务 / agent / backend / evaluator 接口，预算检查，逐题结果、轨迹和带校验值的运行记录。
- 两个合成 box 任务、脚本 agent、mock 元数据 backend，以及离线测试和 GitHub Actions 配置。

**目前可执行的是工程 smoke 自检。** 它不调用模型、不生成真实 CAD 几何，也不产生官方 benchmark 成绩。真实 CAD 后端、LLM provider、官方 benchmark adapter / scorer 和 SOTA 复现将在固定协议后逐项接入；候选清单不代表已验证的 SOTA 排名。

## 快速开始

需要 Python **3.9+** 和 `make`。离线自检没有第三方运行时依赖，不需要 API key、GPU 或下载数据。

在仓库根目录运行：

```bash
make doctor
make check
make smoke
```

`make smoke` 默认写入新的 `runs/smoke-<UTC 时间>/`。也可以指定一个空目录，运行后核验产物：

```bash
make smoke SMOKE_OUTPUT=runs/my-first-smoke
PYTHONPATH=src python3 -m cadloop summarize runs/my-first-smoke
```

程序拒绝覆盖非空运行目录；重复运行时请换一个目录名。CLI 也可直接执行：

```bash
PYTHONPATH=src python3 -m cadloop run \
  --config configs/experiments/smoke.json \
  --output-dir runs/another-smoke
```

`max_steps` 限制每题的工具调用次数；当前超时只在同步步骤之间检查。接入真实模型或 CAD 代码执行时，需要另行实现进程隔离和强制超时。

## 项目结构

```text
CADloop/
├── paper/                       # LaTeX 论文源文件与引用
├── docs/                        # 调研、研究计划、复现协议、架构和论文提纲
├── src/cadloop/                 # 公共接口、runner、CLI 与 mock smoke 实现
├── configs/
│   ├── benchmarks/             # benchmark 候选 registry
│   ├── baselines/              # harness / 方法候选 registry
│   └── experiments/            # 可执行实验配置
├── examples/                    # 可提交的小型合成样例
├── tests/                       # 无外部依赖的离线测试
├── third_party/                 # 上游复现说明与版本记录模板
├── data/                        # 数据接入说明；下载文件不入 Git
├── experiments/                 # 实验设计、预注册与日志模板
├── results/                     # 人工审阅后的结果表与图；当前无正式结果
└── runs/                        # 本地生成的逐次运行产物，不入 Git
```

每次 smoke 运行保留以下文件：

| 产物 | 用途 |
| --- | --- |
| `manifest.json` | 运行 ID、环境、Git 状态、预算、输入与产物 SHA-256 |
| `config.snapshot.json` / `tasks.snapshot.jsonl` | 本次配置与合成任务快照 |
| `trace.jsonl` | 每次工具动作、观察、耗时与任务 ID |
| `results.jsonl` | 逐题状态、工具调用数、耗时和合成检查结果 |
| `summary.json` | 状态计数与自检结论，明确标注 `rankable: false` |

`summarize` 会核验产物 hash、运行 ID、结果数量和工具调用记录的一致性。正式实验还需补齐模型 / prompt / CAD 内核 / 数据 / scorer 的固定版本和对应预算。

## 研究与复现入口

| 工作线 | 入口 | 初始化后的下一步 |
| --- | --- | --- |
| 研究设计 | [研究计划](docs/research_plan.md) | 固定任务范围、首个 benchmark、主要指标和预算 |
| 文献与基准 | [候选矩阵](docs/benchmark_matrix.md)、[registry](configs/benchmarks/registry.json) | 复核官方协议、许可、split 与 scorer 可用性 |
| 现有框架复现 | [复现协议](docs/reproduction_protocol.md)、[上游记录](third_party/README.md) | 固定一个候选框架的 commit 和独立环境，跑通官方最小样例 |
| 自研 harness | [架构](docs/architecture.md)、[实验模板](experiments/experiment.template.md) | 根据基线失败轨迹提出可证伪机制并设计消融 |
| 论文 | [论文提纲](docs/paper_outline.md)、[论文源码](paper/main.tex) | 先写问题定义、协议和方法；结果由真实运行支撑 |

建议首个里程碑是：**选定一个 benchmark → 复现一个上游基线 → 在固定的小型开发子集上跑通真实 CAD 产物和官方评分 → 再冻结正式比较协议。** 原始论文协议复现与统一预算下的横向比较分别记录。

论文采用通用 LaTeX 起稿，待选定投稿场所后更换官方模板。安装 TeX 工具链后可运行 `make paper`；本地 Python 自检不依赖 LaTeX。

## 实验约定

- 官方 split 和 scorer 保持可追溯；参考答案只提供给 evaluator。
- 失败、超时、预算耗尽保留在分母中；实验前写明重复次数、预算与筛选规则。
- 上游代码与数据分别记录版本和许可；大数据、权重、API key 与原始运行目录不入 Git。
- 论文结论关联逐题产物和实验记录；不将 smoke、候选方法或论文报告值当作本地实测成绩。

开发约定见 [AGENTS.md](AGENTS.md)。修改后运行 `make check`，涉及实验链路时再运行 `make smoke`。
