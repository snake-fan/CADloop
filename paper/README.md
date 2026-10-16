# 论文目录

`main.tex` 是通用 `article` 骨架；当前正文为英文占位说明，研究计划与论文论证约束见 [`docs/paper_outline.md`](../docs/paper_outline.md)。本仓库尚无真实 CAD benchmark 分数，LaTeX 不包含结果表。

如本机安装 TeX Live / MacTeX，可从此目录构建：

```bash
latexmk -pdf main.tex
```

或使用 `pdflatex → bibtex → pdflatex → pdflatex`。初始化流程不自动安装 TeX，也不保证当前机器具有编译环境。

`references.bib` 初始条目来自已读官方仓库或项目页。投稿前仍需逐一核对作者、venue、年份与引用格式；确定目标 venue 后再替换模板。未验证的文献不要填入占位 BibTeX 条目。
