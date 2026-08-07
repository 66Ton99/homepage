# 66ton99.org.ua

Static site served by nginx on the OCI edge VM `nixos-micro`, which also terminates
TLS for `pass.66ton99.org.ua`.

## Layout

```
site/                       mirrors /var/www/66ton99.org.ua exactly
  index.html                homepage
  _pages/                   page HTML, not publicly reachable (nginx `internal`)
    awg-to-amps.html          -> https://66ton99.org.ua/awg-to-amps
    uk-awg-to-amps.html       -> https://66ton99.org.ua/uk/awg-to-amps
  robots.txt  sitemap.xml
  favicon.svg  apple-touch-icon.png  site.webmanifest
  og-awg-to-amps.png  og-awg-to-amps-uk.png
nixos/site.nix              nginx vhosts, copy of /etc/nixos/site.nix
src/                        generator for the AWG pages
deploy.sh                   rsync to the server
```

Pages live under `_pages/` so that each one has exactly one public URL. nginx maps
the extensionless URL onto the file with `try_files` and marks `/_pages/` as
`internal`, so there is no `.html` duplicate for search engines to index.

## AWG to amps page

`src/` generates the English and Ukrainian versions from one template, so the
markup, the data table and the calculator logic cannot drift apart.

- `src/template.html` — page shell with `{{TOKEN}}` placeholders
- `src/build.py` — content, translations, JSON-LD, table, `robots.txt`, `sitemap.xml`
- `src/make_og.py` — the two 1200×630 Open Graph cards
- `src/test.js` — jsdom checks of the calculator against the rendered pages

```bash
cd src
python3 build.py        # writes ../site/_pages/*.html, robots.txt, sitemap.xml
python3 make_og.py      # writes ../site/og-*.png
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
- `en` / `uk` / `x-default` hreflang triples are declared in both pages and in
  `sitemap.xml`.
- JSON-LD per page: `Organization`, `WebSite`, `WebPage`, `ImageObject`,
  `BreadcrumbList`, `WebApplication`, `Dataset`, `FAQPage`.
- Canonical URLs are the extensionless HTTPS ones.
