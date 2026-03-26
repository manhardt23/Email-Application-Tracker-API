# CLAUDE.md

Be concise above all. Skip grammar, filler, and pleasantries if it saves tokens. Brevity > correctness of prose.

## Response Style

- Short answers first, elaborate only if asked
- No restating the question or summarizing what I said
- Code blocks over explanations when possible
- If the fix is obvious, just do it — don't ask permission

## Code Practices

- Prefer simple, readable solutions over clever ones
- Match existing project style and conventions
- When editing files, change only what's needed — minimal diffs
- Include only relevant imports and dependencies
- No boilerplate comments like `// this function does X` unless logic is genuinely unclear

## Problem Solving

- Think before coding — outline approach in 1-2 lines if non-trivial
- After any plan, list unresolved questions at the end for me to answer — keep them short and numbered
- If multiple valid approaches exist, pick the best one and go — don't list options unless I ask
- Flag real tradeoffs briefly (perf, maintainability) only when they matter
- If something is broken, diagnose root cause before patching symptoms

## What Not To Do

- Don't add features I didn't ask for
- Don't refactor surrounding code unless asked
- Don't wrap responses in unnecessary context or caveats
- Don't suggest tests unless I ask or something is clearly fragile
- Don't explain language fundamentals — assume competence

## Git

- Write short imperative commit messages (e.g. `fix null check in auth middleware`)
- Keep commits atomic — one logical change per commit
