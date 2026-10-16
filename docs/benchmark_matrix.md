# CAD benchmark 与 baseline 候选矩阵

核验日期：**2026-10-16**。本页只做初始化阶段的官方来源核验与接入排序，尚未复现任何方法、运行真实 CAD 评测或获得排行榜成绩。`P1` 表示建议优先调查接入成本，`P2` 表示辅助任务或后续拓展；优先级不表示性能排名。

机器可读条目分别位于 [benchmark registry](../configs/benchmarks/registry.json) 和 [baseline registry](../configs/baselines/registry.json)。所有候选均为 `source_status: source_verified`、`integration_status: not_integrated`、`reproduction_status: not_started`。`source_verified` 仅说明已核对官方来源及其声明的任务范围，不能解释为实现、分数或复现已通过验证。

## Benchmark 与数据

| 候选 | 类型与任务 | 输入 → 输出 | 接入价值与限制 | 优先级 |
| --- | --- | --- | --- | --- |
| [CADGenBench](https://github.com/huggingface/cadgenbench) | Benchmark；工程图生成 CAD、按指令修改 CAD | 图纸及描述，或初始 STEP 及修改要求 → 每题一个 STEP | 与执行、视觉反馈、修复机制研究直接相关；有官方迭代 baseline。公开数据卡当前声明 81 题，含 49 生成、32 修改，无 train/test split；GT 私有，正式分数由排行榜服务计算。 | P1 |
| [CADBench（anniedoris / DeCoDELab）](https://github.com/anniedoris/CADBench) | Benchmark；图像 / mesh 到 CAD 程序 | 单视图、多视图、PBR 图像，或 mesh / noisy mesh → CadQuery Python | 可覆盖不同模态与数据来源。官方 README 的子集名称与当前 HF 元数据不完全一致，接入前需确认映射。涉及多个原始数据许可。 | P1 |
| [SGP-Bench 的 CAD partitions](https://github.com/sgp-bench/sgp-bench) | Benchmark；CAD 程序理解与问答 | 符号图形 / CAD 程序及问题 → 答案 | 可用于 CAD-Assistant 原始协议复现与工具反馈能力研究；指标是理解 / 问答表现，不能直接代替几何建模质量。 | P2 |
| [DeepCAD](https://github.com/rundiwu/DeepCAD) | 数据集与原始生成 / 重建评测协议；同时也是模型名称 | CAD 构造序列 → 重建或随机生成的 CAD 序列 | 提供常用的参数化 CAD 数据来源及评测实现。原始 autoencoding / random generation 与后续 point-cloud-to-CAD、text-to-CAD 是不同任务；上游环境较旧。 | P2 |
| [Text2CAD](https://github.com/SadilKhan/Text2CAD) | 文本标注数据与 text-to-CAD 评测协议；同时也是生成模型名称 | 分层文字描述 → 顺序 CAD 表示 | 适合文本条件建模；数据基于 DeepCAD，需固定 v1.0 / v1.1、split 与去重规则。HF 元数据声明自动 gating 与 CC BY-NC-SA 4.0，尚未下载需接受条款的文件。 | P2 |

CADGenBench 官方指标包含有效性门控、形状相似度、接口匹配和拓扑匹配；generation 与 editing 的组合规则不同，应采用固定版本的 [官方指标说明](https://github.com/huggingface/cadgenbench/blob/33304cf771fc5639144b1df9611e347251052cf8/docs/metrics.md)。只运行公开数据附带的 validity helper 不能得到正式 CAD Score。官方数据卡说明 GT 存放在私有仓库；本次未授权访问的 GT API 返回 HTTP 401，未读取任何 GT。初始化不自动提交外部排行榜。

CADBench 在 [官方 README](https://github.com/anniedoris/CADBench/blob/99e41a2eeb351f04611e83980f9f23cb0ca216c7/README.md) 中仍出现 `bench0`、`bench0F`、`bench1A` 等名称；本次读取的 [HF 元数据](https://huggingface.co/api/datasets/DeCoDELab/CADBench) 暴露 `benchB`、`benchF`、`benchE`、`benchA`、`benchM`、`benchO`。二者存在待确认的命名差异，因此这里不自行断言它们的对应关系。其 [数据许可说明](https://github.com/anniedoris/CADBench/blob/99e41a2eeb351f04611e83980f9f23cb0ca216c7/DATASET_LICENSE.md) 保留 DeepCAD、Fusion 360 Gallery、ABC、MCB 和 Objaverse 的各自条款。

## Harness 与方法

| 候选 | 类型 | 官方发布范围 | 建议用途与边界 | 优先级 |
| --- | --- | --- | --- | --- |
| [CAD-Assistant](https://github.com/dimitrismallis/CAD-Assistant) | Agent harness / 工具增强 VLLM 框架 | 生成并执行 FreeCAD 代码，提供 `sketch_recognizer` 与 `solid_recognizer`；发布了 SGP-Bench 2D / 3D 问答评测入口 | 优先复现其已发布的原始问答协议。迁移到 CADGenBench 生成 / 修改属于新适配，应与原始复现分别记录。README 声明 Attribution-NonCommercial 许可，使用前还需检查精确 LICENSE。 | P1 |
| [CADGenBench reference baseline](https://github.com/huggingface/cadgenbench) | 迭代 Agent harness | 生成 build123d / CadQuery 代码，执行、渲染并反馈修复，产出 STEP | 与主 benchmark 的输入 / 产物契约直接对齐，适合作为首个可比较的迭代 baseline。需固定模型、prompt、backend 和预算；它只生成候选，正式评测依赖私有 GT。 | P1 |
| [CAD-Recode](https://github.com/filaPro/cad-recode) | 训练后的 CAD 生成 / 重建模型 | Point cloud → CadQuery Python；官方链接 v1、v1.5 与相关后续资产 | 可作为 point-cloud 重建方向的专用方法对照，不属于 harness。与图纸 / 文本 agent 的比较必须使用同样的输入条件或单独开 track。 | P2 |

DeepCAD、Text2CAD、CAD-Recode 都不能仅因能输出 CAD 而归类为 agent harness。前两者还同时命名了数据或标注资源，registry 用 `artifact_type` 区分当前收录对象。CAD-Recode README 的历史 SOTA 描述属于上游在特定时间的声明；本仓库不据此给出当前 SOTA 排名。

## 已核验的原始来源与版本

本次通过 GitHub 仓库搜索识别候选，读取下表固定 commit 的官方 README，以 `git ls-remote ... HEAD` 记录审阅版本，并读取相关 HF 数据元数据 / 官方数据卡。GitHub 搜索随后遇到未认证 API rate limit，后续使用官方 raw README 与 Git 协议完成来源核验。没有 clone、安装、下载模型、运行推理或调用付费 API。

| 对象 | 官方来源与论文 | 本次审阅的 upstream commit |
| --- | --- | --- |
| CADGenBench | [官方 README](https://github.com/huggingface/cadgenbench/blob/33304cf771fc5639144b1df9611e347251052cf8/README.md) · [公开输入数据卡](https://huggingface.co/datasets/HuggingAI4Engineering/cadgenbench-data/blob/f76f965585817c621d6ea0d150d745adf670e66e/README.md) · 论文链接尚未从已读来源确认 | `33304cf771fc5639144b1df9611e347251052cf8` |
| CADBench | [官方 README](https://github.com/anniedoris/CADBench/blob/99e41a2eeb351f04611e83980f9f23cb0ca216c7/README.md) · [论文](https://arxiv.org/abs/2605.10873) | `99e41a2eeb351f04611e83980f9f23cb0ca216c7` |
| SGP-Bench | [官方 README](https://github.com/sgp-bench/sgp-bench/blob/e7906399beebb82ab5dcc4aa547eaec8674c9144/README.md) · [论文](https://arxiv.org/abs/2408.08313) | `e7906399beebb82ab5dcc4aa547eaec8674c9144` |
| DeepCAD | [官方 README](https://github.com/rundiwu/DeepCAD/blob/f7b350790a3bce0267a5345339fd09be0250c8cb/README.md) · [论文](https://arxiv.org/abs/2105.09492) | `f7b350790a3bce0267a5345339fd09be0250c8cb` |
| Text2CAD | [官方 README](https://github.com/SadilKhan/Text2CAD/blob/669a81472ede2269837c22a4d00070eaac360c82/README.md) · [论文](https://arxiv.org/abs/2409.17106) · [HF 数据元数据](https://huggingface.co/api/datasets/SadilKhan/Text2CAD) | `669a81472ede2269837c22a4d00070eaac360c82` |
| CAD-Assistant | [官方 README](https://github.com/dimitrismallis/CAD-Assistant/blob/5fea47309b2db5245f9e01c7a2445cce9dd2d07e/README.md) · [论文](https://arxiv.org/abs/2412.13810) | `5fea47309b2db5245f9e01c7a2445cce9dd2d07e` |
| CAD-Recode | [官方 README](https://github.com/filaPro/cad-recode/blob/03e3262119b38939feaa44b8368ad8db99243d47/README.md) · [论文](https://arxiv.org/abs/2412.14042) | `03e3262119b38939feaa44b8368ad8db99243d47` |

上述 commit 是 `reviewed_upstream_commit`，只固定本页陈述的来源快照。真正复现时仍需决定原论文版本还是当前版本，另行填写 `reproduction_commit`；不能把当前 HEAD 自动视为原论文实现版本。数据同理：registry 记录了已查询到的 HF revision，正式实验所用 revision、split、checkpoint 和校验和仍需在复现清单中固定。未确认的字段明确为 `null`。

## 名称歧义与下一步筛选

GitHub 搜索至少返回 [anniedoris/CADBench](https://github.com/anniedoris/CADBench)、[ThomasRochefortB/cadbench](https://github.com/ThomasRochefortB/cadbench) 和 [FuturePresentLabs/cadbench](https://github.com/FuturePresentLabs/cadbench) 等同名项目。前者 README 明确关联 *CADBench: A Multimodal Benchmark for AI-Assisted CAD Program Generation*，且 [arXiv 页面](https://arxiv.org/abs/2605.10873) 的论文标题与之相符，因此本 registry 用完整 repo 身份消歧。其他同名项目不因此视为该论文 benchmark 的实现。

`CAD-Agent` 一词也会命中多个不同项目；本次没有确认一个可唯一对应目标论文的官方身份，因此不把它写入待复现清单。这里也不做完整 SOTA 覆盖。新增候选应先补原论文 / 作者官方代码链接，明确任务和实际发布范围，再进入统一比较。

建议首先决定主研究 track：工程图生成与 STEP 修改可从 CADGenBench 及其 reference baseline 着手；需要验证工具增强理解能力时复现 CAD-Assistant / SGP-Bench。CADBench 可作为另一组跨模态 CAD 程序生成评测，接入前解决 subset 名称、输入契约和 scorer 对齐。DeepCAD / Text2CAD 的派生关系意味着后续应做样本重叠检查，避免把相关测试集当成相互独立的泛化证据。
