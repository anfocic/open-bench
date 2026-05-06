# bench/scripts/_tests

Unit tests for the eval-framework code under `bench/scripts/`. Stdlib
`unittest`, no external dependencies.

From the repo root:

```
python -m unittest discover -s bench/scripts/_tests -t .
```

(`-t .` sets the top-level directory so tests can use package imports.) The suite includes a snapshot test that re-runs
`aggregate_judges.py` against checked-in judgment data and diffs the
rendered review against a golden file — refactors must keep that diff
empty.
