# CADloop

面向 **CAD agent harness** 的研究与论文仓库，统一承载文献调研、现有框架复现、多基准评测、自研框架和论文产物。

研究主线已确定为 **参数化 3D CAD 的建模与修改**：研究在固定基础模型、任务输入和预算下，工具接口、状态管理、执行反馈与修复策略如何影响结果。具体 benchmark、基础模型、CAD 内核和投稿目标仍待冻结。

## 当前状态

项目初始化已包含：

- 研究计划、复现协议、benchmark / 方法候选清单和论文提纲。
- 独立的论文目录、实验记录模板、上游复现记录模板与数据接入约定。
- 可运行的 Python harness 骨架：任务 / agent / backend / evaluator 接口，预算检查，逐题结果、轨迹和带校验值的运行记录。
- 两个合成 box 任务、脚本 agent、mock 元数据 backend，以及离线测试和 GitHub Actions 配置。

**目前可执行的是工程 smoke 自检和 agent 接线 demo。** smoke 不调用模型、不生成真实 CAD 几何，也不产生官方 benchmark 成绩。Codex、Claude Code 和 mini-SWE-agent 已有统一适配入口；真实 provider 连通性、CAD 后端、官方 benchmark scorer 和 SOTA 复现仍需在固定协议后逐项验证。候选清单不代表已验证的 SOTA 排名。

## 快速开始

离线 harness 需要 Python **3.9+** 和 `make`；agent / Harbor 集成环境由 `uv` 使用 Python **3.12** 管理。

在仓库根目录运行：

```bash
make bootstrap
make doctor
make check
make smoke
```

首次准备集成环境和公开 benchmark 索引时运行：

```bash
make prepare
```

这会根据 `pyproject.toml` 与 `uv.lock` 创建 `.venv`，安装固定的
mini-SWE-agent `2.4.6` 与 Harbor `0.23.0`，检查 Codex、Claude Code、Harbor
和 mini 的可用性，并下载 CAD Bench V3 的公开任务索引到
`runs/cadbench-v3-index/tasks.jsonl`。索引不包含任务镜像、参考几何或
evaluator 文件；这些文件由正式 Harbor 运行按固定数据集版本处理。

`make bootstrap`（也可用 `npm run setup`）会创建被 Git 忽略的运行、缓存和
上游 checkout 目录，并报告 Codex、Claude Code、mini-SWE-agent、Harbor、
FreeCAD、uv 和 npm 的可用性。它不安装依赖、不下载 benchmark，也不读取或
写入 API key。需要检查第三方 OpenAI-compatible provider 时，把 key 临时
放在当前进程环境中。`make provider-check` 也会安全读取仓库根目录的
`.env`；环境变量优先于 `.env`，任何 key 都只在当前进程中使用：

`make uv-doctor` 会检查 `.venv` 中锁定的 agent / benchmark 版本；`make
cadbench-run` 提供 V3 的本地 Harbor 运行入口，默认不上传结果。正式运行
仍需模型 provider、FreeCAD 任务镜像和相应凭据，部分 demo 不能作为
leaderboard 成绩。

```bash
make provider-check
```

provider 检查默认请求 `https://us.ruiyumaas.com/v1` 的 `/models`、
`/chat/completions` 和 `/responses`，报告不会保存 Authorization header 或
完整响应。Claude Code 需要单独的 Anthropic Messages-compatible endpoint；
OpenAI provider 检查通过不代表 Claude Code 协议可用。

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
│   ├── agents.json              # agent CLI 与 provider 协议 registry
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
| CAD Bench V3 demo | [加载与 demo 说明](docs/cadbench_v3.md)、[V3 registry](configs/benchmarks/cadbench_v3.json) | 先加载公开任务索引，再在不上传的前提下跑少量 agent demo |

建议首个里程碑是：**选定一个 benchmark → 复现一个上游基线 → 在固定的小型开发子集上跑通真实 CAD 产物和官方评分 → 再冻结正式比较协议。** 原始论文协议复现与统一预算下的横向比较分别记录。

论文采用通用 LaTeX 起稿，待选定投稿场所后更换官方模板。安装 TeX 工具链后可运行 `make paper`；本地 Python 自检不依赖 LaTeX。

## 实验约定

- 官方 split 和 scorer 保持可追溯；参考答案只提供给 evaluator。
- 失败、超时、预算耗尽保留在分母中；实验前写明重复次数、预算与筛选规则。
- 上游代码与数据分别记录版本和许可；大数据、权重、API key 与原始运行目录不入 Git。
- 论文结论关联逐题产物和实验记录；不将 smoke、候选方法或论文报告值当作本地实测成绩。

开发约定见 [AGENTS.md](AGENTS.md)。修改后运行 `make check`，涉及实验链路时再运行 `make smoke`。
