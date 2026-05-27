# Candor

> Automated code review via a fine-tuned local LLM trained on your repo's own PR history.

[![CI](https://img.shields.io/github/actions/workflow/status/nidhijadhav/candor/test.yml?branch=main&label=tests)](https://github.com/nidhijadhav/candor/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](#contributing)

---

## The problem

Code review is a bottleneck. Senior engineers spend disproportionate time on mechanical review work — style issues, missing tests, obvious bugs, naming problems — that could be automated. General-purpose cloud LLMs are expensive to run on every PR and have no awareness of your codebase's specific patterns. Linters catch syntax. Nothing catches the stuff in between.

## How Candor works

Candor fine-tunes a local language model on a repository's own merged PR history. It learns what *your* team actually flags in reviews — the patterns, conventions, and anti-patterns specific to your codebase — then posts inline review comments automatically when a new PR is opened.

The model runs entirely on your own infrastructure. No code leaves your network. No per-request API cost.

```
GitHub PR opened
      │
      ▼
 Webhook handler
      │  raw diff
      ▼
 Orchestrator
      │  diff chunks + prompts
      ▼
 Local LLM (fine-tuned CodeLlama)
      │  review comments
      ▼
 GitHub PR Review
```

---

## Progress

### ✅ M1 — Data Pipeline (complete)

- GitHub API collector: fetches all merged PRs from a target repo with pagination, rate limiting, and checkpointing
- Curation pipeline: filters by comment quality, reviewer association, recency, and deduplicates using TF-IDF similarity
- Training format processor: converts curated data to instruction-tuning format with 80/10/10 train/val/test split by PR number

Currently trained on **trinodb/trino** — 13,463 merged PRs, curated down to **18,928 high-quality (diff, review comment) pairs**.

### ✅ M2 — Fine-Tuning (complete)

- QLoRA fine-tune of CodeLlama-13B-instruct on 15,177 training examples
- Trained for 2 epochs on a single A100 GPU via Google Colab
- Final training loss: 0.61
- Adapter weights saved and versioned

### ✅ M3 — Inference (complete)

- LoRA adapter merged into base model and converted to GGUF format
- Served locally via llama.cpp on Apple Silicon (Metal) or Linux (CUDA)
- OpenAI-compatible `/v1/chat/completions` API
- Output formatter parses model responses into structured `ReviewComment` objects

### ✅ M4 — Orchestrator (complete)

- Diff parser: splits unified diffs into `DiffChunk` objects with hunk extraction and edge case handling
- Prompt assembler: enforces token budget, injects guidelines, formats CodeLlama instruction template
- Runner: wires the full pipeline — parse → assemble → infer → format → deduplicate → return
- Full unit test coverage across all components

### 🔲 M5 — GitHub Integration (in progress)

- [ ] GitHub App registration and webhook handler
- [ ] PR event listener (opened, synchronize, reopened)
- [ ] Post results as a GitHub Pull Request Review
- [ ] Jenkins CI/CD pipeline step

### 🔲 M6 — Dev Experience

- [ ] `pyproject.toml` and setup script
- [ ] CI workflow
- [ ] Contributing guide and architecture docs
- [ ] ADRs for key design decisions

---

## Quickstart

### Prerequisites

- Python 3.10+
- [llama.cpp](https://github.com/ggerganov/llama.cpp) (`brew install llama.cpp` on macOS)
- A merged GGUF model (see [docs/inference_setup.md](docs/inference_setup.md))

### Setup

```bash
git clone https://github.com/nidhijadhav/candor.git
cd candor
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in GITHUB_TOKEN and target repo
```

### Run a review

Start the inference server:

```bash
python inference/server/start.py --model models/trino-merged.gguf
```

Run the orchestrator on a diff file:

```bash
PYTHONPATH=. python orchestrator/run.py --diff path/to/your.diff
```

### Collect training data from a repo

```bash
python data/collect.py          # fetch raw PR data
python data/curate.py           # filter and clean
python data/process.py          # format for training
```

---

## Project structure

```
candor/
├── data/                   # Data pipeline (collect → curate → process)
├── training/               # Fine-tuning notebook and configs
├── inference/
│   ├── server/             # llama.cpp inference server wrapper
│   └── formatter/          # Structured output parser
├── orchestrator/
│   ├── chunker/            # Unified diff parser
│   ├── prompt/             # Prompt assembler
│   └── run.py              # End-to-end pipeline runner
├── integrations/
│   ├── github_app/         # GitHub webhook handler (M5)
│   └── jenkins/            # CI pipeline step (M5)
├── scripts/                # Utilities (merge_adapter, sample_review)
├── docs/                   # Setup guides and architecture docs
└── tests/                  # Unit and integration tests
```

---

## Design decisions

Key architectural choices are documented in [docs/decisions/](docs/decisions/). Short version:

**Why local LLM?** Cost, privacy, and relevance. Cloud LLMs charge per token and have no knowledge of your codebase. A locally-run fine-tuned model learns your team's specific patterns and runs at zero marginal cost per review.

**Why fine-tune instead of prompt engineer?** A well-prompted general model will catch obvious issues. A model trained on 18,000 real review comments from your repo will catch the things your team actually cares about.

**Why LoRA?** Fine-tuning all 13 billion parameters of CodeLlama would require enormous compute. LoRA freezes the base model and trains only small adapter matrices, producing a ~500MB adapter file rather than a 26GB model copy.

**Why Trino as the training corpus?** Large, active Java project with thousands of merged PRs and high-quality reviews from experienced engineers. Good signal density and publicly available.

---

## Tech stack

| Component | Technology |
|---|---|
| Base model | CodeLlama-13B-instruct |
| Fine-tuning | QLoRA via Hugging Face PEFT + TRL |
| Inference | llama.cpp (local) |
| Data collection | GitHub REST API |
| Orchestrator | Python, FastAPI (M5) |
| GitHub integration | GitHub App + webhook (M5) |

---

## Contributing

Contributions are welcome. Candor is early-stage and there's a lot of ground to cover.

Good first areas to contribute:

- **More training repos** — the data pipeline works against any public GitHub repo. PRs adding support for other languages or ecosystems are very welcome.
- **Evaluation harness** — the eval script computes ROUGE-L but human eval tooling would be valuable.
- **GitHub App** — M5 is the next milestone. If you've built GitHub Apps before, this is a great place to jump in.
- **Docs** — architecture docs and ADRs are sparse. Any improvements help.

To get started: fork the repo, create a branch, open a PR. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide (coming in M6).

---

## Roadmap

| Milestone | Status |
|---|---|
| M1 Data Pipeline | ✅ Complete |
| M2 Fine-Tuning | ✅ Complete |
| M3 Inference | ✅ Complete |
| M4 Orchestrator | ✅ Complete |
| M5 GitHub Integration | 🔲 In progress |
| M6 Dev Experience | 🔲 Planned |
| Cloud deployment | 🔲 Future |

---

## License

MIT
