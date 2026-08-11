# shaxelib

Minimal template for publishing a Haxe library to haxelib through GitHub Releases.

## What is included

- `src/` for library source code
- `tests/` for lightweight test entry points
- `cli/Main.hx` as the CLI entry point
- `build_cli.hxml` to compile the CLI to Neko
- `build_tests.hxml` for local test execution
- optional `haxelib.json` for package metadata overrides
- `.github/scripts/generate_haxelib_json.py` to build `package/haxelib.json`
- `.github/workflows/publish-haxelib.yml` to publish on release

## Intended workflow

1. Add your library code under `src/`.
2. Optionally create `haxelib.json` if you want to override generated metadata such as `name`, `classPath`, `contributors`, or `dependencies`.
3. Update tests in `tests/` so they compile against the real library.
4. Create a GitHub Release with a semantic version tag such as `v0.1.0`.
5. The workflow generates `package/haxelib.json` and submits the package to haxelib.

## Required setup

Optional `haxelib.json` overrides:

- `name`
- `classPath`
- `contributors`
- `description` if the GitHub repository description is empty
- `license` if automatic SPDX to haxelib mapping is not enough
- `dependencies` when your library requires other haxelib packages

Set GitHub Actions secrets:

- `HAXELIB_PASSWORD` required
- `HAXELIB_USER` optional for explicit username-based submit

## Local usage

Run tests:

```bash
haxe build_tests.hxml
```

Run the CLI entry point locally:

```bash
haxe build_cli.hxml
neko run.n
```

## Current placeholders to replace

- `src/Library.hx` and `tests/Main.hx` are starter stubs

## Project layout

### `src/`

This directory contains the public library source that will be shipped to haxelib.

- Put reusable library code here.
- Keep package names aligned with the library name you plan to publish.
- Only files copied into `package/src` are included in the published package.
- The runnable CLI entry point lives separately in `cli/Main.hx`.

`src/Library.hx` is only a stub. Replace it with your real modules or remove it if you do not need a root source module under `src/`.

### `cli/`

This directory contains the CLI entry point and generated Neko binary.

- `cli/Main.hx` is compiled by `build_cli.hxml`.
- `run.n` is generated in the package root during local builds and during release packaging.
- Keep command-line bootstrap logic here instead of mixing it into the library source tree.

### `tests/`

This directory contains compile-time or runtime tests for the library.

- `build_tests.hxml` adds `tests/` to the class path.
- `Main` is the default test entry point.

Suggested usage:

- smoke tests that compile the public API
- regression tests for fixed bugs
- small interpreter-based checks with `--interp`

`tests/Main.hx` is intentionally empty and should be replaced with real assertions or compile checks.

## Publish behavior

The release workflow:

1. Checks out the published Git tag
2. Installs Haxe and Python dependencies
3. Copies the configured `classPath`, `cli/`, `build_cli.hxml`, `README.md`, `LICENSE`, and optional `CHANGELOG.md` into `package/`
4. Compiles `run.n` in the package root
5. Generates `package/haxelib.json` from `haxelib.json`, repository metadata, and the release body
6. Publishes `package/` with `haxelib submit`

## Notes

- `releasenote` comes from the release body; if it is empty, the workflow uses the release title, and if that is also empty, it uses `New release`.
- Repository topics are used as package tags when `tags` are not set in `haxelib.json`.
- The generated package version comes from the Git tag unless `version` is set manually.
- If `haxelib.json` is missing or does not define `classPath`, the workflow uses `src`.
- `contributors` can be omitted from `haxelib.json`; the release script falls back to GitHub contributors.
