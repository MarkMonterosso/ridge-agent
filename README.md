<p align="center">
  <img src="assets/ridge-logo.png" alt="RIDGE logo" width="220">
</p>

## RIDGE — Repository Intelligence Documentation & Generation Engine

Every project leaves a trail: commits, notes, decisions made and reversed. The reasoning behind the work lives in that trail, and it is normally lost — commits record what changed, not why.

RIDGE reads that trail and turns it into a record worth keeping. It runs weekly, reads authored markdown and git metadata from a project's archive, and drafts a field note describing what happened and why. Facts are assembled deterministically; only the prose is written by a model. Every claim traces back to a source record.

Output is a pull request. A human reviews and merges. RIDGE does not publish, does not author plans, and does not modify the records it reads.

Runs locally on open tooling. Model-agnostic by configuration. Built to be reused across projects.

### Status

RIDGE is built one phase at a time (Define, Design, Boundaries, Decide, Plan, Build, Integrate, Operate), and each phase closes with a written decision before the next one starts. Define, Design, Boundaries, Decide, and Plan are closed. Build is underway.

Right now RIDGE can load its config, find a project, and read that project's marker file. It then walks the archive's folders and reads every record it finds, checking each one for a required id and a real date. A record that fails that check is logged and skipped, not silently included. Two records that share the same id are also flagged. It doesn't yet read a project's git history, or write anything back out.

Weekly progress is written up by hand until RIDGE can write it itself: [redmountainindustries.com/projects/ridge](https://www.redmountainindustries.com/projects/ridge)

### Requirements

- Python 3.11+
- [LM Studio](https://lmstudio.ai/) running locally, serving a local model over its OpenAI-compatible API
- A GPU with roughly 16GB+ VRAM, enough to run a ~26B parameter model locally at a reasonable quantization

### Setup

Install the runtime dependencies:

```
pip install -r requirements.txt
```

Contributing, or want to run the tests and linter yourself? Install the development dependencies instead — this includes everything in `requirements.txt`, plus `pytest` and `ruff`:

```
pip install -r requirements-dev.txt
```

### Project structure

| File | What it does |
| --- | --- |
| `main.py` | Entry point. Parses command-line arguments and runs the pipeline in order. |
| `config.py` | Reads `config.yml` and a tracked project's `ridge.yml` marker file. |
| `records.py` | Walks a project's archive folders, validates each record, and checks for duplicate ids. |
| `file_io.py` | Shared file-reading helper, used by `config.py` and `records.py`, that always reads as UTF-8. |
| `tests/` | The test suite. One file per module above (`test_config.py`, `test_file_io.py`, `test_records.py`). |
| `conftest.py` | Empty on purpose — its presence tells pytest where the project root is, so tests can import the modules above. |

### Configuration

RIDGE reads a `config.yml` file. Copy `config.example.yml` to `config.yml` to get started. `config.yml` is gitignored, since it holds paths specific to your own machine.

`config.yml` lists the project archives RIDGE should track:

```yaml
projects:
  - ../path-to-your-project-archive
```

You can list more than one project here, but right now RIDGE only reads the first one in the list. Tracking several projects in one run is planned, not built yet.

Each listed folder is a project archive. It must contain a marker file, `ridge.yml`, at its root:

```yaml
id: my-project                  # stable identifier, never derived from the folder name
name: My Project
code_repo: ../my-project-code   # for git metadata (read-only)
site_slug: my-project           # which site page this project writes to
conventions:                    # optional — maps record types to folders
  sessions: docs/sessions/
  decisions: docs/decisions/
```

`conventions` is how RIDGE finds your session logs, decision records, and other authored files, without assuming any particular folder layout. Every project can name its own folders differently.

### Usage

```
py main.py
```

Point at a different config file with `--config`:

```
py main.py --config path/to/other_config.yml
```

Output right now is a short console summary — how many valid records were found, and any duplicate ids. RIDGE doesn't generate or publish a field note yet.

### Testing

Run the test suite from the `ridge-agent` folder:

```
pytest
```

Check code style with the linter:

```
ruff check .
```

### License

MIT, see [LICENSE](LICENSE).
