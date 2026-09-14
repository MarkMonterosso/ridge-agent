<p align="center">
  <img src="assets/ridge-logo.png" alt="RIDGE logo" width="220">
</p>

## RIDGE — Repository Intelligence Documentation & Generation Engine

Every project leaves a trail: commits, notes, decisions made and reversed. The reasoning behind the work lives in that trail, and it is normally lost — commits record what changed, not why.

RIDGE reads that trail and turns it into a record worth keeping. It runs weekly, reads authored markdown and git metadata from a project's archive, and drafts a field note describing what happened and why. Facts are assembled deterministically; only the prose is written by a model. Every claim traces back to a source record.

Output is a pull request. A human reviews and merges. RIDGE does not publish, does not author plans, and does not modify the records it reads.

Runs locally on open tooling. Model-agnostic by configuration. Built to be reused across projects.

### Status

RIDGE is built one phase at a time (Define, Design, Boundaries, Decide, Plan, Build, Integrate, Operate), and each phase closes with a written decision before the next one starts. Define, Design, Boundaries, Decide, and Plan are closed. Build is underway: reading a project's archive is in progress. Right now RIDGE can load its config, find a project, and read that project's marker file, with clear error messages on anything missing or malformed. It doesn't yet look inside the archive's own folders.

Weekly progress is written up by hand until RIDGE can write it itself: [redmountainindustries.com/projects/ridge](https://www.redmountainindustries.com/projects/ridge)

### Requirements

- Python 3.11+
- [LM Studio](https://lmstudio.ai/) running locally, serving a local model over its OpenAI-compatible API
- A GPU with roughly 16GB+ VRAM, enough to run a ~26B parameter model locally at a reasonable quantization

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

### License

MIT, see [LICENSE](LICENSE).
