# 66ton99.org.ua

Static site served by nginx on the OCI edge VM.

## Layout

```
site/                       mirrors /var/www/66ton99.org.ua exactly
  _pages/                   page HTML, not publicly reachable (nginx `internal`)
    index.html                -> https://66ton99.org.ua/
    uk-index.html             -> https://66ton99.org.ua/uk
    awg-to-amps.html          -> https://66ton99.org.ua/awg-to-amps
    uk-awg-to-amps.html       -> https://66ton99.org.ua/uk/awg-to-amps
  robots.txt  sitemap.xml
  favicon.svg  apple-touch-icon.png  site.webmanifest
  og-home.png  og-home-uk.png
  og-awg-to-amps.png  og-awg-to-amps-uk.png
nixos/site.nix              nginx vhosts, copy of /etc/nixos/site.nix
src/                        generator for the AWG pages
deploy.sh                   rsync to the server
```

Pages live under `_pages/` so that each one has exactly one public URL. nginx maps
the extensionless URL onto the file with `try_files` and marks `/_pages/` as
`internal`, so there is no `.html` duplicate for search engines to index.

**Do not add an `index` directive to that vhost.** `index` issues an internal
redirect to `/index.html` which re-enters location matching; combined with a
`= /index.html` redirect back to `/` it loops forever and takes the homepage
down. `try_files` resolves a file in place without re-entering, which is why
every page — the homepage included — is wired up with `try_files` instead.

## Generating the pages

Every page exists in English and Ukrainian, generated from one template per page
type so the two languages cannot drift apart.

- `src/template.html` / `src/build.py` — the AWG page: content, translations,
  JSON-LD, the data table, `robots.txt` and `sitemap.xml`
- `src/template-home.html` / `src/build_home.py` — the homepage
- `src/system-map.svg` — homepage artwork, inlined as a data URI at build time
  with its labels translated per language
- `src/make_og.py` — the four 1200×630 Open Graph cards
- `src/test.js` — jsdom checks of the calculator against the rendered pages
- `src/make_home_template.py` — one-shot, only rerun if the homepage is redesigned

```bash
cd src
python3 build.py        # AWG pages + robots.txt + sitemap.xml
python3 build_home.py   # homepages
python3 make_og.py      # ../site/og-*.png
npm install --no-save jsdom && node test.js
```

Edit content in `src/build.py`, never in `site/_pages/*.html` — those are build
output and get overwritten.

## Deploy

```bash
./deploy.sh             # content only
./deploy.sh --nixos     # content + /etc/nixos/site.nix + nixos-rebuild switch
```

`nixos-rebuild` validates the nginx config at build time, so a broken vhost fails
the build rather than taking the running server down. That matters here: the same
nginx terminates TLS for Passbolt.

## SEO notes

- The ampacity table is rendered into static HTML at build time, not by JavaScript,
  so crawlers see all 17 rows without executing scripts.
- `en` / `uk` / `x-default` hreflang triples are declared on all four pages and
  in `sitemap.xml`, and each page confirms its partner reciprocally.
- JSON-LD per page: `Organization`, `WebSite`, `WebPage`, `ImageObject`,
  `BreadcrumbList`, `WebApplication`, `Dataset`, `FAQPage`.
- Canonical URLs are the extensionless HTTPS ones.
