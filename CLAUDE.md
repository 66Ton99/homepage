@../homepage-infra/AGENTS.md

<!-- The import above is the shared source of truth for this repo and the
     private homepage-infra one. Keep repo-specific notes below it, and put
     anything that applies to both in that file instead. -->

## homepage

Public repo: site content, the generators in `src/`, and the built `site/` tree.

If the import above did not load — no `homepage-infra` checkout beside this one,
or the external-import prompt was declined — these are the rules that matter
most here:

- Enter the toolchain first: `nix develop` (PHP 8.5 + Node 24, pinned in `flake.nix`).
- Never edit `site/_pages/*.html`; they are build output. Edit `src/build.php`
  or `src/build_home.php`, then rebuild.
- Verify with `php src/build.php && php src/build_home.php`, check
  `git status --porcelain -- site` shows only intended changes, and run
  `cd src && npm test`. CI fails if committed `site/` differs from a rebuild.
- `src/make_og.php` is not in CI. Do not regenerate the committed PNGs unless
  the cards are actually being redesigned.
