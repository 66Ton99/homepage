#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the 1200x630 Open Graph cards for both languages."""

import pathlib
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / "site"

W, H = 1200, 630
BG = "#0d0e0e"
ACCENT = "#ebe4d2"
MUTED = "#a69e92"
FAINT = "#777064"
LINE = "#7d7466"
GRID = (125, 116, 102, 40)

S = "/System/Library/Fonts/Supplemental/"
BOLD = S + "Arial Bold.ttf"
REG = S + "Arial.ttf"
MONO = "/System/Library/Fonts/Menlo.ttc"


def font(path, size, index=0):
    if path.endswith(".ttc"):
        return ImageFont.truetype(path, size, index=index)
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_width):
    lines, line = [], ""
    for word in text.split():
        probe = f"{line} {word}".strip()
        if draw.textlength(probe, font=fnt) <= max_width or not line:
            line = probe
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def build(name, kicker, title, subtitle, footer_right, title_size, cells):
    img = Image.new("RGB", (W, H), BG)
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for x in range(0, W, 54):
        gd.line([(x, 0), (x, H)], fill=GRID, width=1)
    for y in range(0, H, 54):
        gd.line([(0, y), (W, y)], fill=GRID, width=1)
    img = Image.alpha_composite(img.convert("RGBA"), grid).convert("RGB")
    d = ImageDraw.Draw(img)

    PAD = 70
    f_kick = font(MONO, 19)
    f_title = font(BOLD, title_size)
    f_sub = font(REG, 25)
    f_cell_label = font(MONO, 15)
    f_cell_value = font(MONO, 33, index=1)
    f_foot = font(MONO, 18)

    y = 64
    d.text((PAD, y), kicker.upper(), font=f_kick, fill=MUTED)
    y += 46

    for line in wrap(d, title, f_title, W - 2 * PAD - 40):
        d.text((PAD, y), line, font=f_title, fill=ACCENT)
        y += int(title_size * 0.98)

    y += 18
    for line in wrap(d, subtitle, f_sub, 900):
        d.text((PAD, y), line, font=f_sub, fill=MUTED)
        y += 36

    # data strip
    top = 432
    bottom = 520
    d.rectangle([PAD, top, W - PAD, bottom], outline=LINE, width=1)
    cell_w = (W - 2 * PAD) / len(cells)
    for i, (label, value) in enumerate(cells):
        cx = PAD + i * cell_w
        if i:
            d.line([(cx, top), (cx, bottom)], fill=LINE, width=1)
        d.text((cx + 22, top + 18), label.upper(), font=f_cell_label, fill=FAINT)
        d.text((cx + 22, top + 42), value, font=f_cell_value, fill=ACCENT)

    # footer
    fy = 566
    d.line([(PAD, fy), (W - PAD, fy)], fill=LINE, width=1)
    d.text((PAD, fy + 20), "66TON99.ORG.UA/AWG-TO-AMPS", font=f_foot, fill=FAINT)
    right = footer_right.upper()
    d.text(
        (W - PAD - d.textlength(right, font=f_foot), fy + 20),
        right,
        font=f_foot,
        fill=FAINT,
    )

    path = OUT / name
    img.save(path, "PNG", optimize=True)
    print(f"{name}  {img.size}  {path.stat().st_size:,} bytes")


CELLS = [("4 AWG", "21.15 mm²"), ("60 °C", "62 A"), ("200 °C", "131 A"), ("0 AWG", "112 A")]

build(
    "og-awg-to-amps.png",
    "Wire sizing / 30—0 AWG · copper",
    "AWG to amps chart & calculator",
    "Real copper cross-section in mm², ampacity at 60 °C and 200 °C, strand-count "
    "calculator, bundle derating and DC voltage drop.",
    "17 gauges",
    76,
    CELLS,
)

build(
    "og-awg-to-amps-uk.png",
    "Переріз дроту / 30—0 AWG · мідь",
    "AWG в ампери: таблиця і калькулятор",
    "Реальний переріз міді в мм², допустимий струм за 60 °C і 200 °C, калькулятор "
    "жилок, поправка на пучок і падіння напруги.",
    "17 калібрів",
    66,
    CELLS,
)
