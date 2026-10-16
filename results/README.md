# Reviewed results

这里保存从真实实验产物导出、经人工审阅、适合论文引用的 CSV/JSON 与图表。初始化没有真实 benchmark 成绩。

每张表至少关联 benchmark、split、数据和 scorer 版本、方法、模型、预算、重复次数、样本数及运行 manifest。记录失败和缺失；没有测量的数据写 `NA`，不要写 0。smoke 结果不能进入正式排行榜或论文性能表。

临时分析放在 `local/`，原始执行日志放在 `runs/`，两者均由 Git 忽略。论文正式图表可保存到 `paper/figures/`。
