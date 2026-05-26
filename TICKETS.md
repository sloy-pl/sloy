# Writing Tickets

Turn a request into a GitHub issue that's **grounded in this repo** — name the
real files and patterns the implementer will touch, not generic advice.

## Workflow

1. **Explore first.** Most changes here mirror an existing pattern: adding a page
   is a new entry in `tests/pages.ts`; silencing a dynamic region is a `mask`
   selector on that entry; a capture/stability tweak lives in `tests/helpers.ts`.
   Find the analog before writing.
2. **Anchor in real code.** Reference concrete files — `tests/pages.ts`,
   `tests/helpers.ts`, `tests/visual.spec.ts`, `playwright.config.ts`, the
   workflows in `.github/workflows/` — and the gotchas in [CLAUDE.md](./CLAUDE.md).
3. **Reuse over invention.** Extend the existing `PageDef`, `mask` array, or
   `preparePage()` helper rather than adding new machinery, unless there's a
   reason not to.
4. **Surface decisions as open questions** with a recommendation — don't silently
   pick (e.g. mask a region vs. raise tolerance; one page per template vs. every
   URL; add a viewport vs. keep two).
5. **Create with `gh`** via `--body-file` so checkboxes survive:

   ```bash
   cat > /tmp/ticket.md <<'EOF'
   ...body...
   EOF
   gh issue create --title "…" --body-file /tmp/ticket.md && rm -f /tmp/ticket.md
   ```

   - Title: imperative and scoped (e.g. "Add lookbook page to the capture set").
   - Labels: check `gh label list` first; leave unlabeled rather than forcing a
     wrong label, and offer to add one.

## Ticket structure (drop what doesn't apply)

- **Summary** — what and why in 2–4 sentences, naming the pattern it mirrors.
- **Motivation** — the reason it's worth doing.
- **Proposed change** — by layer:
  - Pages / coverage — `tests/pages.ts` entries, paths, viewports.
  - Capture / stability — `tests/helpers.ts`, `mask` selectors, tolerances.
  - Config / CI — `playwright.config.ts`, the workflows, baseline handling.
- **Open questions** — real forks with a recommendation.
- **Acceptance criteria** — a `- [ ]` checklist, including: baselines regenerated
  on CI, `npm test` green, report published.

## Principles

- Specific beats exhaustive — naming the right two or three files beats a long
  list of generic advice.
- Write for someone who knows Playwright but not this repo's history.
- Don't restate what CLAUDE.md already owns — link to it.
