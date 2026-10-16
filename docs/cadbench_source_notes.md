# CAD Bench V3 Source Notes

This file records a read-only source investigation of the Parametric CAD Bench
site and Harbor task service. It is not an official benchmark result and does
not contain downloaded benchmark artifacts.

## Canonical sources

- Website and run instructions: <https://cadbench.ai/cad-bench/benchmark>
- Harbor dataset, current V3: <https://hub.harborframework.com/datasets/gnucleus-ai/cad-bench/v3>
- Harbor task index API:
  `https://hub.harborframework.com/api/datasets/gnucleus-ai/cad-bench/v3/tasks`
- Submission portal: <https://github.com/gNucleus-AI/cad-bench-submission>
- Validator repository: <https://github.com/gNucleus-AI/freecad-validator>
- Source CAD dataset link advertised by the site:
  <https://huggingface.co/datasets/gnucleus-ai/cad-gen-freecad>

The submission repository is `gNucleus-AI/cad-bench-submission`; it is a
lightweight manifest and audit portal, not the task-data checkout. Its README
states that Harbor stores the heavy job/trial artifacts and that submissions
must point to a complete public Harbor job. The repository's `LICENSE` is
Apache-2.0. This does not establish a license for the Harbor task data or the
Hugging Face source dataset.

## V3 identity and official run contract

The website currently describes V3 as 100 parametric FreeCAD tasks:

- 30 text-to-CAD creation tasks
- 30 text-to-CAD create-and-edit tasks
- 40 image-to-CAD / engineering-drawing tasks

The run page identifies Harbor `0.23.0`, task schema `1.3`, FreeCAD `1.1.0`,
`gnucleus-freecad-validator 0.6.0`, a 9,000-second task time limit, and the
dataset digest:

```text
sha256:8a786725d3648a76282fc5868df06da3d5e00d603f283573a53430803465d78a
```

The documented full run is:

```bash
uv tool install harbor==0.23.0
harbor run -d gnucleus-ai/cad-bench@v3 \
  -a <your-agent> -m <your-model> \
  --n-concurrent 4 --n-attempts 1 --max-retries 0 \
  --upload --public
```

The complete 100-task cohort, one attempt per task, retries disabled, and
preservation of failures are part of the official submission contract. A
partial/local run is a demo and cannot be represented as a leaderboard score.

## Public task index and file API

The task index currently returns 100 records with fields like:

```json
{
  "id": "01df935b-ec0b-44aa-b33c-358162f5be49",
  "task_version_id": "01df935b-ec0b-44aa-b33c-358162f5be49",
  "available": true,
  "org_name": "gnucleus-ai",
  "task_name": "freecad-6b54209a13",
  "revision": 1
}
```

For a task `org_name=gnucleus-ai`, `task_name=freecad-6b54209a13`, the public
task page is:

```text
https://hub.harborframework.com/tasks/gnucleus-ai/freecad-6b54209a13
```

The page advertises this command:

```bash
harbor run -t gnucleus-ai/freecad-6b54209a13
```

Public file content is available under:

```text
https://hub.harborframework.com/api/tasks/gnucleus-ai/freecad-6b54209a13/latest/files/<path>
```

The public agent-facing files for this example are:

- `instruction.md`
- `task.toml`
- `environment/6b54209a13.png` (for the engineering-drawing task)
- the environment files needed to build the task image

`instruction.md` asks the agent to write `/app/answer.py` and produce
`/app/answer.FCStd`, with exactly one parametric PartDesign Body. The public
`task.toml` declares schema `1.3`, those two artifacts, a separate verifier,
agent timeout `9000`, and agent `network_mode = "no-network"` unless the run
configuration explicitly allows the model provider. It also sets the FreeCAD
environment to 1.1.0 through the task image.

The task page also exposes paths under `solution/` and `tests/grader/` (for
example, `reference.FCStd` and `spec.json`). These are evaluator/reference
materials and must never be fetched, copied into an agent prompt, or included
in a public-task loader. The loader should use an explicit allowlist for
agent-facing files rather than recursively downloading the task tree.

## Version notes

The Harbor dataset has historical V1 and V2 revisions as well as V3. The
submission portal README says V1 is frozen and V2 is current for that repository
snapshot, but the website's current run page targets V3. Do not mix versions:
bind every experiment to the exact tag, digest, FreeCAD/scorer versions, and
Harbor schema.

## License and redistribution status

The submission portal is Apache-2.0. Task images include Apache-2.0/LGPL notices
for bundled runtime components, but that is not a clear license grant for the
benchmark task collection itself. The public pages reviewed here did not expose
a definitive dataset license. Keep the loader metadata-only or fetch task
inputs at run time until Harbor/Hugging Face licensing and redistribution terms
are verified from their authoritative cards/terms.

## Reproducibility and integrity cautions

- The official scorer is hermetic and reference geometry is held back in the
  task image; do not claim a score from generated files without the matching
  verifier environment.
- Failed or unscored trials count as zero.
- A public Harbor job must retain task config/digests, generated `.FCStd` and
  script artifacts, full trajectory, logs, and verifier output.
- API keys belong in the process environment only. Never commit them or place
  them in task snapshots, prompts, manifests, or logs.


## Reproduced public API examples (read-only)

The V3 index endpoint returned 100 records on 2026-10-16. For the first
engineering-drawing task (`freecad-6b54209a13`), the public file API returned
`instruction.md` and `task.toml`; `environment/6b54209a13.png` was a 1692×930
PNG. The task instruction specifies `/app/answer.py` and `/app/answer.FCStd`.
No reference or grader file was used by the loader or demo harness.

The separately advertised source dataset `gnucleus-ai/cad-gen-freecad` does have
an Apache-2.0 dataset card. It documents columns `id`, `name`, `description`,
`key_parameters`, `image`, `fcstd_path`, and `viewer_url`; per-row assets are in
`fcstd/`, `glb/`, and `edges/`. That is the source CAD dataset, not proof that
all held-out Parametric CAD Bench task materials share those terms. The current
Harbor V3 dataset API is not anonymously readable from the Hugging Face API in
this environment, so its own data license remains unverified.
