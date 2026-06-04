# Contributing

Thanks for your interest in improving the Createrington Skin API Python client.
Issues and pull requests are welcome.

## Licensing of contributions

By submitting a pull request you agree that your contribution is licensed under
the project's [Apache-2.0](LICENSE) terms (per section 5 of the license). There
is no separate CLA to sign.

## Prerequisites

- Python 3.10 or newer.

```sh
pip install -e ".[dev]"
pytest
mypy
```

`mypy` runs in strict mode, so a clean local typecheck and a green test run are
the bar a PR has to clear.

## Project layout

- `src/createrington_skin_api/` is the published library.
- `tests/` holds the pytest suite (it runs against a stubbed httpx transport, so
  it needs no network or API key).
- `scripts/generate_poses.py` regenerates `_poses.py`.

`src/createrington_skin_api/_poses.py` is **generated, not hand-edited**. It is
produced from the published OpenAPI document. If you need to refresh it:

```sh
python scripts/generate_poses.py
```

Note that `render` accepts any pose string, so a new server-side pose works
without changing the SDK; `Poses` and `KNOWN_POSES` only provide names known at
build time.

## Branching and pull requests

- Branch off `dev`, and open your PR against `dev`. `main` is the released
  branch; merges to it publish to PyPI.
- Use short, descriptive branch names like `feat/retry-jitter`,
  `fix/timeout-mapping`, `chore/bump-httpx`.
- Keep a PR focused on one change, and make sure `mypy` and the tests pass.

## Commit messages

Use Conventional Commit style:

```
type(scope): description
```

- Types: `feat`, `fix`, `chore`, `refactor`, `docs`, `style`, `test`, `perf`.
- Scope is optional.
- Description is lowercase, imperative, and has no trailing period.

Examples:

```
feat: add cancellation support to render
fix: map 503 to upstream_unavailable
docs: document the async client
```

## Code style

- Public types and methods carry docstrings.
- Default to no comments; add one only when the reasoning is not obvious from the
  code itself.
- Avoid em dashes in code, comments, and docs; use commas, parentheses, colons,
  or hyphens.

## Reporting issues

Open an issue with a clear description and, where relevant, a minimal repro (the
pose, the skin source, the client options, and the observed vs expected result).
