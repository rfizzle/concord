# Vendored dependencies

Third-party code committed verbatim so the site generator stays zero-install —
`gen-changelog.cjs` runs on plain `node` from CI (`build-site.yml`) and from each
member's `make site`, none of which run `npm install`.

## markdown-it.min.js

- **What:** [markdown-it](https://github.com/markdown-it/markdown-it) — the
  CommonMark parser `scripts/gen-changelog.cjs` uses to turn changelog Markdown
  into the template's block schema. Zero runtime dependencies; the UMD build is a
  single self-contained file.
- **Version:** 14.1.0
- **Source:** `https://cdn.jsdelivr.net/npm/markdown-it@14.1.0/dist/markdown-it.min.js`
- **SHA-256:** `38c70a1e7ca91ab40e2d9e6e60129851a717ed1c7d4acbbdd41bf9503791cf68`
- **License:** MIT

### Updating

```sh
ver=14.1.0
curl -fsSL "https://cdn.jsdelivr.net/npm/markdown-it@${ver}/dist/markdown-it.min.js" \
  -o template/vendor/markdown-it.min.js
sha256sum template/vendor/markdown-it.min.js   # record the digest above
```
