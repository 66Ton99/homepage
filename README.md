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
src/                        generator for the pages
deploy.sh                   rsync to the server
```

Pages live under `_pages/` so that each one has exactly one public URL. nginx maps
the extensionless URL onto the file with `try_files` and marks `/_pages/` as
`internal`, so there is no `.html` duplicate for search engines to index.

**If you maintain that config: do not add an `index` directive to the vhost.** `index` issues an internal
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
- `src/test.js` — jsdom checks of the calculator against the rendered pages,
  including the DC / AC 1-phase / AC 3-phase behaviour
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
./deploy.sh
```

`site/` mirrors the web root exactly, so this is a plain `rsync --delete`:
whatever is committed here is what gets served.

The nginx/NixOS configuration is **not** in this repo — it names internal
addresses, so it lives in a separate private one. The notes below describe how
it is wired, which is what you need to understand the URLs.

## Contributing

Corrections to the ampacity data are welcome, especially with a datasheet or
standard to back them. The AWG 24–30 rows are the least certain: they are
indicative for fine-stranded silicone wire rather than taken from one
authoritative table.

Edit `src/build.py`, never `site/_pages/*.html` — those are build output. Run
`python3 build.py && node test.js` before opening a pull request.

## The DC / AC toggle

The toggle above the table is deliberately honest about what it does and does
not change.

Every data cell in the table is recomputed when the mode changes, but not every
column moves by the same amount, and that is deliberate.

**The ampacity columns move for three-phase**, and this is the large effect. A
three-phase circuit puts three current-carrying conductors in the cable where DC
and single-phase put two; three conductors dissipating I²R make half again as
much heat in the same bundle. IEC 60364-5-52 publishes this as separate
"2 loaded conductors" and "3 loaded conductors" columns, and across its copper
tables the ratio averages **0.915** — the factor applied to the in-cable columns
here. 0 AWG reads 112 A on DC and single-phase, 102 A on three-phase. The
free-air columns describe one isolated conductor, the same object in every mode,
so they do not move.

**Frequency is the small effect, and it is the whole of DC vs single-phase.**
Both have two loaded conductors, so no conductor-count derate applies, and
unarmoured low-voltage wire has neither sheath nor dielectric losses. That
leaves skin and proximity, computed per IEC 60287-1-1: 0.30 % at 50 Hz on
0 AWG, 0.05 % at 4 AWG, nothing measurable below. Ampacity is printed to one
decimal so that difference is visible where it exists (112.0 A → 111.8 A) rather
than being rounded away — the earlier integer display made the toggle look inert
between those two modes. Raise the frequency and it stops being subtle: 0 AWG
loses 8 % by 400 Hz.

**The maximum-load column is the honest answer to "the current is different on
AC".** Amperes are amperes — copper does not care where the heat came from — but
what those amperes are worth changes completely. The same 0 AWG conductor at
112 A delivers 2.7 kW on 24 V DC, 26 kW on 230 V single-phase and 78 kW on 400 V
three-phase. Read backwards: for a given load the current you must carry differs
by a factor of twenty-nine between those systems, and the copper follows the
current, not the watts.

**The resistance and maximum-run columns move a lot.** Resistance switches
between DC and the AC value at the chosen frequency. Maximum run is the longest
one-way length holding the drop within 3 % at the row's rated current, using the
mode's own drop formula — which is where DC and three-phase genuinely diverge:

| 0 AWG | in-cable 60 °C | voltage | max run @3 % | max load |
|---|---|---|---|---|
| DC | 112 A | 24 V | 9.8 m | 2.7 kW |
| AC 1-phase | 112 A | 120 / 230 V | 49 / 94 m | 13 / 26 kW |
| AC 3-phase | 102 A | 208 / 400 V | 107 / 207 m | 37 / 71 kW |

The three-phase run comes out *longer* despite the √3, because the current it
has to hold is lower.

The system voltage follows the mode unless the reader has typed their own, which
is never overwritten. Defaults are regional, set per language in `build.py`:

| | DC | 1-phase | 3-phase | frequency |
|---|---|---|---|---|
| English | 24 V | 120 V | 208 V | 60 Hz |
| Ukrainian | 24 V | 230 V | 400 V | 50 Hz |

Both are the standards-current nominals rather than the colloquial older ones —
120 V per ANSI C84.1 rather than "110", and 230/400 V per IEC 60038 rather than
"220/380". Each pair is internally consistent, since the three-phase figure is
√3 times the single-phase one. The prose in each language quotes numbers worked
out at its own defaults, and the tests carry a regional expectation set for the
same reason.

**Voltage drop in the calculator:**

| | drop | I²R conductors |
|---|---|---|
| DC | `2·I·R·L` | 2 |
| AC 1-phase | `2·I·R·L·cos φ` | 2 |
| AC 3-phase | `√3·I·R·L·cos φ` | 3 |

The AC modes also expose a frequency input, because skin effect does matter
higher up: 0 AWG picks up 4.7 % at 400 Hz. The IEC fit holds for xs ≤ 2.8
(~1 kHz on the largest gauge), and above that the calculator flags its own
output as indicative rather than silently extrapolating.

Reactance is neglected throughout — at these cross-sections and run lengths it
is below the uncertainty in the resistance, but that assumption breaks on long
three-phase runs in conduit.

## Shareable links

Mode and every calculator input are reflected in the query string, so a
configuration can be sent to someone else. There is a copy-link button next to
Calculate.

```
/awg-to-amps?mode=ac3&n=4208&u=400&a=50&f=400
```

Rules that keep this from turning into an SEO problem or a mess:

- **Only non-defaults are written.** A page in its default state has a clean URL,
  and Reset returns it to one. `mode` disappears on DC; frequency and power
  factor are omitted outside the AC modes.
- **The canonical link is static and ignores the query string**, so parameter
  variants consolidate onto the clean URL rather than being indexed separately.
  There is a test asserting this for both languages.
- **Query string, not hash**, because the hash already carries the in-page
  anchors (`#chart`, `#faq`, …).
- **`replaceState`, debounced 350 ms.** Browsers rate-limit history writes —
  Safari throws above 100 in 30 seconds — and typing in a field would otherwise
  trip it. No history entries are created, so Back still leaves the page.
- Arriving with optional parameters opens the optional section, so the values in
  the link are visible rather than hidden behind a collapsed `<details>`.

`localStorage` still holds the mode as a fallback for visitors arriving without
parameters; an explicit URL always wins over it.

## SEO notes

- The ampacity table is rendered into static HTML at build time, not by JavaScript,
  so crawlers see all 17 rows without executing scripts.
- `en` / `uk` / `x-default` hreflang triples are declared on all four pages and
  in `sitemap.xml`, and each page confirms its partner reciprocally.
- JSON-LD per page: `Organization`, `WebSite`, `WebPage`, `ImageObject`,
  `BreadcrumbList`, `WebApplication`, `Dataset`, `FAQPage`.
- Canonical URLs are the extensionless HTTPS ones.
