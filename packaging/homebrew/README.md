# Homebrew Packaging

`agent-hive.rb` is generated from published PyPI artifacts.

Generate it locally after a package release with:

```bash
make brew-formula
```

The release workflow can also update a Homebrew tap automatically when
`HOMEBREW_TAP_REPO` and `HOMEBREW_TAP_GITHUB_TOKEN` are configured.
