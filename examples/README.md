# test-gap — examples

Each scenario shows: a diff + coverage report fixture, the exact command, and the helper's report.

---

## Scenario 1 — Cobertura report with partial coverage

**Setup:** You've changed lines 11–15 of `src/auth/refresh.py`. Your test suite was run with `pytest --cov --cov-report=xml`, producing `coverage.xml`. Lines 12–14 are uncovered.

**Fixtures:**

- [`sample-coverage.xml`](./sample-coverage.xml) — synthetic Cobertura report
- [`sample.diff`](./sample.diff) — synthetic unified diff

**Command:**

```sh
python3 scripts/gap.py --report examples/sample-coverage.xml --format md
```

(In a real repo, you'd skip `--report` and let auto-detection find `coverage.xml`.)

**Helper output:**

```
| File | Changed | Uncovered | Coverage |
| --- | ---: | ---: | ---: |
| src/auth/refresh.py | 5 | 12,13,14 | 72.00% |
```

Three of the five changed lines are uncovered — the gap.

---

## Scenario 2 — no coverage report present (the "false-green" guard)

The single most important guarantee of `test-gap`: if there's no coverage data, you do NOT get a green "100% covered" result by accident.

```sh
python3 scripts/gap.py --report does-not-exist.xml
# stderr: error: coverage report not found at does-not-exist.xml
# exit:   2
```

And when no report is present at all (no `coverage.xml`, `lcov.info`, or `coverage.json` in the cwd):

```sh
python3 scripts/gap.py
# stderr: warning: no coverage report detected (looked for coverage.xml, lcov.info,
#   coverage.json) — treating every changed line as a gap.
# exit:   1
```

The report renders every changed line as uncovered with `Coverage: unknown`. That's the safe failure mode.

---

## Scenario 3 — lcov.info (JavaScript / Istanbul / c8)

```sh
python3 scripts/gap.py --report build/lcov.info --base develop --format md
```

Works identically; the parser auto-detects from the file extension.

---

## Workflow tip

Wire `test-gap` into your local `pre-push` hook to catch coverage regressions before they leave your machine:

```sh
#!/bin/sh
# .git/hooks/pre-push
python3 -m pytest --cov --cov-report=xml -q || exit 1
python3 ~/.claude/plugins/test-gap/scripts/gap.py --format md
```
