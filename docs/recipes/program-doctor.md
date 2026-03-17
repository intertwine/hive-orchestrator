# Program Doctor

`PROGRAM.md` is the contract that decides whether Hive can promote a run on its own.

## Start with one real evaluator

The safest default is one evaluator that proves the main slice is healthy.

Examples:

- Python library: `pytest -q`
- Frontend app: `npm test -- --run`
- API service: `pytest tests/api -q`
- Docs-only project: a link checker or docs build

## Make promotion rules obvious

- Keep `promotion.requires_all` aligned with the evaluator IDs you actually trust.
- Turn on unsafe promotion only when you mean it.
- Turn on no-change acceptance only for report-only or review-only flows.

## Path rules that help in practice

- Use `paths.allow` to keep runs inside the slice they were meant to change.
- Use `paths.deny` for production infra, secrets, or anything that should always trigger a human check.
- Use `promotion.review_required_when_paths_match` for areas where code can land only after review.

## A good first pass

You do not need a perfect contract on day one. You need one that is explicit, testable, and hard to misunderstand in a pull request.
