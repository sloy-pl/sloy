# Commit & PR Guide

## Attribution

- Do **not** add `Co-Authored-By: Claude …` trailers or "🤖 Generated with
  Claude Code" lines. Commits are authored by the human running the session; no
  tool/agent attribution belongs in the permanent history.

## Commit messages

- Subject: imperative, ~50 chars, no trailing period.
  - Good: `Mask search grid to stop thumbnail false positives`
  - Bad: `Fixed search.` / `Fix #12`
- Body (when needed): wrap ~72 chars, explain **why** the change exists and what
  behaviour shifts. Don't restate the diff.
- Reference issues with `Refs #NNN` / `Closes #NNN` on their own line at the
  bottom of the body. No other trailers.

## Referencing & closing issues

- **`Closes #NNN`** when the commit fully resolves the issue — GitHub auto-closes
  it on merge to `main`.
- **`Refs #NNN`** for partial or related work that doesn't finish it.
- Find numbers with `gh issue list` / `gh issue view`; never guess. Omit the
  trailer if no existing issue matches.

## PR descriptions

- **Summary** — 1–2 sentences / bullets on what changed from the user's view.
  Put `Closes #NNN` here so GitHub links and closes it.
- **Notes** — trade-offs, deferred work, follow-ups for the reviewer.
- **Test plan** — a checklist of checks run (`npm test`, the published report).
- No emoji footer, no tool attribution.

## Visual changes

This repo's whole job is screenshots, so prove rendering changes with the
report, not prose. When a change touches what's captured or compared (config,
`tests/helpers.ts`, the page list, masks):

- Run the **Visual regression report** workflow (or `npm test` locally) and link
  the published report — <https://sloy-pl.github.io/sloy/> — in the PR.
- Cover both viewports: `desktop` and `mobile`.
- If baselines change intentionally, regenerate them via the **Update baselines**
  workflow (Linux rendering, matches CI) and say so — never commit
  macOS-rendered baselines.

## Keep doing

- Use `HEREDOC` for multi-line commit messages and PR bodies so formatting
  survives the shell.
- Stage files explicitly (`git add path/…`); avoid `git add -A` / `git add .`.
- Don't commit `test-results/` or `playwright-report/` (both git-ignored); only
  the baselines under `tests/__screenshots__/` belong in history.
- Never `--amend` a pushed commit or push to `main` without an explicit ask.
