#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the EN + UK homepage from src/template-home.html."""

import base64
import pathlib
import re

BASE = "https://66ton99.org.ua"
HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / "site"


def system_map(alt, stack, mapping):
    svg = (HERE / "system-map.svg").read_text(encoding="utf-8")
    svg = (
        svg.replace("{{SVG_ALT}}", alt)
        .replace("{{SVG_STACK}}", stack)
        .replace("{{SVG_MAP}}", mapping)
    )
    return base64.b64encode(svg.encode("utf-8")).decode("ascii")


ICON = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" '
    'd="M3 5.5h18v1.6H3V5.5Zm0 4.1h18v2.2H3V9.6Zm0 4.7h18v3H3v-3Zm0 5.5h18v1.2H3v-1.2Z"/></svg>'
)


def tool(href, label, open_label, hreflang, lang=None):
    lang_attr = f' lang="{lang}"' if lang else ""
    return (
        "            <li>\n"
        f'              <a class="profile-link" href="{href}" hreflang="{hreflang}"{lang_attr}>\n'
        f"                {ICON}\n"
        f"                <strong>{label}</strong>\n"
        f"                <span>{open_label}</span>\n"
        "              </a>\n"
        "            </li>"
    )


EN = {
    "LANG": "en",
    "CANONICAL": f"{BASE}/",
    "OG_LOCALE": "en_US",
    "OG_LOCALE_ALT": "uk_UA",
    "OG_IMAGE": f"{BASE}/og-home.png",
    "OG_IMAGE_ALT": "66Ton99 — profiles and engineering references",
    "TITLE": "66Ton99 — profiles and engineering references",
    "DESC": "66Ton99 personal index: profile links and engineering references, "
    "including an AWG to amps chart and wire gauge ampacity calculator.",
    "LANG_LINKS": '<span aria-current="true" lang="en">EN</span>'
    '<a href="/uk" hreflang="uk" lang="uk">УК</a>',
    "A_HEADER": "Site header",
    "A_LANG": "Language",
    "A_MAIN": "66Ton99 homepage",
    "A_VISUAL": "Visual profile",
    "A_PROFILES": "Social profiles",
    "A_TOOLS": "Tools and references",
    "T_PROFILES": "Profiles",
    "T_TOOLS": "Tools",
    "OPEN": "Open",
    "SVG_ALT": "Abstract monochrome system map",
    "SYSTEM_MAP": system_map(
        "Abstract monochrome system map", "WEB / LINUX / CLOUD", "SYSTEM MAP"
    ),
    "TOOLS_LIST": "\n".join(
        [
            tool("/awg-to-amps", "AWG to amps", "Open", "en"),
            tool("/uk/awg-to-amps", "AWG в ампери", "Відкрити", "uk", "uk"),
        ]
    ),
    "FOOTER_R": "Personal index",
}

UK = {
    "LANG": "uk",
    "CANONICAL": f"{BASE}/uk",
    "OG_LOCALE": "uk_UA",
    "OG_LOCALE_ALT": "en_US",
    "OG_IMAGE": f"{BASE}/og-home-uk.png",
    "OG_IMAGE_ALT": "66Ton99 — профілі та інженерні довідники",
    "TITLE": "66Ton99 — профілі та інженерні довідники",
    "DESC": "Персональний індекс 66Ton99: посилання на профілі та інженерні довідники, "
    "зокрема таблиця AWG в ампери й калькулятор перерізу дроту.",
    "LANG_LINKS": '<a href="/" hreflang="en" lang="en">EN</a>'
    '<span aria-current="true" lang="uk">УК</span>',
    "A_HEADER": "Шапка сайту",
    "A_LANG": "Мова",
    "A_MAIN": "Головна сторінка 66Ton99",
    "A_VISUAL": "Візуальний профіль",
    "A_PROFILES": "Профілі в соцмережах",
    "A_TOOLS": "Інструменти та довідники",
    "T_PROFILES": "Профілі",
    "T_TOOLS": "Інструменти",
    "OPEN": "Відкрити",
    "SVG_ALT": "Абстрактна монохромна системна карта",
    "SYSTEM_MAP": system_map(
        "Абстрактна монохромна системна карта", "ВЕБ / LINUX / ХМАРА", "СИСТЕМНА КАРТА"
    ),
    "TOOLS_LIST": "\n".join(
        [
            tool("/uk/awg-to-amps", "AWG в ампери", "Відкрити", "uk"),
            tool("/awg-to-amps", "AWG to amps", "Open", "en", "en"),
        ]
    ),
    "FOOTER_R": "Персональний індекс",
}


def render(cfg, out_path):
    html = (HERE / "template-home.html").read_text(encoding="utf-8")
    for key, value in cfg.items():
        html = html.replace("{{" + key + "}}", str(value))

    leftover = set(re.findall(r"\{\{([A-Z_0-9]+)\}\}", html))
    if leftover:
        raise SystemExit(f"Unreplaced tokens in {out_path.name}: {sorted(leftover)}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path.relative_to(OUT)}  ({len(html):,} bytes)")


if __name__ == "__main__":
    render(EN, OUT / "index.html")
    render(UK, OUT / "_pages" / "uk-index.html")
