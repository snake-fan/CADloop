# Parametric CAD Bench V3

CAD Bench V3 的官方运行入口是 Harbor Hub，不是一个包含完整任务数据的 Git checkout：

- 官网：[cadbench.ai/cad-bench/benchmark](https://cadbench.ai/cad-bench/benchmark)
- 固定数据集：[gnucleus-ai/cad-bench@v3](https://hub.harborframework.com/datasets/gnucleus-ai/cad-bench/v3)
- 任务索引 API：`https://hub.harborframework.com/api/datasets/gnucleus-ai/cad-bench/v3/tasks`
- submission repository：[gNucleus-AI/cad-bench-submission](https://github.com/gNucleus-AI/cad-bench-submission)
- validator：[gNucleus-AI/freecad-validator](https://github.com/gNucleus-AI/freecad-validator)

官方源调查、公开文件 API 和 evaluator 文件隔离记录见
[docs/cadbench_source_notes.md](cadbench_source_notes.md)。

V3 包含 100 个参数化 FreeCAD 任务：30 个 text-to-CAD creation、30 个 create-and-edit、40 个 image-to-CAD / engineering drawing。固定环境为 Harbor `0.23.0`、Harbor schema `1.3`、FreeCAD `1.1.0` 和 `gnucleus-freecad-validator 0.6.0`，数据集 digest 为：

```text
sha256:8a786725d3648a76282fc5868df06da3d5e00d603f283573a53430803465d78a
```

## 加载公开任务索引

用 `make prepare` 创建锁定的 `uv` 环境并下载完整 100 条公开任务索引。该
步骤不取回任务镜像、参考几何或 evaluator 文件。

这一步只读取任务 ID、版本和 revision 等公开元数据，不下载任务镜像，也不读取 `solution/`、`tests/grader/` 等 evaluator 文件：

```bash
PYTHONPATH=scripts python3 scripts/cadbench.py inspect
PYTHONPATH=scripts python3 scripts/cadbench.py index \
  --limit 3 \
  --output runs/cadbench-v3-index/tasks.jsonl
```

如果已有本地公开任务导出，可以转成给 agent 使用的 JSONL。加载器会删除 `answer`、`reference`、`ground_truth`、`verifier`、`reward` 等敏感字段：

```bash
PYTHONPATH=scripts python3 scripts/cadbench.py load \
  path/to/public-tasks.jsonl \
  --limit 3 \
  --output runs/cadbench-v3-demo/public_tasks.jsonl
```

完整的本地运行入口是 `make cadbench-run`，默认使用 Codex 和 `gpt-5.6-sol`，
按完整 100-task、单次尝试、零重试配置运行且不上传：

```bash
make cadbench-run HARBOR_AGENT=codex HARBOR_MODEL=gpt-5.6-sol
```

启动前仍要配置可用的模型 provider 和 Harbor 所需凭据，并准备 FreeCAD task
image 运行条件。完整官方命令也可只打印、不执行：

```bash
PYTHONPATH=scripts python3 scripts/cadbench.py command \
  --agent '<agent>' --model 'gpt-5.6-sol'
```

官网的完整榜单命令使用 `--n-attempts 1 --max-retries 0`，要求完整 100-task public Harbor job。少量 task 的本地试跑只能作为 demo，不能写成 benchmark 分数或 leaderboard 结果。

## 本地 agent demo

`examples/cadbench_demo_tasks.jsonl` 是 3 个本地合成 CAD prompt，用于验证 CLI / provider 接线，不是 Harbor V3 样本。先做 dry-run，脚本只写公开 prompt、CLI 可用性和命令形状，不会发起模型请求：

```bash
PYTHONPATH=scripts python3 scripts/run_agent_demo.py \
  --tasks examples/cadbench_demo_tasks.jsonl \
  --agent all \
  --limit 3 \
  --model gpt-5.6-sol \
  --output-dir runs/cadbench-agent-plan
```

真实执行必须显式加入 `--execute`，并把凭据只放在当前子进程环境中。OpenAI-compatible URL 只用于 Codex/LiteLLM；Claude Code 需要单独的 Anthropic Messages-compatible URL 和 key：

```bash
OPENAI_API_KEY='...' \
ANTHROPIC_API_KEY='...' \
PYTHONPATH=scripts python3 scripts/run_agent_demo.py \
  --tasks examples/cadbench_demo_tasks.jsonl \
  --agent codex \
  --limit 1 \
  --model gpt-5.6-sol \
  --base-url https://us.ruiyumaas.com/v1 \
  --claude-base-url https://anthropic-compatible.example/v1 \
  --output-dir runs/cadbench-codex-demo \
  --execute
```

结果会标记 `official_benchmark=false`、`rankable=false`。第三方网关必须分别兼容 Codex 的 OpenAI Responses API、mini-SWE-agent 使用的 LiteLLM/OpenAI 适配，以及 Claude Code 的 Anthropic Messages API；不能因为同一个 URL 能访问一个 CLI 就假设另外两个协议兼容。runner 不会读取、记录或写入 API key。

当前机器的集成环境状态由 `make uv-doctor` 报告：项目 `.venv` 提供固定版
mini-SWE-agent 与 Harbor，Codex CLI 和 Claude Code 是外部用户级 CLI。系统
Python 3.9 只用于离线 smoke；不会用它启动需要 Python 3.10/3.12 的集成工具。
