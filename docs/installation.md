# Installation guide

This guide covers two separate things:

1. Getting the project and its Python helper running (works the same everywhere).
2. Installing `SKILL.md` as an agent skill in a coding harness (Claude Code, OpenCode, Kilo Code, Codex CLI, Gemini CLI, or anything else).

The skill and the helper do different jobs. The skill (`SKILL.md`) tells the AI how to run an SPSS-style workflow. The helper (`scripts/analyze.py` and friends) does the actual calculations. Installing only the skill gives you the workflow but no computed numbers unless the harness can also run Python. Coding harnesses can, so install both.

Contents:

- [1. Clone and run the helper](#1-clone-and-run-the-helper)
- [2. Install the skill in a harness](#2-install-the-skill-in-a-harness)
  - [Claude Code](#claude-code)
  - [OpenCode](#opencode)
  - [Kilo Code](#kilo-code)
  - [Codex CLI](#codex-cli)
  - [Gemini CLI](#gemini-cli)
  - [Any other harness or LLM](#any-other-harness-or-llm)
- [3. Make the skill find the helper](#3-make-the-skill-find-the-helper)
- [4. Check it works](#4-check-it-works)
- [Troubleshooting](#troubleshooting)
- [Sources](#sources)

## 1. Clone and run the helper

Requirements: Git, Python 3.10 or newer, and pip.

```bash
git clone https://github.com/Kaamchor-Solutions/SPSS-Simulator-Skills.git
cd SPSS-Simulator-Skills

python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r scripts/requirements.txt

python scripts/analyze.py --config examples/describe-request.json
```

If you see JSON with descriptive statistics, the helper works. Run the tests if you want a full check:

```bash
python -m unittest discover -s tests -v
```

On some systems the command is `python3` instead of `python`.

## 2. Install the skill in a harness

Claude Code, OpenCode, Kilo Code, Codex CLI and Gemini CLI all follow the Agent Skills layout: a folder named after the skill, with `SKILL.md` inside, plus optional `scripts/` and `references/` folders. This repository already has that shape. `SKILL.md` has `name: spss-simulator`, so the folder must be named `spss-simulator` (OpenCode requires the folder name to match the `name` field).

Two rules apply everywhere:

- Keep `SKILL.md`, `scripts/` and `references/` together in one folder. `SKILL.md` points at `references/procedure-guide.md` and `scripts/analyze.py` by relative path. Copying only `SKILL.md` breaks those links.
- The folder name must be `spss-simulator`. Cloning with the default name (`SPSS-Simulator-Skills`) will not match. Clone straight into the right place, as shown below.

Pick one location per harness: personal (all your projects) or project (one repository, can be committed so a team shares it).

### Claude Code

Claude Code docs: https://code.claude.com/docs/en/skills

| Scope | Folder | Loads in |
| --- | --- | --- |
| Personal | `~/.claude/skills/spss-simulator/` | All your projects on this machine |
| Project | `.claude/skills/spss-simulator/` (inside your project) | Sessions in that repository |

Personal install:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/Kaamchor-Solutions/SPSS-Simulator-Skills.git ~/.claude/skills/spss-simulator
cd ~/.claude/skills/spss-simulator
python -m venv .venv
source .venv/bin/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r scripts/requirements.txt
```

Project install (from your project root):

```bash
mkdir -p .claude/skills
git clone https://github.com/Kaamchor-Solutions/SPSS-Simulator-Skills.git .claude/skills/spss-simulator
```

A clone inside your project is a nested Git repository. To commit the skill with your project, delete the nested `.git` folder first (or add it as a submodule).

Use it:

1. Start Claude Code with `claude` (or restart it if it was already running).
2. Type `/spss-simulator` to invoke it directly, or just describe the task ("run a t-test on score by group in data.csv") and Claude loads the skill when the description matches.
3. If the skill is not listed, restart Claude Code.

Claude Code also accepts a symlink: a `~/.claude/skills/spss-simulator` entry can point to a checkout elsewhere on disk.

### OpenCode

OpenCode docs: https://opencode.ai/docs/skills/ and https://opencode.ai/docs/rules/

OpenCode has native skill support through a `skill` tool. It searches these folders for `<name>/SKILL.md`:

| Scope | Folder |
| --- | --- |
| Project | `.opencode/skills/spss-simulator/` |
| Global | `~/.config/opencode/skills/spss-simulator/` |
| Project, Claude-compatible | `.claude/skills/spss-simulator/` |
| Global, Claude-compatible | `~/.claude/skills/spss-simulator/` |
| Project, agent-compatible | `.agents/skills/spss-simulator/` |
| Global, agent-compatible | `~/.agents/skills/spss-simulator/` |

For project paths OpenCode walks up from the current directory to the git worktree root. So if you already installed the skill for Claude Code in `~/.claude/skills/`, OpenCode finds it with no extra step.

Global install for OpenCode:

```bash
mkdir -p ~/.config/opencode/skills
git clone https://github.com/Kaamchor-Solutions/SPSS-Simulator-Skills.git ~/.config/opencode/skills/spss-simulator
cd ~/.config/opencode/skills/spss-simulator
python -m venv .venv
source .venv/bin/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r scripts/requirements.txt
```

Project install: use `.opencode/skills/spss-simulator/` in your repository instead.

Use it: OpenCode lists available skills (name and description) to the agent, and the agent loads one with the `skill` tool when the task matches. There is no documented slash command for skills, so ask in plain words, for example: "Use the spss-simulator skill to run a one-way ANOVA on data.csv."

Optional permissions in `opencode.json` (docs: skill permissions). `allow` loads immediately, `ask` prompts you first, `deny` hides it:

```json
{
  "permission": {
    "skill": {
      "spss-simulator": "allow"
    }
  }
}
```

If the skill does not appear: the `SKILL.md` frontmatter needs `name` and `description`, and `name` must match the folder name (`spss-simulator`). Both are already true in this repository.

Rules fallback (no skill loading): OpenCode reads custom instructions from `AGENTS.md` in the project root, or globally from `~/.config/opencode/AGENTS.md`. If you prefer that route, add a short note there that points at the skill file, for example:

```markdown
## Statistics
For SPSS-style statistical analysis, read and follow /path/to/SPSS-Simulator-Skills/SKILL.md.
Run calculations with /path/to/SPSS-Simulator-Skills/scripts/analyze.py. Never invent results.
```

### Kilo Code

Kilo docs: https://kilo.ai/docs/customize/skills

Kilo Code implements Agent Skills. It loads skills from:

| Scope | Folder |
| --- | --- |
| Global (Mac/Linux) | `~/.kilo/skills/spss-simulator/` |
| Global (Windows) | `C:\Users\<you>\.kilo\skills\spss-simulator\` |
| Project | `.kilo/skills/spss-simulator/` |
| Shared user-level, open standard | `~/.agents/skills/spss-simulator/` (loaded by default) |
| Project, open standard | `.agents/skills/spss-simulator/` |
| Claude Code compatibility | `~/.claude/skills/` and `.claude/skills/` (only when Claude Code Compatibility is enabled) |

Global install:

```bash
mkdir -p ~/.kilo/skills
git clone https://github.com/Kaamchor-Solutions/SPSS-Simulator-Skills.git ~/.kilo/skills/spss-simulator
cd ~/.kilo/skills/spss-simulator
python -m venv .venv
source .venv/bin/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r scripts/requirements.txt
```

You can also point Kilo at a folder of skills you keep elsewhere, in `kilo.jsonc` (project or global):

```jsonc
{
  "skills": {
    "paths": ["~/my-skills"]
  }
}
```

Use it: Kilo reads only each skill's name and description at startup, then loads the full `SKILL.md` when your request matches the description. Naming the skill in your request always works, for example: "Use the spss-simulator skill to describe the variables in survey.xlsx." Kilo also supports mode-specific skills; this one works as a generic skill available in all modes.

### Codex CLI

Codex docs: https://developers.openai.com/codex/skills

| Scope | Folder |
| --- | --- |
| Repository | `<repo>/.agents/skills/spss-simulator/` (Codex scans from the working directory up to the repo root) |
| User | `~/.agents/skills/spss-simulator/` |

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/Kaamchor-Solutions/SPSS-Simulator-Skills.git ~/.agents/skills/spss-simulator
```

Use it: run `/skills` or type `$` and pick the skill, or describe the task and let Codex match the description. Codex detects skill changes automatically; restart it if a new skill does not show up. Because `~/.agents/skills/` is also read by OpenCode, Kilo Code and Gemini CLI, one clone there covers several tools.

### Gemini CLI

Gemini CLI docs: https://geminicli.com/docs/cli/skills/

| Scope | Folder |
| --- | --- |
| User | `~/.gemini/skills/spss-simulator/` or `~/.agents/skills/spss-simulator/` |
| Workspace | `.gemini/skills/spss-simulator/` or `.agents/skills/spss-simulator/` |

Use it: inside a session, `/skills list` shows discovered skills and `/skills reload` refreshes the list. When your task matches, Gemini asks for confirmation to activate the skill and gives it access to the skill folder, so approve it to let it read `scripts/` and `references/`.

### Any other harness or LLM

Not every tool has a skill system. Work out which case you are in.

**The harness supports Agent Skills (a folder with `SKILL.md`).** Many do, and `~/.agents/skills/` is a common shared location. Check the harness docs for its skills folder and install the whole folder as `spss-simulator`, as above.

**The harness has no skill system but has custom instructions** (a rules file, `AGENTS.md`, `CLAUDE.md`, project instructions, or a system prompt box). Use this fallback:

1. Clone the repository anywhere and set up the helper (section 1).
2. Add this to the harness instructions, with real paths filled in:

   ```text
   For SPSS-style statistical analysis, follow the workflow in <path>/SKILL.md.
   Read <path>/references/procedure-guide.md for procedures and request formats.
   Compute results only by running <path>/.venv/bin/python <path>/scripts/analyze.py
   (or spss_report.py). Never invent or estimate numbers.
   ```

3. Or paste the contents of `SKILL.md` into the instructions box and also provide `references/procedure-guide.md`, because linked files are not loaded automatically in that case.

**A chat-only LLM with no code execution and no file access.** It can follow the workflow, plan the analysis, write code or SPSS syntax for you to run, and interpret numbers you paste in. It cannot compute results. Run the helper yourself and paste the output back.

What matters in the repository, if you are wiring it by hand:

| Path | Purpose |
| --- | --- |
| `SKILL.md` | The instructions. Required. |
| `references/procedure-guide.md`, `references/portable-runtime.md` | Procedure details and helper interface. Needed for full behavior. |
| `scripts/analyze.py`, `scripts/spss_format.py`, `scripts/spss_plots.py`, `scripts/spss_report.py`, `scripts/requirements.txt` | The Python helper that does the calculations. Keep them together. |
| `examples/` | Sample data and runnable request files. |
| `templates/` | Report templates. |

## 3. Make the skill find the helper

`SKILL.md` refers to `scripts/analyze.py` relative to the skill folder, but your agent usually runs commands from your own project folder. If the agent cannot find the script, tell it the absolute path once, for example:

> The helper lives at `~/.claude/skills/spss-simulator/scripts/analyze.py`. Run it with `~/.claude/skills/spss-simulator/.venv/bin/python`.

On Windows the venv interpreter is `.venv\Scripts\python.exe`. Request files can use absolute paths to your data (`"file": "/home/me/data/survey.csv"`); relative paths are resolved from the directory where the command runs.

If the agent runs in a sandbox that cannot reach your home folder, install the helper requirements in whatever Python environment the sandbox uses.

## 4. Check it works

Start a new session in the harness and try:

> Use the spss-simulator skill. Run a descriptive analysis of score and age in `examples/demo.csv` and show the SPSS-style table.

You should see the agent load the skill, run `analyze.py`, and return a "Descriptive Statistics" table with real numbers. If it answers without running anything, ask it to run the helper and show the command it used. Results that did not come from a real run should not be trusted.

## Troubleshooting

| Problem | Likely cause and fix |
| --- | --- |
| Skill does not appear | Folder name is not `spss-simulator`, or `SKILL.md` is not directly inside it (a double folder such as `spss-simulator/SPSS-Simulator-Skills/SKILL.md` will not work). Restart the harness. |
| Agent says it cannot read `references/` or `scripts/` | Only `SKILL.md` was copied. Install the whole folder. |
| `ModuleNotFoundError` when running the helper | The requirements are not installed in the Python the agent uses. Run the pip install from section 1 with that Python. |
| `python: command not found` | Use `python3`, or give the agent the full path to the venv Python. |
| `.sav` files fail to load | `pyreadstat` is missing. It is part of `scripts/requirements.txt`. |
| Old `.xls` files fail to load | Convert to `.xlsx`, or install `xlrd`. |
| Agent gives numbers without running code | The skill alone cannot compute. Make sure the harness can execute Python and that the helper is installed. |

## Sources

Harness behavior above comes from each project's own documentation, checked on 8 October 2026. Harnesses change quickly, so confirm against these pages if something differs:

- Claude Code skills: https://code.claude.com/docs/en/skills
- OpenCode skills: https://opencode.ai/docs/skills/
- OpenCode rules (`AGENTS.md`): https://opencode.ai/docs/rules/
- Kilo Code skills: https://kilo.ai/docs/customize/skills
- Codex skills: https://developers.openai.com/codex/skills
- Gemini CLI skills: https://geminicli.com/docs/cli/skills/
