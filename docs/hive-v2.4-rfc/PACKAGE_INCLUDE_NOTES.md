# Package and PR Wiring Notes

I could not open a live GitHub PR from this environment because there is no writable repository checkout or GitHub credential path here.

This bundle is laid out so it can be copied directly into the repo root.

## Files to add

- `docs/V2_4_STATUS.md`
- `docs/hive-v2.4-rfc/README.md`
- `docs/hive-v2.4-rfc/HIVE_V2_4_RFC.md`
- `docs/hive-v2.4-rfc/HIVE_V2_4_ADAPTER_MODEL_AND_LINK_SPEC.md`
- `docs/hive-v2.4-rfc/HIVE_V2_4_HARNESS_PACKAGES_AND_ONBOARDING.md`
- `docs/hive-v2.4-rfc/HIVE_V2_4_IMPLEMENTATION_PLAN.md`
- `docs/hive-v2.4-rfc/HIVE_V2_4_ACCEPTANCE_TESTS.md`
- `docs/hive-v2.4-rfc/SOURCES.md`

## `pyproject.toml` updates

Follow the same pattern already used for `docs/hive-v2.2-rfc` and `docs/hive-v2.3-rfc`.

### Wheel `force-include`
Add:

```toml
"docs/V2_4_STATUS.md" = "src/hive/resources/docs/V2_4_STATUS.md"
"docs/hive-v2.4-rfc" = "src/hive/resources/docs/hive-v2.4-rfc"
```

### `sdist` `only-include`
Add:

```toml
"docs/V2_4_STATUS.md",
"docs/hive-v2.4-rfc",
```

## Optional follow-up docs links

After the files are added, consider linking them from:

- `docs/MAINTAINING.md`
- `docs/RELEASING.md`
- `docs/START_HERE.md` only if you want the v2.4 line visible to non-maintainers
