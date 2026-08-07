#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot: turn the hand-written site/index.html into src/template-home.html.

Kept in the repo so the transformation is auditable, but it only needs to run
again if the homepage design is rewritten from scratch.
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
src = (HERE.parent / "site" / "index.html").read_text(encoding="utf-8")
out = HERE / "template-home.html"

if out.exists() and "--force" not in sys.argv:
    sys.exit(f"{out.name} already exists; pass --force to regenerate")


def sub(pattern, repl, count=1, flags=0):
    global src
    src, n = re.subn(pattern, repl, src, count=count, flags=flags)
    if n != count:
        sys.exit(f"expected {count} replacement(s), made {n}: {pattern[:70]}")


# ---- head ----------------------------------------------------------------
sub(r'<html lang="en">', '<html lang="{{LANG}}">')
sub(r'(?s)<meta\s+name="description"\s+content="[^"]*"\s*/>',
    '<meta name="description" content="{{DESC}}" />')
sub(r"<title>[^<]*</title>", "<title>{{TITLE}}</title>")
sub(r'<link rel="canonical" href="[^"]*" />',
    '<link rel="canonical" href="{{CANONICAL}}" />\n'
    '    <link rel="alternate" hreflang="en" href="https://66ton99.org.ua/" />\n'
    '    <link rel="alternate" hreflang="uk" href="https://66ton99.org.ua/uk" />\n'
    '    <link rel="alternate" hreflang="x-default" href="https://66ton99.org.ua/" />')
sub(r'<meta property="og:title" content="[^"]*" />',
    '<meta property="og:title" content="{{TITLE}}" />')
sub(r'<meta property="og:description" content="[^"]*" />',
    '<meta property="og:description" content="{{DESC}}" />')
sub(r'<meta property="og:url" content="[^"]*" />',
    '<meta property="og:url" content="{{CANONICAL}}" />')
sub(r'<meta property="og:locale" content="[^"]*" />',
    '<meta property="og:locale" content="{{OG_LOCALE}}" />\n'
    '    <meta property="og:locale:alternate" content="{{OG_LOCALE_ALT}}" />\n'
    '    <meta property="og:image" content="{{OG_IMAGE}}" />\n'
    '    <meta property="og:image:width" content="1200" />\n'
    '    <meta property="og:image:height" content="630" />\n'
    '    <meta property="og:image:type" content="image/png" />\n'
    '    <meta property="og:image:alt" content="{{OG_IMAGE_ALT}}" />\n'
    '    <meta name="twitter:card" content="summary_large_image" />\n'
    '    <meta name="twitter:title" content="{{TITLE}}" />\n'
    '    <meta name="twitter:description" content="{{DESC}}" />\n'
    '    <meta name="twitter:image" content="{{OG_IMAGE}}" />')

# ---- css: h1 brand must look exactly like the old span, plus lang switch ---
sub(r"      \.brand \{\n        display: inline-flex;",
    "      .brand {\n"
    "        margin: 0;\n"
    "        font-size: inherit;\n"
    "        display: inline-flex;")
sub(r"      \.main \{\n        display: grid;",
    "      .langswitch {\n"
    "        display: inline-flex;\n"
    "        align-items: center;\n"
    "        gap: 7px;\n"
    "      }\n\n"
    "      .langswitch a,\n"
    "      .langswitch span {\n"
    "        padding: 3px 7px;\n"
    "        border: 1px solid var(--line);\n"
    "        color: var(--quiet);\n"
    "      }\n\n"
    "      .langswitch [aria-current=\"true\"] {\n"
    "        border-color: var(--line-strong);\n"
    "        color: var(--text);\n"
    "      }\n\n"
    "      .main {\n        display: grid;")

# ---- body ----------------------------------------------------------------
sub(r'(?s)<header class="top" aria-label="Site header">.*?</header>',
    '<header class="top" aria-label="{{A_HEADER}}">\n'
    '        <h1 class="brand">66Ton99</h1>\n'
    '        <nav class="langswitch" aria-label="{{A_LANG}}">{{LANG_LINKS}}</nav>\n'
    '      </header>')
sub(r'<section class="main" aria-label="[^"]*">',
    '<section class="main" aria-label="{{A_MAIN}}">')
sub(r'<section aria-label="Visual profile">',
    '<section aria-label="{{A_VISUAL}}">')
sub(r'(?s)<img class="visual" src="data:image/svg\+xml;base64,[^"]+" alt="[^"]*" />',
    '<img class="visual" width="900" height="620" '
    'src="data:image/svg+xml;base64,{{SYSTEM_MAP}}" alt="{{SVG_ALT}}" />')
sub(r'<aside class="links" aria-label="Social profiles">',
    '<aside class="links" aria-label="{{A_PROFILES}}">')
sub(r"<span>Profiles</span>", "<span>{{T_PROFILES}}</span>")
sub(r"<span>Open</span>", "<span>{{OPEN}}</span>", count=5)
sub(r'(?s)<aside class="links" aria-label="Tools and references">.*?</aside>',
    '<aside class="links" aria-label="{{A_TOOLS}}">\n'
    "          <header>\n"
    "            <span>{{T_TOOLS}}</span>\n"
    "            <span>02</span>\n"
    "          </header>\n"
    '          <ul class="link-list">\n'
    "{{TOOLS_LIST}}\n"
    "          </ul>\n"
    "        </aside>")
sub(r'(?s)<footer class="foot">.*?</footer>',
    '<footer class="foot">\n'
    "        <span>66Ton99</span>\n"
    "        <span>{{FOOTER_R}}</span>\n"
    "      </footer>")

out.write_text(src, encoding="utf-8")
tokens = sorted(set(re.findall(r"\{\{([A-Z_0-9]+)\}\}", src)))
print(f"wrote {out.name} with {len(tokens)} tokens:")
print("  " + ", ".join(tokens))
