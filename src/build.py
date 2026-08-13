#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the EN + UK AWG-to-amps pages, robots.txt and sitemap.xml into ../site."""

import json
import pathlib
import re

BASE = "https://66ton99.org.ua"
EN_URL = f"{BASE}/awg-to-amps"
UK_URL = f"{BASE}/uk/awg-to-amps"

HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / "site"

# gauge, mm2, bundle60, free60, bundle200, free200
ROWS = [
    ("30", 0.051, 2, 3, 3, 4),
    ("28", 0.080, 3, 4, 4, 6),
    ("26", 0.129, 4, 5, 5, 7),
    ("24", 0.205, 5, 7, 7, 10),
    ("22", 0.326, 5, 7, 11, 15),
    ("20", 0.518, 6, 9, 14, 20),
    ("18", 0.823, 8, 12, 19, 26),
    ("16", 1.31, 11, 15, 24, 34),
    ("14", 2.08, 14, 21, 32, 46),
    ("12", 3.31, 19, 27, 41, 60),
    ("10", 5.26, 26, 36, 54, 81),
    ("8", 8.37, 35, 50, 74, 113),
    ("6", 13.30, 48, 71, 100, 156),
    ("4", 21.15, 62, 95, 131, 210),
    ("2", 33.62, 81, 129, 173, 286),
    ("1", 42.41, 93, 152, 199, 338),
    ("0", 53.49, 112, 167, 224, 348),
]


# Conductor materials, by conductivity on the IACS scale (annealed copper = 100%).
#
# Resistivity is derived as COPPER_RESISTIVITY x 100/iacs, which keeps copper at
# exactly the 0.0175 the page has always used — about 1.5% above the 0.017241
# solid-wire IACS reference, the usual allowance for the helical lay of a
# stranded conductor.
#
# Ampacity scales as sqrt(iacs/100): identical geometry and an identical
# permitted temperature rise mean I^2*R is fixed, so current goes as the inverse
# square root of resistivity. Checked against NEC 310.16, where the aluminium to
# copper ratio averages 0.774 from 6 AWG to 4/0 against sqrt(0.612) = 0.782
# predicted — agreement to about 1%.
#
# The plated coppers are approximate: the figure depends on coating thickness
# and strand diameter. Tin at 96% assumes a ~1 um layer on a 0.08 mm strand,
# where tin occupies about 5% of the area and conducts at 15% of copper.
MATERIALS = [
    ("cu",     100.0, "Copper, annealed",      "Мідь, відпалена"),
    ("cusn",    96.0, "Copper, tinned",        "Мідь, луджена"),
    ("cuag",   100.0, "Copper, silver-plated", "Мідь, посріблена"),
    ("cuni",    95.0, "Copper, nickel-plated", "Мідь, нікельована"),
    ("al",      61.2, "Aluminium 1350",        "Алюміній 1350"),
    ("al8000",  61.0, "Aluminium alloy 8000",  "Алюмінієвий сплав 8000"),
    ("cca",     61.5, "Copper-clad aluminium", "Мідно-алюмінієвий (CCA)"),
    ("ccs",     30.0, "Copper-clad steel",     "Мідно-сталевий (CCS)"),
    ("ag",     105.0, "Silver",                "Срібло"),
]

# What the selector starts on, and therefore what the server-rendered table has
# to be computed for. Tinned copper, because that is what fine-stranded silicone
# lead wire actually is; the published ROWS above are the annealed-copper
# reference the whole model is built on, so the default view carries the 96%
# IACS penalty like any other material.
DEFAULT_MATERIAL = "cusn"


def material_json(lang):
    data = {
        key: {"iacs": iacs, "name": (en if lang == "en" else uk)}
        for key, iacs, en, uk in MATERIALS
    }
    return json.dumps(data, ensure_ascii=False)


def material_options(lang):
    custom = "Custom conductivity" if lang == "en" else "Власна провідність"
    out = [
        f'                <option value="{key}"{" selected" if key == DEFAULT_MATERIAL else ""}>'
        f'{(en if lang == "en" else uk)} · {iacs:g}% IACS</option>'
        for key, iacs, en, uk in MATERIALS
    ]
    out.append(f'                <option value="custom">{custom}</option>')
    return "\n".join(out)


# Insulation, by the conductor temperature it permits. That rating is the only
# thing insulation contributes to ampacity here; its thermal resistance matters
# too, but that needs a wall thickness datasheets rarely make comparable.
#
# Ampacity at a different rating scales as sqrt((T-30)/(1+alpha*(T-20))): heat
# leaves as dT while heat arrives as I^2*R, and R itself climbs with T. Checked
# against NEC 310.16, where 90/60 C ratios run 1.333-1.360 for 10 AWG and up
# against 1.347 predicted.
#
# Silicone 200 C is the reference at exactly 1.000, so the published 200 C
# columns stay untouched.
INSULATIONS = [
    ("pvc70",   70,  "PVC",                 "ПВХ"),
    ("thhn",    90,  "PVC/nylon, THHN",     "ПВХ/нейлон, THHN"),
    ("xlpe",    90,  "XLPE / EPR",          "Зшитий поліетилен / EPR"),
    ("pvc105", 105,  "PVC, heat-resistant", "ПВХ, термостійкий"),
    ("etfe",   150,  "ETFE (Tefzel)",       "ETFE (Tefzel)"),
    ("sil150", 150,  "Silicone",            "Силікон"),
    ("sil180", 180,  "Silicone",            "Силікон"),
    ("sil200", 200,  "Silicone",            "Силікон"),
    ("fep",    200,  "FEP",                 "FEP"),
    ("ptfe",   260,  "PTFE / PFA",          "PTFE / PFA"),
]


def insulation_json(lang):
    data = {
        key: {"c": celsius, "name": (en if lang == "en" else uk)}
        for key, celsius, en, uk in INSULATIONS
    }
    return json.dumps(data, ensure_ascii=False)


def insulation_options(lang):
    custom = "Custom rating" if lang == "en" else "Власна температура"
    out = [
        f'                <option value="{key}"{" selected" if key == "sil200" else ""}>'
        f'{(en if lang == "en" else uk)} · {celsius} °C</option>'
        for key, celsius, en, uk in INSULATIONS
    ]
    out.append(f'                <option value="custom">{custom}</option>')
    return "\n".join(out)


INSTALL_KEYS = ["bundle", "free", "4-6", "7-9", "10-20", "21-30", "31-40", "41-plus"]


COPPER_RESISTIVITY = 0.0175  # Ω·mm²/m at 20 °C
DEFAULT_VOLTAGE = {"dc": 24, "ac1": 230, "ac3": 400}

# The default conductor, mirrored from MATERIALS so the two cannot drift.
DEFAULT_IACS = next(iacs for key, iacs, _en, _uk in MATERIALS if key == DEFAULT_MATERIAL)
DEFAULT_RESISTIVITY = COPPER_RESISTIVITY * (100 / DEFAULT_IACS)
DEFAULT_AMPACITY_FACTOR = (DEFAULT_IACS / 100) ** 0.5


def fmt_area(area, decimal_sep):
    text = f"{area:.3f}" if area < 10 else f"{area:.2f}"
    return text.replace(".", decimal_sep)


def fmt_amps(amps, decimal_sep):
    return f"{amps:.1f}".replace(".", decimal_sep)


def fmt_resistance(milliohm, decimal_sep):
    """Resistance in mΩ/m spans 0.33 to 343 across the table, so the number of
    decimals has to follow the magnitude. Mirrored exactly in the page's JS, or
    the server-rendered row would flicker when the script re-renders it."""
    if milliohm >= 100:
        text = f"{milliohm:.0f}"
    elif milliohm >= 10:
        text = f"{milliohm:.1f}"
    elif milliohm >= 1:
        text = f"{milliohm:.2f}"
    else:
        text = f"{milliohm:.3f}"
    return text.replace(".", decimal_sep)


def fmt_length(metres, decimal_sep):
    text = f"{metres:.0f}" if metres >= 100 else f"{metres:.1f}"
    return text.replace(".", decimal_sep)


def fmt_power(watts, decimal_sep, unit_w, unit_kw):
    """Mirrored in the page's JS; see fmt_resistance for why that matters."""
    if watts < 1000:
        return f"{watts:.0f} {unit_w}"
    kilowatts = watts / 1000
    digits = 0 if kilowatts >= 100 else 1 if kilowatts >= 10 else 2
    return f"{kilowatts:.{digits}f}".replace(".", decimal_sep) + f" {unit_kw}"


def max_run_length(area, current, voltage, run_factor, power_factor=1.0):
    """Longest one-way run that keeps the drop within 3% at the rated current."""
    resistance = DEFAULT_RESISTIVITY / area
    return (0.03 * voltage) / (run_factor * current * resistance * power_factor)


def build_tbody(lang):
    sep = "." if lang == "en" else ","
    aria = (
        "Load {g} AWG into the calculator"
        if lang == "en"
        else "Підставити {g} AWG у калькулятор"
    )
    amp = "A" if lang == "en" else "А"
    watt = "W" if lang == "en" else "Вт"
    kilowatt = "kW" if lang == "en" else "кВт"
    out = []
    # Server-rendered in the DC state at 24 V on the default conductor, matching
    # the page defaults, so a crawler sees real numbers and the JS re-render
    # produces identical text.
    factor = DEFAULT_AMPACITY_FACTOR
    for gauge, area, b60_ref, f60_ref, b200_ref, f200_ref in ROWS:
        b60, f60, b200, f200 = (value * factor for value in (b60_ref, f60_ref, b200_ref, f200_ref))
        resistance = fmt_resistance(DEFAULT_RESISTIVITY / area * 1000, sep)
        length = fmt_length(
            max_run_length(area, b60, DEFAULT_VOLTAGE["dc"], 2), sep
        )
        out.append(
            f'                  <tr data-gauge="{gauge}">\n'
            f'                    <th scope="row"><button type="button" class="row-btn" '
            f'aria-label="{aria.format(g=gauge)}">{gauge} <span class="unit">AWG</span></button></th>\n'
            f"                    <td>{fmt_area(area, sep)}</td>\n"
            f'                    <td class="js-b60">{fmt_amps(b60, sep)} {amp}</td>\n'
            f'                    <td class="js-f60">{fmt_amps(f60, sep)} {amp}</td>\n'
            f'                    <td class="js-b200">{fmt_amps(b200, sep)} {amp}</td>\n'
            f'                    <td class="js-f200">{fmt_amps(f200, sep)} {amp}</td>\n'
            f'                    <td class="js-r">{resistance}</td>\n'
            f'                    <td class="js-len">{length}</td>\n'
            f'                    <td class="js-p">'
            f'{fmt_power(DEFAULT_VOLTAGE["dc"] * b60, sep, watt, kilowatt)}</td>\n'
            f"                  </tr>"
        )
    return "\n".join(out)


def build_options(labels):
    return "\n".join(
        f'                      <option value="{key}">{labels[key]}</option>'
        for key in INSTALL_KEYS
    )


def faq_html(items):
    parts = ['            <div class="faq">']
    for question, answer in items:
        parts.append(
            f'              <details class="faq-item">\n'
            f'                <summary class="faq-q"><h3>{question}</h3></summary>\n'
            f'                <div class="faq-a">{answer}</div>\n'
            f"              </details>"
        )
    parts.append("            </div>")
    return "\n".join(parts)


def strip_tags(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()


def conv_html(pairs):
    body = "\n".join(
        f"              <div><dt>{a}</dt><dd>{b}</dd></div>" for a, b in pairs
    )
    return f'            <dl class="conv-list">\n{body}\n            </dl>'


def quicknav(items):
    return "\n".join(f'              <li><a href="{h}">{t}</a></li>' for h, t in items)


# --------------------------------------------------------------------------
# ENGLISH
# --------------------------------------------------------------------------

EN_FAQ = [
    (
        "How many amps can each AWG wire size carry?",
        "<p>For tinned copper conductors at 30&nbsp;°C ambient, the conservative 60&nbsp;°C reference in "
        "the chart above gives roughly 7.8&nbsp;A for 18&nbsp;AWG, 13.7&nbsp;A for 14&nbsp;AWG, "
        "25.5&nbsp;A for 10&nbsp;AWG, 34.3&nbsp;A for 8&nbsp;AWG, 60.7&nbsp;A for 4&nbsp;AWG and "
        "109.7&nbsp;A for 0&nbsp;AWG "
        "with up to three current-carrying conductors in a cable. A single conductor in free air runs "
        "cooler and carries more. High-temperature silicone wire rated to 200&nbsp;°C carries roughly "
        "twice the conservative figure, but only if every terminal, fuse and connector in the circuit "
        "is rated for that temperature too.</p>",
    ),
    (
        "What is the difference between the 60&nbsp;°C and 200&nbsp;°C columns?",
        "<p>Both describe the same copper. The difference is how hot you allow the conductor to get. "
        "The 60&nbsp;°C columns are the everyday design baseline: the wire stays touch-safe and the "
        "insulation, terminals and adjacent materials are comfortable. The 200&nbsp;°C columns are the "
        "thermal limit of the silicone insulation itself — the current at which the conductor reaches "
        "200&nbsp;°C. Treat the second number as a ceiling for short, well-ventilated runs, not as a "
        "design target.</p>",
    ),
    (
        "How do I convert AWG to mm²?",
        "<p>AWG is a logarithmic scale, so there is a closed formula rather than a simple ratio. The "
        "conductor diameter in millimetres is <em>d</em>&nbsp;=&nbsp;0.127&nbsp;×&nbsp;92<sup>(36−AWG)/39</sup>, "
        "and the cross-section is <em>A</em>&nbsp;=&nbsp;π&nbsp;<em>d</em>²/4. In practice, every three AWG "
        "steps roughly double the copper area, and six steps roughly double the diameter. The mm² column "
        "in the chart above already carries the ASTM&nbsp;B258 nominal values, so you can read the "
        "conversion straight off the table.</p>",
    ),
    (
        "Why is 25&nbsp;mm² wire sold as 4&nbsp;AWG?",
        "<p>Because it is a marketing label, not a measurement. True 4&nbsp;AWG is 21.15&nbsp;mm² of "
        "copper. Sellers of flexible silicone wire frequently round up to the nearest metric size, or "
        "quote the outside diameter over the insulation instead of the conductor. Always size from the "
        "strand count and strand diameter on the datasheet — that is what the calculator on this page "
        "asks for — and treat any headline mm² figure as unverified until it matches.</p>",
    ),
    (
        "Does a higher strand count increase ampacity?",
        "<p>Not by itself. Ampacity follows the total copper cross-section, so 1&nbsp;650 strands of "
        "0.08&nbsp;mm carry the same current as a solid conductor of the same area. What fine stranding "
        "buys you is flexibility, vibration and flex-cycle life, and easier routing in tight enclosures. "
        "At DC and mains frequencies the skin effect is negligible at these sizes, so stranding gives no "
        "measurable current bonus.</p>",
    ),
    (
        "How do I calculate DC voltage drop?",
        "<p>Voltage drop is the load current times the resistance of the full circuit — out and back. "
        "With copper resistivity ρ&nbsp;=&nbsp;0.0175&nbsp;Ω·mm²/m, the drop is "
        "ΔU&nbsp;=&nbsp;<em>I</em>&nbsp;×&nbsp;ρ&nbsp;×&nbsp;2<em>L</em>&nbsp;/&nbsp;<em>A</em>, where "
        "<em>L</em> is the one-way run length. Most low-voltage DC systems aim to keep the drop under "
        "3&nbsp;% of system voltage; on a 12&nbsp;V circuit that is only 0.36&nbsp;V, which is why long "
        "12&nbsp;V runs are usually sized by voltage drop rather than by ampacity.</p>",
    ),
    (
        "How much should I derate for bundled conductors?",
        "<p>Bundling traps heat, so every conductor in the group carries less. Common factors are 80&nbsp;% "
        "for 4–6 current-carrying conductors, 70&nbsp;% for 7–9, 50&nbsp;% for 10–20, 45&nbsp;% for 21–30, "
        "40&nbsp;% for 31–40 and 35&nbsp;% beyond that. Ambient temperature derates on top of grouping, and "
        "the two multiply. Conductors that never carry current at the same time, and neutrals in a balanced "
        "circuit, usually do not count towards the group.</p>",
    ),
    (
        "Can I use this chart for aluminium wire?",
        "<p>Yes — switch the conductor material and every column recalculates. Aluminium at 61.2&nbsp;% "
        "IACS carries about 78&nbsp;% of copper's current at the same cross-section, because ampacity "
        "follows the square root of conductivity. Matching a copper conductor therefore takes 1.64 times "
        "the area, roughly two AWG sizes up. The arithmetic is the easy part: aluminium creeps under "
        "clamping pressure, oxidises on contact with air and expands more than copper when hot, so it "
        "needs terminals listed for aluminium, anti-oxidant compound and a torque wrench. Copper-clad "
        "aluminium behaves the same electrically while terminating like copper, and copper-clad steel at "
        "30&nbsp;% IACS is for strength and RF, not for power.</p>",
    ),
    (
        "Does the ampacity change between DC and AC?",
        "<p>Not meaningfully at mains frequency. Alternating current crowds toward the conductor "
        "surface, but the skin depth in copper is about 9.4&nbsp;mm at 50&nbsp;Hz and 8.5&nbsp;mm at "
        "60&nbsp;Hz, while a 0&nbsp;AWG conductor has a radius of just 4.1&nbsp;mm. By IEC&nbsp;60287 "
        "the resistance rise works out at 0.08&nbsp;% for 0&nbsp;AWG and under 0.01&nbsp;% below "
        "4&nbsp;AWG, so the same table serves DC, single-phase and three-phase. What the current type "
        "really changes is the voltage drop: two conductors out and back for DC and single-phase, √3 "
        "line-to-line for three-phase, with the power factor on top. Skin effect only becomes worth "
        "counting in the hundreds of hertz, which is why the calculator asks for a frequency.</p>",
    ),
    (
        "Is this chart the same as NEC or IEC ampacity?",
        "<p>No. This is a reference for flexible, fine-stranded tinned copper lead wire with silicone "
        "insulation, of the kind used in equipment wiring, battery leads, robotics and RC. Building "
        "installations are governed by NEC&nbsp;310 tables in North America and IEC&nbsp;60364-5-52 in "
        "Europe, which assume different insulation, installation methods and correction factors. Use those "
        "codes for fixed wiring, and use this chart for equipment and appliance wiring.</p>",
    ),
]

EN_CONTENT = f"""            <section id="how-to-read">
              <h2>How to read this AWG to amps chart</h2>
              <p>
                Every row pairs an American Wire Gauge size with the nominal copper cross-section it
                actually contains, in mm², and with four current ratings. The gauge number alone tells you
                nothing about how much current a wire can carry — the copper area does, and that is why the
                mm² column sits second, right next to the gauge.
              </p>

              <h3>Copper area, not outside diameter</h3>
              <p>
                Flexible silicone wire is sold by its outside diameter far more often than by its conductor.
                A cable advertised as 8&nbsp;AWG may measure 8&nbsp;mm across the jacket and hold barely
                6&nbsp;mm² of copper. Size from the strand count and strand diameter on the datasheet, then
                compare that area against the chart. The calculator above does exactly this arithmetic.
              </p>

              <h3>The 60&nbsp;°C and 200&nbsp;°C columns</h3>
              <p>
                The 60&nbsp;°C columns are the conservative everyday reference: the conductor stays cool,
                terminals stay within their own ratings, and there is margin for a hot day. The 200&nbsp;°C
                columns are the thermal limit of the silicone insulation, not a design target. A conductor
                run at its 200&nbsp;°C limit will melt heat-shrink, discolour terminals and burn skin on
                contact, so use it only to understand the headroom you have, never as the number you design to.
              </p>

              <h3>Maximum load — where the current type really shows</h3>
              <p>
                The ampacity columns are in amperes, and amperes are amperes: a conductor does not care
                whether the heat came from DC or AC. What changes completely is what those amperes are
                <em>worth</em>. The same 0&nbsp;AWG conductor at its 109.7&nbsp;A rating delivers
                <strong>2.6&nbsp;kW</strong> on a 24&nbsp;V DC system, <strong>13.2&nbsp;kW</strong> on
                120&nbsp;V single-phase, and <strong>36&nbsp;kW</strong> on 208&nbsp;V three-phase — a
                factor of fourteen, from voltage and the √3. On a 230/400&nbsp;V system the spread is
                wider still, at twenty-nine.
              </p>
              <p>
                Read the other way round, that is the number most people actually want: for a given load,
                the current you must carry is wildly different between DC and AC, and the copper you need
                follows the current, not the watts. A 3&nbsp;kW load is 125&nbsp;A at 24&nbsp;V DC and
                8.3&nbsp;A at 208&nbsp;V three-phase.
              </p>

              <h3>Resistance and maximum run</h3>
              <p>
                The last two columns are the ones the current-type toggle moves most. Resistance is
                ρ/<em>A</em> per metre, switching to the AC value at your chosen frequency. Maximum run is
                the longest one-way length that keeps the drop within 3&nbsp;% while the conductor carries
                its ≤3&nbsp;conductor 60&nbsp;°C current, at the voltage set in the calculator.
              </p>
              <p>
                That last column is worth staring at. The same 0&nbsp;AWG conductor is good for
                <strong>9.6&nbsp;m</strong> on a 24&nbsp;V DC system and <strong>105&nbsp;m</strong> on
                208&nbsp;V three-phase — a factor of eleven, from voltage and the √3 alone, with the
                copper completely unchanged. Ampacity is rarely what limits a long run; voltage drop is.
              </p>

              <h3>Bundled versus free air</h3>
              <p>
                A single conductor hanging in still air sheds heat in every direction. The same conductor in
                the middle of a loom shares its heat with its neighbours, and all of them run hotter. The
                <strong>≤3 conductors</strong> columns assume a normal cable or small bundle; the
                <strong>free air</strong> columns assume one conductor with nothing around it. Anything above
                three current-carrying conductors needs the grouping factors in the calculator on top.
              </p>
            </section>

            <section id="how-it-works">
              <h2>How the wire gauge calculator works</h2>
              <p>
                The calculator starts from the physical construction of the wire rather than from its label,
                then walks the same four steps an engineer would.
              </p>

              <h3>1. Cross-section from strand count</h3>
              <p class="formula"><span>Copper area</span>A = n × π × d² / 4</p>
              <p>
                <strong>n</strong> is the number of strands and <strong>d</strong> is the diameter of one
                strand in millimetres. A typical 4&nbsp;AWG silicone lead of 1&nbsp;650 strands at
                0.08&nbsp;mm works out to 8.29&nbsp;mm² — well under the 21.15&nbsp;mm² a real 4&nbsp;AWG
                conductor carries, which is exactly the kind of mismatch this page exists to catch.
              </p>

              <h3>2. Equivalent AWG</h3>
              <p class="formula"><span>Gauge from area</span>AWG = 36 − 39 × log(d<sub>eq</sub> / 0.127) / log(92)</p>
              <p>
                The area is converted back to an equivalent solid diameter, then to a gauge number on the
                AWG scale. The result is usually fractional, which is honest: real stranded wire rarely
                lands exactly on a gauge.
              </p>

              <h3>3. Ambient and grouping derating</h3>
              <p class="formula"><span>Derated ampacity</span>I = I<sub>base</sub> × k<sub>ambient</sub> × k<sub>grouping</sub></p>
              <p>
                Base ampacity comes from your own cross-section, not from whichever row is closest:
                between two tabulated gauges the current follows a power law in area,
                <em>I</em>&nbsp;∝&nbsp;<em>A</em><sup>k</sup>, with <em>k</em> taken from that pair of rows
                — 0.5 to 0.7 here, because heat arrives through a section and leaves through a surface. Land
                exactly on a gauge and you get the published figure back. The ambient factor is interpolated between
                the published correction points — 60&nbsp;°C conductors lose capacity quickly above
                30&nbsp;°C, while 200&nbsp;°C conductors keep working far into the heat. The grouping factor
                comes from the installation selector, and the two multiply.
              </p>

              <h3>4. Voltage drop and wire loss</h3>
              <p class="formula"><span>Direct current, and single-phase AC</span>ΔU = 2 × I × R × L × cos φ<span
                style="margin-top:10px">Three-phase AC, line to line</span>ΔU = √3 × I × R × L × cos φ</p>
              <p>
                <em>R</em> is the resistance per metre, ρ/<em>A</em>, with ρ&nbsp;=&nbsp;0.0175&nbsp;Ω·mm²/m
                for copper at 20&nbsp;°C, and <em>L</em> is the one-way run. Direct current and single-phase
                AC both travel out and back, so the length counts twice. A three-phase circuit does not:
                the line-to-line drop carries a √3 instead. Power factor is 1 for DC, which is why the
                first formula collapses to the familiar 2<em>IRL</em>.
              </p>
              <p>
                Power lost as heat is <em>I</em>²<em>R</em> per conductor — two conductors for DC and
                single-phase, three for three-phase. On low-voltage systems this, not ampacity, is usually
                what forces a bigger conductor: a 12&nbsp;V circuit allows only 0.36&nbsp;V of drop at the
                common 3&nbsp;% target.
              </p>
              <p>
                Reactance is left out. For the cross-sections and run lengths this page covers it sits well
                below the uncertainty in the resistance itself, but on long three-phase runs in conduit it
                stops being negligible and you should size from the cable's published R and X.
              </p>

              <h3>5. Why three-phase derates, and why frequency mostly does not</h3>
              <p>
                Two separate things are at work, and they are wildly different in size.
              </p>
              <p>
                <strong>Conductor count is the big one.</strong> A three-phase circuit puts three
                current-carrying conductors in the cable where DC and single-phase put two. Three
                conductors each dissipating <em>I</em>²<em>R</em> make half again as much heat in the same
                bundle, so each one has to be rated lower. IEC&nbsp;60364-5-52 handles this by publishing
                separate <em>2 loaded conductors</em> and <em>3 loaded conductors</em> columns; across its
                copper tables the ratio averages <strong>0.915</strong>, and that is the factor applied to
                the in-cable columns here. It is a frequency-independent, roughly 9&nbsp;% cut — the reason
                0&nbsp;AWG reads 109.7&nbsp;A on DC and 100.4&nbsp;A on three-phase. The free-air columns
                describe one isolated conductor, which is the same object in every mode, so they do not
                move.
              </p>
              <p>
                <strong>Frequency is the small one</strong>, at least at mains. Alternating current pushes
                charge toward the conductor surface, so resistance rises — but in copper at 60&nbsp;Hz the
                skin depth is about 8.5&nbsp;mm, while even a 0&nbsp;AWG conductor has a radius of only
                4.1&nbsp;mm.
              </p>
              <p class="formula"><span>Skin and proximity, IEC 60287-1-1</span>y<sub>s</sub> = x<sub>s</sub>⁴ / (192 + 0.8 x<sub>s</sub>⁴)<span style="margin-top:10px">y<sub>p</sub> = y<sub>s</sub> (d/s)² [0.312 (d/s)² + 1.18 / (y<sub>s</sub> + 0.27)]</span></p>
              <p>
                Both effects are counted — skin, plus the proximity effect of neighbouring conductors, which
                dominates once you leave mains frequency. Together they come to <strong>0.40&nbsp;%</strong>
                at 60&nbsp;Hz for 0&nbsp;AWG, 0.06&nbsp;% at 4&nbsp;AWG and nothing measurable below that.
                This is the entire difference between DC and single-phase AC here: both have two loaded
                conductors, and unarmoured low-voltage wire has no sheath or dielectric losses to add. The
                table shows a decimal place so you can see it on the gauges where it exists — 0&nbsp;AWG
                goes from 109.7&nbsp;A to 109.5&nbsp;A — and read as identical where it genuinely is. Ampacity scales as
                1/√(1+y<sub>s</sub>), so it moves by well under a tenth of a percent — far less than the
                spread between one manufacturer's datasheet and another's. So the frequency term alone would not justify a
                separate AC column; the conductor count is what does.
              </p>
              <p>
                It does start to matter higher up. At 400&nbsp;Hz — aircraft and some drive systems —
                0&nbsp;AWG picks up 17&nbsp;%, which is why the calculator takes a frequency rather than
                assuming mains. The published fit holds to x<sub>s</sub>&nbsp;≤&nbsp;2.8, roughly 1&nbsp;kHz
                on the largest gauge here; above that the calculator flags its own result as indicative.
              </p>
            </section>

            <section id="materials">
              <h2>Conductor materials</h2>
              <p>
                AWG is a geometric size, so the cross-section in the table is the same whatever the metal
                is. What changes is how much current that cross-section can carry and how much voltage it
                drops. Both follow from one number — conductivity, quoted on the IACS scale where annealed
                copper is 100&nbsp;%.
              </p>
              <p class="formula"><span>Ampacity against copper</span>I / I<sub>Cu</sub> = √(σ / σ<sub>Cu</sub>)<span
                style="margin-top:10px">Resistance against copper</span>R / R<sub>Cu</sub> = σ<sub>Cu</sub> / σ</p>
              <p>
                Identical geometry and an identical permitted temperature rise mean <em>I</em>²<em>R</em> is
                fixed, so current goes as the inverse square root of resistivity. That is not a rule of
                thumb: against NEC&nbsp;310.16 the aluminium-to-copper ratio averages <strong>0.774</strong>
                from 6&nbsp;AWG to 4/0, where √0.612 predicts <strong>0.782</strong>.
              </p>

              <h3>What the selector offers</h3>
              <dl class="conv-list">
                <div><dt>Copper</dt><dd>100% IACS · ×1.000</dd></div>
                <div><dt>Silver</dt><dd>105% IACS · ×1.025</dd></div>
                <div><dt>Tinned copper</dt><dd>96% IACS · ×0.980</dd></div>
                <div><dt>Nickel-plated</dt><dd>95% IACS · ×0.975</dd></div>
                <div><dt>Aluminium 1350</dt><dd>61.2% IACS · ×0.782</dd></div>
                <div><dt>Alloy 8000</dt><dd>61% IACS · ×0.781</dd></div>
                <div><dt>Copper-clad alu</dt><dd>61.5% IACS · ×0.784</dd></div>
                <div><dt>Copper-clad steel</dt><dd>30% IACS · ×0.548</dd></div>
              </dl>
              <p>
                Anything else goes in as a custom % IACS, which is the honest way to handle a datasheet
                that quotes its own figure.
              </p>

              <h3>Plated coppers</h3>
              <p>
                Plating is about the environment, not conduction. Tin resists corrosion and keeps solder
                wetting; nickel survives past 200&nbsp;°C where tin has long melted; silver is for RF, where
                current rides the surface. The penalty is small and depends on how thick the coating is
                relative to the strand: on a 0.08&nbsp;mm strand a micron of tin occupies roughly 5&nbsp;% of
                the area and conducts at 15&nbsp;% of copper, which is where the 96&nbsp;% figure comes from.
                On thicker strands it is less. Silver plating does not change DC resistance measurably,
                since the bulk is still copper.
              </p>

              <h3>Aluminium, and what it costs you</h3>
              <p>
                Aluminium carries about 78&nbsp;% of copper's current at the same size, so matching a copper
                conductor takes <strong>1.64× the area — roughly two AWG sizes up</strong>. It is still worth
                it on long runs, because it is around a third of the weight for the same conductance and
                much cheaper.
              </p>
              <p>
                The catch is never the metal, it is the joint. Aluminium creeps under clamping pressure, so
                a terminal that was tight last year may not be now; it grows an insulating oxide the moment
                it meets air; and it expands about 40&nbsp;% more than copper with temperature, working
                itself loose through every heating cycle. Aluminium branch circuits earned their reputation
                in the 1960s and 70s for exactly this. Use terminals listed for aluminium, apply
                anti-oxidant compound, torque to the figure on the connector, and never put bare aluminium
                against bare copper in a damp place — the galvanic pair eats the aluminium.
              </p>
              <p>
                Fine-stranded silicone wire, which is what this page is mostly about, is not made in
                aluminium: it does not survive the flex cycles.
              </p>

              <h3>Copper-clad conductors</h3>
              <p>
                Copper-clad aluminium is aluminium with a copper skin, typically 10&nbsp;% by volume. It
                terminates like copper and conducts like aluminium, which is a reasonable trade — the
                problem is that it is frequently sold <em>as</em> copper. Strip a sample: the core is
                silver-coloured. Copper-clad steel is a different animal at 30&nbsp;% IACS, made for
                mechanical strength and RF skin conduction, not for carrying power; a magnet identifies it
                instantly.
              </p>

              <h3>One caveat on temperature</h3>
              <p>
                Every figure here is at 20&nbsp;°C. A conductor actually running at 60&nbsp;°C has around
                16&nbsp;% more resistance, and aluminium's temperature coefficient (0.00403/K) is slightly
                worse than copper's (0.00393/K). For voltage drop on a hot circuit, add that margin
                yourself — the calculator does not, because it would need a conductor temperature rather
                than an ambient one.
              </p>
            </section>

            <section id="insulation">
              <h2>Insulation</h2>
              <p>
                Insulation contributes one thing to ampacity: how hot it will let the conductor get. Copper
                does not care — it is happy at 400&nbsp;°C. The plastic around it decides where you have to
                stop, and that single number moves the high-temperature column of the table.
              </p>
              <p class="formula"><span>Ampacity at a different rating</span>I / I<sub>200</sub> = √( (T−30) / (1 + α(T−20)) ) ÷ √( 170 / (1 + α·180) )</p>
              <p>
                Heat leaves the conductor in proportion to ΔT while heat arrives as <em>I</em>²<em>R</em>,
                and <em>R</em> itself climbs with temperature — which is why the gain from a hotter rating
                is less than it first looks. Against NEC&nbsp;310.16 this predicts the 90&nbsp;°C to
                60&nbsp;°C ratio as <strong>1.347</strong> where the published columns give 1.333 to 1.360
                for 10&nbsp;AWG and larger. Silicone at 200&nbsp;°C is the reference at exactly 1.000, so
                selecting it reproduces the published data untouched.
              </p>

              <h3>What the selector offers</h3>
              <dl class="conv-list">
                <div><dt>PVC</dt><dd>70 °C · ×0.579</dd></div>
                <div><dt>PVC/nylon THHN</dt><dd>90 °C · ×0.687</dd></div>
                <div><dt>XLPE / EPR</dt><dd>90 °C · ×0.687</dd></div>
                <div><dt>PVC, heat-resistant</dt><dd>105 °C · ×0.751</dd></div>
                <div><dt>ETFE (Tefzel)</dt><dd>150 °C · ×0.893</dd></div>
                <div><dt>Silicone</dt><dd>180 °C · ×0.962</dd></div>
                <div><dt>Silicone, FEP</dt><dd>200 °C · ×1.000</dd></div>
                <div><dt>PTFE / PFA</dt><dd>260 °C · ×1.090</dd></div>
              </dl>

              <h3>The rule that catches people out</h3>
              <p>
                <strong>The whole circuit runs at the temperature of its weakest part, and that is almost
                never the wire.</strong> A breaker terminal listed for 75&nbsp;°C caps the whole run at
                75&nbsp;°C no matter what the insulation says — NEC&nbsp;110.14(C) makes this explicit, and
                most equipment under 100&nbsp;A is listed at 60&nbsp;°C. Buying 200&nbsp;°C silicone and
                sizing from its 200&nbsp;°C column, then landing it in a 75&nbsp;°C lug, is how connections
                cook. This is exactly why the conservative 60&nbsp;°C column stays fixed in this table
                regardless of what you select: for most real installations it is the number that governs.
              </p>
              <p>
                The high-temperature rating buys you margin in a hot enclosure, survival next to an exhaust
                or a heater, and the ability to run at full current when the ambient is already 80&nbsp;°C.
                It does not license you to push more current through the same terminals.
              </p>

              <h3>Choosing between them</h3>
              <p>
                <strong>PVC</strong> is cheap, tough against abrasion and stiff in the cold; it softens
                where it is hot and gives off hydrogen chloride in a fire, which is why LSZH compounds
                replace it in tunnels and ships. <strong>XLPE</strong> is PVC's crosslinked cousin: same
                price bracket, better heat, does not melt and flow. <strong>Silicone</strong> is the most
                flexible thing on the list by a wide margin and survives 200&nbsp;°C, but it tears and
                abrades easily, so it wants a sleeve wherever it can rub. <strong>PTFE and PFA</strong> are
                the best electrically and thermally and shrug off almost every solvent, at several times
                the price and with noticeably less flexibility. <strong>ETFE</strong> is the compromise the
                aerospace world settled on: thin wall, tough, 150&nbsp;°C.
              </p>

              <h3>Two things this does not model</h3>
              <p>
                Wall thickness. A thick jacket is a thermal blanket, so two 90&nbsp;°C cables of different
                construction do not carry the same current. Datasheets rarely publish thickness in a
                comparable way, so only the rating is used here.
              </p>
              <p>
                Voltage rating, which is a separate property entirely. 600&nbsp;V, 1&nbsp;kV and 3&nbsp;kV
                versions of the same insulation share a temperature rating and differ only in wall. Check it
                separately — nothing on this page tells you whether the insulation will hold your voltage.
              </p>
            </section>

            <section id="conversions">
              <h2>AWG to mm² at a glance</h2>
              <p>
                Nominal copper cross-sections per ASTM&nbsp;B258, with the nearest metric cable size the
                market actually sells against each one.
              </p>
{conv_html([
    ("0 AWG", "53.49 mm² · ≈ 50 mm²"),
    ("2 AWG", "33.62 mm² · ≈ 35 mm²"),
    ("4 AWG", "21.15 mm² · ≈ 25 mm²"),
    ("6 AWG", "13.30 mm² · ≈ 16 mm²"),
    ("8 AWG", "8.37 mm² · ≈ 10 mm²"),
    ("10 AWG", "5.26 mm² · ≈ 6 mm²"),
    ("12 AWG", "3.31 mm² · ≈ 4 mm²"),
    ("14 AWG", "2.08 mm² · ≈ 2.5 mm²"),
    ("16 AWG", "1.31 mm² · ≈ 1.5 mm²"),
    ("18 AWG", "0.823 mm² · ≈ 1 mm²"),
    ("20 AWG", "0.518 mm² · ≈ 0.5 mm²"),
    ("22 AWG", "0.326 mm² · ≈ 0.35 mm²"),
])}
              <p>
                The right-hand figure is the size a supplier will usually quote. It is almost always larger
                than the true AWG area, so a metric cable labelled as an AWG equivalent is safe on ampacity
                and misleading on price per millimetre of copper.
              </p>
            </section>

            <section id="faq">
              <h2>Frequently asked questions</h2>
{faq_html(EN_FAQ)}
            </section>

            <section id="source">
              <h2>Read the source, or fix it</h2>
              <p>
                This page is open source. The table data, both translations, the calculator and
                this text are all produced by one generator, which is why the English and
                Ukrainian versions cannot drift apart.
              </p>
              <ul>
                <li><strong>src/build.py</strong> — the ampacity table, the copy, the FAQ and the JSON-LD</li>
                <li><strong>src/template.html</strong> — the page shell and the calculator</li>
                <li><strong>src/test.js</strong> — checks that run the calculator against the built pages</li>
              </ul>
              <p>
                Found a wrong number, or want a gauge added? Open an issue or send a pull request
                at <a href="https://github.com/66Ton99/homepage" target="_blank"
                rel="noopener noreferrer">github.com/66Ton99/homepage</a>. Corrections backed by a
                datasheet or a standard are especially welcome — the AWG 24–30 rows are the
                shakiest, since they are indicative for fine-stranded silicone wire rather than
                taken from a single authoritative table.
              </p>
            </section>"""

EN = {
    "LANG": "en",
    "JS_LOCALE": "en-US",
    "OG_LOCALE": "en_US",
    "OG_LOCALE_ALT": "uk_UA",
    "CANONICAL": EN_URL,
    "TITLE": "AWG to Amps Chart &amp; Wire Gauge Ampacity Calculator",
    "OG_TITLE": "AWG to Amps Chart &amp; Wire Gauge Ampacity Calculator",
    "DESC": "AWG to amps chart for 30–0 AWG copper wire: real mm² cross-section, "
    "60 °C and 200 °C ampacity, plus a free calculator for strands, derating and voltage drop.",
    "OG_IMAGE": f"{BASE}/og-awg-to-amps.png",
    "OG_IMAGE_ALT": "AWG to amps chart and wire gauge ampacity calculator",
    "HOME_HREF": "/",
    "BRAND": "AWG / AMPACITY",
    "TOPBAR_META": "Flexible tinned copper · silicone insulation",
    "TOPBAR_SIGNAL": "reference build",
    "LANG_NAV_LABEL": "Language",
    "LANG_LINKS": '<span aria-current="true" lang="en">EN</span>'
    '<a href="/uk/awg-to-amps" hreflang="uk" lang="uk">УК</a>',
    "BREADCRUMB_LABEL": "Breadcrumb",
    "BC_HOME": "66ton99.org.ua",
    "BC_CURRENT": "AWG to amps",
    "EYEBROW": "Wire sizing / 30—0 AWG · copper",
    "H1": "AWG to amps chart &amp; calculator",
    "HERO_P": "A working reference for flexible, fine-stranded lead wire, from 30 AWG to 0 AWG. Read "
    "current capacity by real conductor cross-section in mm², then use the calculator to check a custom "
    "strand construction, conductor material, insulation temperature rating, bundle derating and voltage "
    "drop on DC or AC.",
    "MAP_ALT": "Abstract diagram of conductors and thermal paths",
    "MAP_CAPTION": "conductors / thermal path",
    "LAYOUT_LABEL": "AWG chart and wire gauge calculator",
    "KICKER_TABLE": "Reference table",
    "H2_TABLE": "AWG → copper area → ampacity",
    "P_TABLE": "Power sizes from 30 AWG through 0 AWG, including the 4 AWG / 25 mm² market-label case. "
    "Select any gauge to load a representative 0.08 mm fine-strand construction into the calculator.",
    "COUNT": "17 gauges",
    "TABLE_CAPTION": "AWG to amps: copper cross-section in mm², reference ampacity at 60 °C and 200 °C, conductor resistance and the maximum run at 3% voltage drop, for DC or AC",
    "TH_GAUGE": "Gauge",
    "TH_AREA": "Nominal copper",
    "TH_BUNDLE": "≤3 conductors",
    "TH_SINGLE": "1 conductor",
    "TH_R": "Resistance",
    "TH_LEN": "Max run",
    "TH_POWER": "Max load",
    "U_R_DC": "mΩ/m · DC",
    "U_LEN_DC": "m @3% · 24 V DC",
    "U_POWER_DC": "at 24 V DC",
    "U_MM2": "mm²",
    "U_60": "60°C / A",
    "U_200": "200°C / A",
    "U_FREE": "free air / A",
    "TABLE_NOTE": "<strong>Conditions:</strong> copper lead wire, 30°C ambient. The 60°C columns are the "
    "conservative everyday reference. The 200°C columns are high-temperature conductor limits, not "
    "touch-safe or connector-safe operating targets. More than three conductors require further derating. "
    "AWG 24–30 rows are indicative for fine-stranded silicone wire and must be checked against the exact "
    "cable datasheet.",
    "MATERIALS": material_json("en"),
    "DEFAULT_MATERIAL": DEFAULT_MATERIAL,
    "INSULATIONS": insulation_json("en"),
    "INSULATION_OPTIONS": insulation_options("en"),
    "INSULATION_LABEL": "Insulation",
    "TEMP_LABEL": "°C",
    "INSULATION_NOTE": "<strong>Silicone, 200 °C.</strong> Conductor rating 200 °C, ampacity ×1.000 against the published silicone data.",

    "MATERIAL_OPTIONS": material_options("en"),
    "MATERIAL_LABEL": "Conductor material",
    "IACS_LABEL": "% IACS",
    "MATERIAL_NOTE_DEFAULT": "<strong>Copper, tinned.</strong> 96% IACS, ρ = 0.01823 Ω·mm²/m, "
    "ampacity ×0.98 against annealed copper.",
    "MODE_VOLTAGE": "{ dc: 24, ac1: 120, ac3: 208 }",
    "DEF_FREQ": "60",
    "MODE_LEGEND": "Current type",
    "MODE_DC": "DC",
    "MODE_AC1": "AC 1-phase",
    "MODE_AC3": "AC 3-phase",
    "MODE_NOTE_DC": "<strong>Direct current.</strong> Voltage drop is counted over the full loop, out and back.",
    "TABLE_MODE_DC": "These figures are for direct current.",
    "L_FREQ": "Frequency / Hz",
    "L_PF": "Power factor cos \u03c6",
    "D_SKIN": "Skin effect",
    "SCROLL_HINT": "Scroll the table sideways for resistance and maximum run →",
    "KICKER_CALC": "Live calculation",
    "H2_CALC": "Wire gauge calculator",
    "P_CALC": "Count strands, enter their diameter, and get the ampacity of that exact cross-section at both "
    "temperature references — interpolated between the table rows, not rounded to one.",
    "L_STRANDS": "Strand count",
    "L_DIAM": "Strand diameter / mm",
    "L_INSTALL": "Installation / grouping",
    "INSTALL_OPTIONS": build_options(
        {
            "bundle": "Up to 3 current-carrying conductors in cable",
            "free": "Single conductor in free air",
            "4-6": "4–6 conductors / 80% derating",
            "7-9": "7–9 conductors / 70% derating",
            "10-20": "10–20 conductors / 50% derating",
            "21-30": "21–30 conductors / 45% derating",
            "31-40": "31–40 conductors / 40% derating",
            "41-plus": "41+ conductors / 35% derating",
        }
    ),
    "OPT_TITLE": "Optional checks",
    "OPT_NOTE": "Defaults: 24 V · 2 m · 35 A · 30°C · 60 Hz",
    "OPTIONAL": "optional",
    "L_VOLT": "System voltage / V",
    "L_LEN": "One-way length / m",
    "L_LOAD": "Load current / A",
    "L_AMB": "Ambient / °C",
    "BTN_CALC": "Calculate",
    "BTN_COPY": "Copy link",
    "BTN_RESET": "Reset",
    "RESULTS_TITLE": "Result / system readout",
    "M_AREA": "Calculated area",
    "M_GAUGE": "Equivalent gauge",
    "SHARED_CTX": "up to 3 in cable · 30°C ambient",
    "AMP_GRID_LABEL": "Ampacity by conductor temperature reference",
    "C_NORMAL": "Normal design",
    "C_HIGH": "High-temperature limit",
    "CTX_60": "60°C conductor",
    "CTX_200": "200°C conductor",
    "D_DROP": "Voltage drop",
    "D_PCT": "Drop percentage",
    "D_LOSS": "Wire loss",
    "MSG_START": "Enter the real conductor construction to start.",
    "SOURCE_NOTE": 'Small-gauge entries are cross-checked against <a '
    'href="https://www.amphenol.co.jp/military/techinfo/CurrentCarryingCapacity.html" target="_blank" '
    'rel="noopener noreferrer">Amphenol Japan cable current-capacity data</a>. AWG areas follow <a '
    'href="https://store.astm.org/b0258-18r26.html" target="_blank" rel="noopener noreferrer">ASTM '
    "B258</a>. Final sizing must follow the exact wire, terminal, fuse, enclosure, and local-code "
    "requirements.",
    "CONTENT": EN_CONTENT,
    "QUICKNAV_TITLE": "On this page",
    "QUICKNAV": quicknav(
        [
            ("#chart", "AWG to amps chart"),
            ("#calculator", "Wire gauge calculator"),
            ("#how-to-read", "How to read the chart"),
            ("#how-it-works", "How the calculator works"),
            ("#materials", "Conductor materials"),
            ("#insulation", "Insulation"),
            ("#conversions", "AWG to mm² conversions"),
            ("#faq", "Frequently asked questions"),
            ("#source", "Read the source"),
            ("/uk/awg-to-amps", "Українська версія"),
        ]
    ),
    "FOOTER_L": "AWG / AMPACITY — technical reference",
    "FOOTER_R": "Not a substitute for a manufacturer datasheet or electrical code.",
    "I18N": json.dumps(
        {
            "uArea": "mm²",
            "copied": "Copied",
            "customMaterial": "Custom",
            "customInsulation": "Custom",
            "insulationNote": "<strong>{name}, {c} °C.</strong> Conductor rating {c} °C, ampacity ×{factor} against the published 200 °C silicone data.",
            "materialNote": "<strong>{name}.</strong> {iacs}% IACS, ρ = {rho} Ω·mm²/m, ampacity ×{factor} against annealed copper.",
            "unitHighTemp": "°C / A",
            "uHz": "Hz",
            "unitResistDc": "mΩ/m · DC",
            "modeTag": {
                "dc": "DC",
                "ac1": "1φ",
                "ac3": "3φ",
            },
            "unitResistAc": "mΩ/m · {f} Hz",
            "unitLength": "m @3% · {u} V {m}",
            "unitPower": "at {u} V {m}",
            "uKilowatt": "kW",
            "labelSystemVoltage": "System voltage / V",
            "labelLineVoltage": "Line voltage / V",
            "modeShort": {
                "dc": "DC",
                "ac1": "AC 1-phase",
                "ac3": "AC 3-phase",
            },
            "modeNote": {
                "dc": "<strong>Direct current.</strong> Voltage drop is counted over the full loop, "
                "out and back.",
                "ac1": "<strong>Single-phase AC.</strong> Two loaded conductors, same as DC, so the only difference is skin and proximity loss: 0.43% on 0 AWG at 60 Hz, 0.07% at 4 AWG, nothing measurable below that. Raise the frequency to see it — 0 AWG loses 8% by 400 Hz.",
                "ac3": "<strong>Three-phase AC.</strong> Three current-carrying conductors share the cable, so the in-cable columns carry the IEC 60364-5-52 factor of 0.915 against the 2-conductor case. Drop is √3·I·R·L line-to-line over the one-way run.",
            },
            "tableModeNote": {
                "dc": "These figures are for direct current.",
                "ac1": "Single-phase has two loaded conductors, exactly like DC, so no conductor-count derate applies. Only skin and proximity loss separate the two, and at 60 Hz that is 0.43% on 0 AWG and less than 0.07% below 4 AWG — which is why most rows read identically to DC.",
                "ac3": "The in-cable columns carry the IEC 60364-5-52 factor of 0.915 for three loaded "
                "conductors instead of two. The free-air columns describe a single isolated conductor "
                "and are unchanged.",
            },
            "msgSkinRange": "Above roughly 1 kHz on the largest gauges the skin-effect fit leaves its "
            "validated range, so treat the AC resistance as indicative only.",
            "uAmp": "A",
            "uVolt": "V",
            "uWatt": "W",
            "below30": "below 30 AWG",
            "below0": "below 0 AWG",
            "instFree": "single conductor / free air",
            "instBundle": "up to 3 in cable",
            "conductorSuffix": "°C conductor",
            "ambientDefault": "30°C ambient default",
            "ambientSuffix": "°C ambient",
            "noMargin": "No margin",
            "stDanger": "Thermal margin required",
            "stReady": "Ampacity ready",
            "stAboveBoth": "Above both references",
            "stAbove60": "Above 60°C reference",
            "stWithin": "Within both references",
            "msgDanger": "The selected ambient exceeds one of the reference ranges. Review both "
            "temperature results before choosing a lower thermal target or a different wire system.",
            "msgReady": "Ampacity is calculated. Add the optional load current, system voltage, and "
            "one-way length to check load margin and voltage drop.",
            "msgAboveBoth": "<strong>{i} A</strong> is above both the 60°C reference of "
            "<strong>{a60} A</strong> and the 200°C reference of <strong>{a200} A</strong>. Increase the "
            "conductor size, improve cooling, or reduce the load.",
            "msgAbove60": "<strong>{i} A</strong> is above the conservative 60°C reference of "
            "<strong>{a60} A</strong>, but within the 200°C limit of <strong>{a200} A</strong>. Confirm "
            "the actual wire, terminal, fuse, enclosure, and local-code limits before use.",
            "msgWithin": "<strong>{i} A</strong> is within both temperature references. The 60°C value "
            "remains the conservative everyday design baseline; confirm the terminal, fuse, enclosure, "
            "and manufacturer limits before final use.",
        },
        ensure_ascii=False,
        indent=None,
    ),
}

# --------------------------------------------------------------------------
# UKRAINIAN
# --------------------------------------------------------------------------

UK_FAQ = [
    (
        "Скільки ампер витримує дріт кожного розміру AWG?",
        "<p>Для лудженої мідної жили за температури довкілля 30&nbsp;°C консервативна колонка 60&nbsp;°C "
        "у таблиці вище дає приблизно 7,8&nbsp;А для 18&nbsp;AWG, 13,7&nbsp;А для 14&nbsp;AWG, "
        "25,5&nbsp;А для 10&nbsp;AWG, 34,3&nbsp;А для 8&nbsp;AWG, 60,7&nbsp;А для 4&nbsp;AWG і "
        "109,7&nbsp;А для 0&nbsp;AWG за "
        "умови до трьох струмопровідних жил у кабелі. Одинарний провідник у вільному повітрі охолоджується "
        "краще й витримує більше. Силіконовий дріт із робочою температурою 200&nbsp;°C витримує приблизно "
        "вдвічі більше, але лише якщо кожна клема, запобіжник і конектор у колі також розраховані на таку "
        "температуру.</p>",
    ),
    (
        "Чим відрізняються колонки 60&nbsp;°C і 200&nbsp;°C?",
        "<p>Обидві описують ту саму мідь. Різниця в тому, наскільки сильно ви дозволяєте провіднику "
        "нагрітися. Колонки 60&nbsp;°C — це щоденна проєктна база: дріт залишається безпечним на дотик, а "
        "ізоляція, клеми та сусідні матеріали працюють у комфортному режимі. Колонки 200&nbsp;°C — це "
        "тепловий ліміт самої силіконової ізоляції, тобто струм, за якого провідник досягає 200&nbsp;°C. "
        "Друге число — це стеля для коротких добре провітрюваних ділянок, а не проєктна ціль.</p>",
    ),
    (
        "Як перевести AWG у мм²?",
        "<p>AWG — логарифмічна шкала, тому тут працює формула, а не проста пропорція. Діаметр провідника в "
        "міліметрах: <em>d</em>&nbsp;=&nbsp;0,127&nbsp;×&nbsp;92<sup>(36−AWG)/39</sup>, а переріз — "
        "<em>A</em>&nbsp;=&nbsp;π&nbsp;<em>d</em>²/4. На практиці кожні три кроки AWG приблизно подвоюють "
        "площу міді, а шість кроків — діаметр. Колонка мм² у таблиці вже містить номінальні значення за "
        "ASTM&nbsp;B258, тож переведення можна зчитати просто з таблиці.</p>",
    ),
    (
        "Чому дріт 25&nbsp;мм² продають як 4&nbsp;AWG?",
        "<p>Бо це маркетингове маркування, а не вимір. Справжній 4&nbsp;AWG — це 21,15&nbsp;мм² міді. "
        "Продавці гнучкого силіконового дроту часто округлюють до найближчого метричного розміру або "
        "вказують зовнішній діаметр по ізоляції замість перерізу жили. Завжди рахуйте за кількістю жилок і "
        "діаметром жилки з даташита — саме це просить калькулятор на цій сторінці — і вважайте заявлену "
        "цифру мм² неперевіреною, доки вона не збіжиться.</p>",
    ),
    (
        "Чи збільшує більша кількість жилок допустимий струм?",
        "<p>Сама собою — ні. Допустимий струм визначається сумарним перерізом міді, тому 1650 жилок по "
        "0,08&nbsp;мм пропускають той самий струм, що й суцільний провідник такої ж площі. Тонке "
        "багатожильне плетіння дає гнучкість, стійкість до вібрації та згинів і зручність прокладання у "
        "тісних корпусах. На постійному струмі та мережевих частотах скін-ефект на цих перерізах "
        "знехтуваний, тож приросту струму багатожильність не дає.</p>",
    ),
    (
        "Як порахувати падіння напруги на постійному струмі?",
        "<p>Падіння напруги — це струм навантаження, помножений на опір усього кола, туди й назад. За "
        "питомого опору міді ρ&nbsp;=&nbsp;0,0175&nbsp;Ом·мм²/м падіння дорівнює "
        "ΔU&nbsp;=&nbsp;<em>I</em>&nbsp;×&nbsp;ρ&nbsp;×&nbsp;2<em>L</em>&nbsp;/&nbsp;<em>A</em>, де "
        "<em>L</em> — довжина траси в один бік. Більшість низьковольтних систем постійного струму тримають "
        "падіння в межах 3&nbsp;% від напруги живлення; для кола 12&nbsp;В це лише 0,36&nbsp;В — саме тому "
        "довгі 12-вольтові траси зазвичай рахують за падінням напруги, а не за допустимим струмом.</p>",
    ),
    (
        "Наскільки знижувати струм для жил у пучку?",
        "<p>Пучок затримує тепло, тож кожна жила в групі витримує менше. Типові коефіцієнти: 80&nbsp;% для "
        "4–6 струмопровідних жил, 70&nbsp;% для 7–9, 50&nbsp;% для 10–20, 45&nbsp;% для 21–30, 40&nbsp;% "
        "для 31–40 і 35&nbsp;% далі. Температура довкілля знижує струм додатково, і два коефіцієнти "
        "перемножуються. Жили, що ніколи не працюють одночасно, а також нейтралі у збалансованому колі, "
        "зазвичай до групи не зараховуються.</p>",
    ),
    (
        "Чи можна користуватися цією таблицею для алюмінієвого дроту?",
        "<p>Так — перемкніть матеріал жили, і всі колонки перерахуються. Алюміній із провідністю "
        "61,2&nbsp;% IACS несе близько 78&nbsp;% струму міді того самого перерізу, бо допустимий струм "
        "змінюється як корінь із провідності. Тому щоб зрівнятися з мідною жилою, потрібно у 1,64 раза "
        "більше площі — приблизно два кроки AWG угору. Арифметика тут найпростіше: алюміній тече під "
        "тиском затиску, окислюється на повітрі й розширюється від нагріву сильніше за мідь, тож потребує "
        "клем, сертифікованих для алюмінію, антиоксидної пасти й динамометричного ключа. Мідно-алюмінієвий "
        "провід поводиться електрично так само, але з'єднується як мідь, а мідно-сталевий із 30&nbsp;% "
        "IACS призначений для міцності та високих частот, а не для потужності.</p>",
    ),
    (
        "Чи змінюється допустимий струм між постійним і змінним струмом?",
        "<p>На мережевій частоті — практично ні. Змінний струм витісняється до поверхні жили, але "
        "глибина скін-шару в міді становить близько 9,4&nbsp;мм на 50&nbsp;Гц і 8,5&nbsp;мм на "
        "60&nbsp;Гц, тоді як жила 0&nbsp;AWG має радіус лише 4,1&nbsp;мм. За IEC&nbsp;60287 приріст "
        "опору виходить 0,08&nbsp;% для 0&nbsp;AWG і менше за 0,01&nbsp;% для всього, тоншого за "
        "4&nbsp;AWG, тож та сама таблиця слугує і для постійного, і для однофазного, і для "
        "трифазного струму. Рід струму справді змінює падіння напруги: дві жили туди й назад для "
        "постійного та однофазного, √3 між лініями для трифазного, плюс cos&nbsp;φ. Скін-ефект варто "
        "рахувати лише від сотень герців — тому калькулятор і питає частоту.</p>",
    ),
    (
        "Чи це те саме, що допустимі струми за NEC або IEC?",
        "<p>Ні. Це довідник для гнучкого тонкожильного лудженого мідного дроту з силіконовою ізоляцією — "
        "того, що використовують у внутрішньому монтажі обладнання, акумуляторних перемичках, робототехніці "
        "та RC-моделях. Стаціонарні електроустановки регулюються таблицями NEC&nbsp;310 у Північній Америці "
        "та IEC&nbsp;60364-5-52 у Європі, які виходять з іншої ізоляції, способів прокладання та "
        "поправкових коефіцієнтів. Для стаціонарної проводки користуйтеся нормами, а цю таблицю "
        "застосовуйте для монтажу обладнання.</p>",
    ),
]

UK_CONTENT = f"""            <section id="how-to-read">
              <h2>Як читати цю таблицю AWG в ампери</h2>
              <p>
                Кожен рядок поєднує розмір за American Wire Gauge із номінальним перерізом міді, який він
                насправді містить, у мм², і з чотирма значеннями допустимого струму. Сам номер калібру не
                каже нічого про те, який струм витримає дріт — це визначає площа міді, і саме тому колонка
                мм² стоїть другою, одразу біля калібру.
              </p>

              <h3>Площа міді, а не зовнішній діаметр</h3>
              <p>
                Гнучкий силіконовий дріт значно частіше продають за зовнішнім діаметром, ніж за перерізом
                жили. Кабель, заявлений як 8&nbsp;AWG, може мати 8&nbsp;мм по оболонці й ледве 6&nbsp;мм²
                міді. Рахуйте за кількістю жилок і діаметром жилки з даташита, а потім звіряйте отриману
                площу з таблицею. Калькулятор вище виконує саме цю арифметику.
              </p>

              <h3>Колонки 60&nbsp;°C і 200&nbsp;°C</h3>
              <p>
                Колонки 60&nbsp;°C — консервативний щоденний орієнтир: провідник залишається холодним, клеми
                працюють у межах власних характеристик, а на спекотний день є запас. Колонки 200&nbsp;°C —
                тепловий ліміт силіконової ізоляції, а не проєктна ціль. Провідник, який працює на межі
                200&nbsp;°C, розплавить термоусадку, змінить колір клем і обпече шкіру при дотику, тож
                використовуйте це число лише щоб розуміти наявний запас, а не як розрахункове.
              </p>

              <h3>Максимальна потужність — тут рід струму й видно</h3>
              <p>
                Колонки допустимого струму — в амперах, і ампер є ампер: провіднику байдуже, від постійного
                чи змінного струму він нагрівся. Повністю змінюється те, чого ці ампери <em>варті</em>. Та
                сама жила 0&nbsp;AWG на своїх 109,7&nbsp;А віддає <strong>2,6&nbsp;кВт</strong> у системі
                24&nbsp;В постійного струму, <strong>25&nbsp;кВт</strong> на 230&nbsp;В однофазних і
                <strong>76&nbsp;кВт</strong> на 400&nbsp;В трифазних — різниця у двадцять дев'ять разів,
                лише за рахунок напруги та √3.
              </p>
              <p>
                У зворотний бік це саме те число, яке більшості й потрібне: для однакового навантаження
                струм, який доведеться нести, кардинально різний для постійного та змінного струму, а мідь
                добирається за струмом, а не за ватами. Навантаження 3&nbsp;кВт — це 125&nbsp;А за
                24&nbsp;В постійного струму і 4,3&nbsp;А за 400&nbsp;В трифазних.
              </p>

              <h3>Опір і максимальна траса</h3>
              <p>
                Дві останні колонки найсильніше залежать від перемикача роду струму. Опір — це ρ/<em>A</em>
                на метр, який для змінного струму перераховується на обрану частоту. Максимальна траса — це
                найбільша довжина в один бік, за якої падіння лишається в межах 3&nbsp;%, коли жила несе свій
                струм для «≤3 жили» за 60&nbsp;°C і напруги, заданої в калькуляторі.
              </p>
              <p>
                На цю колонку варто подивитись уважно. Та сама жила 0&nbsp;AWG придатна для
                <strong>9,6&nbsp;м</strong> у системі 24&nbsp;В постійного струму і <strong>185&nbsp;м</strong>
                у трифазній 400&nbsp;В — різниця в дев'ятнадцять разів, лише за рахунок напруги та √3, за
                абсолютно незмінної міді. Довгу трасу рідко обмежує допустимий струм; її обмежує падіння напруги.
              </p>

              <h3>Пучок проти вільного повітря</h3>
              <p>
                Одинарний провідник у нерухомому повітрі віддає тепло в усі боки. Той самий провідник
                усередині джгута ділить тепло із сусідами, і всі вони гріються сильніше. Колонки
                <strong>≤3 жили</strong> передбачають звичайний кабель або невеликий пучок; колонки
                <strong>вільне повітря</strong> — один провідник без нічого навколо. Понад три струмопровідні
                жили потребують додаткових коефіцієнтів групування з калькулятора.
              </p>
            </section>

            <section id="how-it-works">
              <h2>Як працює калькулятор перерізу дроту</h2>
              <p>
                Калькулятор відштовхується від фізичної конструкції дроту, а не від його маркування, і
                проходить ті самі чотири кроки, що й інженер.
              </p>

              <h3>1. Переріз за кількістю жилок</h3>
              <p class="formula"><span>Площа міді</span>A = n × π × d² / 4</p>
              <p>
                <strong>n</strong> — кількість жилок, <strong>d</strong> — діаметр однієї жилки в
                міліметрах. Типовий силіконовий провід «4&nbsp;AWG» із 1650 жилок по 0,08&nbsp;мм дає
                8,29&nbsp;мм² — істотно менше за 21,15&nbsp;мм² справжнього 4&nbsp;AWG, і саме такі
                розбіжності ця сторінка й покликана виявляти.
              </p>

              <h3>2. Еквівалентний калібр AWG</h3>
              <p class="formula"><span>Калібр із площі</span>AWG = 36 − 39 × log(d<sub>eq</sub> / 0,127) / log(92)</p>
              <p>
                Площа переводиться назад в еквівалентний суцільний діаметр, а потім у номер за шкалою AWG.
                Результат зазвичай дробовий, і це чесно: реальний багатожильний дріт рідко потрапляє точно в
                калібр.
              </p>

              <h3>3. Поправки на температуру та групування</h3>
              <p class="formula"><span>Знижений струм</span>I = I<sub>баз</sub> × k<sub>темп</sub> × k<sub>груп</sub></p>
              <p>
                Базовий струм рахується для вашого перерізу, а не береться з найближчого рядка: між двома
                табличними калібрами струм змінюється за степеневим законом від площі,
                <em>I</em>&nbsp;∝&nbsp;<em>A</em><sup>k</sup>, де <em>k</em> береться із самої пари рядків —
                тут це 0,5–0,7, бо тепло приходить через переріз, а йде через поверхню. Якщо переріз точно
                збігається з калібром, повертається опубліковане число. Температурний коефіцієнт інтерполюється
                між опублікованими точками корекції: провідники на 60&nbsp;°C швидко втрачають запас вище
                30&nbsp;°C, тоді як провідники на 200&nbsp;°C зберігають працездатність глибоко в зоні
                високих температур. Коефіцієнт групування береться з селектора прокладання, і обидва
                перемножуються.
              </p>

              <h3>4. Падіння напруги та втрати в дроті</h3>
              <p class="formula"><span>Постійний і однофазний змінний</span>ΔU = 2 × I × R × L × cos φ<span
                style="margin-top:10px">Трифазний змінний, між лініями</span>ΔU = √3 × I × R × L × cos φ</p>
              <p>
                <em>R</em> — опір одного метра, ρ/<em>A</em>, де ρ&nbsp;=&nbsp;0,0175&nbsp;Ом·мм²/м для міді
                за 20&nbsp;°C, а <em>L</em> — довжина траси в один бік. Постійний і однофазний змінний струм
                ідуть туди й назад, тому довжина враховується двічі. Трифазне коло — ні: у падінні між
                лініями замість двійки стоїть √3. Для постійного струму cos&nbsp;φ дорівнює одиниці, тому
                перша формула зводиться до звичного 2<em>IRL</em>.
              </p>
              <p>
                Потужність, втрачена як тепло, дорівнює <em>I</em>²<em>R</em> на кожну жилу — дві жили для
                постійного та однофазного струму, три для трифазного. У низьковольтних системах саме це, а
                не допустимий струм, зазвичай змушує брати товщий провідник: коло 12&nbsp;В допускає лише
                0,36&nbsp;В падіння за поширеної норми 3&nbsp;%.
              </p>
              <p>
                Реактивний опір не враховано. Для перерізів і довжин, про які йдеться на цій сторінці, він
                менший за невизначеність самого активного опору, але на довгих трифазних трасах у трубі він
                перестає бути знехтуваним — там рахуйте за published R і X конкретного кабелю.
              </p>

              <h3>5. Чому трифаза знижує струм, а частота — здебільшого ні</h3>
              <p>
                Тут діють дві різні причини, і за величиною вони незіставні.
              </p>
              <p>
                <strong>Кількість жил — головна.</strong> Трифазне коло має в кабелі три струмопровідні
                жили там, де постійне й однофазне мають дві. Три жили, кожна з яких виділяє
                <em>I</em>²<em>R</em>, дають у півтора раза більше тепла в тому самому пучку, тож кожна має
                нести менше. IEC&nbsp;60364-5-52 подає це окремими колонками <em>2 навантажені жили</em> та
                <em>3 навантажені жили</em>; по мідних таблицях це відношення в середньому дорівнює
                <strong>0,915</strong> — саме цей коефіцієнт застосовано тут до колонок «у кабелі». Він не
                залежить від частоти й дає зниження приблизно на 9&nbsp;%: тому 0&nbsp;AWG показує
                109,7&nbsp;А для постійного струму і 100,4&nbsp;А для трифазного. Колонки вільного повітря
                описують одну ізольовану жилу — той самий об'єкт у будь-якому режимі, тож вони не
                змінюються.
              </p>
              <p>
                <strong>Частота — другорядна</strong>, принаймні на мережевій. Змінний струм витісняється до
                поверхні жили, тож опір зростає, але в міді на 50&nbsp;Гц глибина скін-шару становить
                близько 9,4&nbsp;мм, тоді як навіть жила 0&nbsp;AWG має радіус лише 4,1&nbsp;мм.
              </p>
              <p class="formula"><span>Скін-ефект і ефект близькості, IEC 60287-1-1</span>y<sub>s</sub> = x<sub>s</sub>⁴ / (192 + 0,8 x<sub>s</sub>⁴)<span style="margin-top:10px">y<sub>p</sub> = y<sub>s</sub> (d/s)² [0,312 (d/s)² + 1,18 / (y<sub>s</sub> + 0,27)]</span></p>
              <p>
                Враховано обидва ефекти — скін-ефект і ефект близькості сусідніх жил, який переважає одразу
                поза мережевою частотою. Разом вони дають <strong>0,28&nbsp;%</strong> на 50&nbsp;Гц для
                0&nbsp;AWG, 0,04&nbsp;% для 4&nbsp;AWG і нічого вимірного для тоншого. Це і є вся різниця
                між постійним і однофазним змінним струмом тут: обидва мають дві навантажені жили, а в
                неброньованого низьковольтного дроту немає ані втрат в оболонці, ані діелектричних. У
                таблиці показано десяткову частку, щоб цю різницю було видно там, де вона є — 0&nbsp;AWG
                переходить зі 109,7&nbsp;А на 109,6&nbsp;А — і щоб рядки читались однаково там, де вона
                справді нульова. Допустимий струм
                масштабується як 1/√(1+y<sub>s</sub>), тобто змінюється менш ніж на десяту частку відсотка —
                значно менше за розбіжність між даташитами двох виробників. Тож сама лише частота не виправдала б окремої колонки для
                змінного струму; її виправдовує кількість жил.
              </p>
              <p>
                Вище за частотою це вже важить. На 400&nbsp;Гц — авіація та деякі приводи — 0&nbsp;AWG
                додає 17&nbsp;%, і саме тому калькулятор питає частоту, а не припускає мережеву. Формула
                чинна до x<sub>s</sub>&nbsp;≤&nbsp;2,8, тобто приблизно до 1&nbsp;кГц на найбільшому калібрі;
                вище калькулятор сам позначає результат як орієнтовний.
              </p>
            </section>

            <section id="materials">
              <h2>Матеріали жили</h2>
              <p>
                AWG — це геометричний розмір, тож переріз у таблиці однаковий для будь-якого металу.
                Змінюється те, який струм цей переріз витримає і скільки напруги на ньому впаде. Обидва
                випливають з одного числа — питомої провідності за шкалою IACS, де відпалена мідь дорівнює
                100&nbsp;%.
              </p>
              <p class="formula"><span>Струм відносно міді</span>I / I<sub>Cu</sub> = √(σ / σ<sub>Cu</sub>)<span
                style="margin-top:10px">Опір відносно міді</span>R / R<sub>Cu</sub> = σ<sub>Cu</sub> / σ</p>
              <p>
                Однакова геометрія й однаковий допустимий перегрів означають, що <em>I</em>²<em>R</em>
                фіксоване, тож струм змінюється як обернений корінь із питомого опору. Це не емпіричне
                правило: за NEC&nbsp;310.16 відношення алюмінію до міді в середньому становить
                <strong>0,774</strong> від 6&nbsp;AWG до 4/0, тоді як √0,612 передбачає
                <strong>0,782</strong>.
              </p>

              <h3>Що пропонує селектор</h3>
              <dl class="conv-list">
                <div><dt>Мідь</dt><dd>100% IACS · ×1,000</dd></div>
                <div><dt>Срібло</dt><dd>105% IACS · ×1,025</dd></div>
                <div><dt>Луджена мідь</dt><dd>96% IACS · ×0,980</dd></div>
                <div><dt>Нікельована</dt><dd>95% IACS · ×0,975</dd></div>
                <div><dt>Алюміній 1350</dt><dd>61,2% IACS · ×0,782</dd></div>
                <div><dt>Сплав 8000</dt><dd>61% IACS · ×0,781</dd></div>
                <div><dt>Мідно-алюмінієвий</dt><dd>61,5% IACS · ×0,784</dd></div>
                <div><dt>Мідно-сталевий</dt><dd>30% IACS · ×0,548</dd></div>
              </dl>
              <p>
                Усе інше вводиться як власний відсоток IACS — це чесний спосіб врахувати даташит, який подає
                власну цифру.
              </p>

              <h3>Покриття міді</h3>
              <p>
                Покриття потрібне заради середовища, а не заради провідності. Олово захищає від корозії й
                зберігає змочуваність припоєм; нікель витримує понад 200&nbsp;°C, де олово давно розплавилось
                би; срібло — для високих частот, де струм іде поверхнею. Втрата невелика й залежить від
                товщини шару відносно жилки: на жилці 0,08&nbsp;мм мікрон олова займає близько 5&nbsp;% площі
                й проводить на рівні 15&nbsp;% від міді — звідси й береться 96&nbsp;%. На товщих жилках менше.
                Срібне покриття на опорі постійному струму практично не позначається, бо основа лишається
                мідною.
              </p>

              <h3>Алюміній і чого він коштує</h3>
              <p>
                Алюміній несе близько 78&nbsp;% струму міді того самого розміру, тож щоб зрівнятися з мідною
                жилою, потрібно <strong>у 1,64 раза більше площі — приблизно два кроки AWG угору</strong>. На
                довгих трасах він однаково вигідний: за однакової провідності важить близько третини й коштує
                значно менше.
              </p>
              <p>
                Проблема ніколи не в металі — вона в з'єднанні. Алюміній тече під тиском затиску, тож клема,
                затягнута торік, сьогодні може бути слабкою; він миттєво вкривається ізолювальним оксидом на
                повітрі; і розширюється від нагріву приблизно на 40&nbsp;% сильніше за мідь, розхитуючи себе
                кожним циклом нагрівання. Алюмінієва проводка в житлових колах заробила свою репутацію в
                1960–70-х саме через це. Використовуйте клеми, сертифіковані для алюмінію, наносьте
                антиоксидну пасту, затягуйте моментом, зазначеним на з'єднувачі, і ніколи не з'єднуйте голий
                алюміній з голою міддю у вологому місці — гальванічна пара з'їдає алюміній.
              </p>
              <p>
                Тонкожильний силіконовий дріт, про який ця сторінка здебільшого й розповідає, з алюмінію не
                роблять: він не витримує циклів згинання.
              </p>

              <h3>Біметалеві жили</h3>
              <p>
                Мідно-алюмінієвий провід (CCA) — це алюміній у мідній оболонці, зазвичай 10&nbsp;% за
                об'ємом. Він з'єднується як мідь, а проводить як алюміній, і це прийнятний компроміс — біда в
                тому, що його часто продають <em>як</em> мідь. Зачистіть зразок: осердя буде сріблястим.
                Мідно-сталевий (CCS) — зовсім інша річ, 30&nbsp;% IACS, зроблений заради механічної міцності
                та поверхневої провідності на високих частотах, а не заради потужності; магніт визначає його
                миттєво.
              </p>

              <h3>Одне застереження щодо температури</h3>
              <p>
                Усі числа тут наведено для 20&nbsp;°C. Жила, що реально працює за 60&nbsp;°C, має приблизно на
                16&nbsp;% більший опір, а температурний коефіцієнт алюмінію (0,00403/K) трохи гірший за мідний
                (0,00393/K). Для падіння напруги в гарячому колі додайте цей запас самостійно — калькулятор
                цього не робить, бо для цього потрібна температура жили, а не довкілля.
              </p>
            </section>

            <section id="insulation">
              <h2>Ізоляція</h2>
              <p>
                Ізоляція додає до допустимого струму одну річ: наскільки гарячою вона дозволить стати жилі.
                Міді байдуже — їй комфортно і за 400&nbsp;°C. Межу визначає пластик навколо, і саме це число
                рухає високотемпературну колонку таблиці.
              </p>
              <p class="formula"><span>Струм за іншої робочої температури</span>I / I<sub>200</sub> = √( (T−30) / (1 + α(T−20)) ) ÷ √( 170 / (1 + α·180) )</p>
              <p>
                Тепло відводиться пропорційно ΔT, а надходить як <em>I</em>²<em>R</em>, причому сам
                <em>R</em> зростає з температурою — тому виграш від вищої робочої температури менший, ніж
                здається спершу. За NEC&nbsp;310.16 формула передбачає відношення 90&nbsp;°C до 60&nbsp;°C
                як <strong>1,347</strong>, тоді як опубліковані колонки дають 1,333–1,360 для 10&nbsp;AWG і
                товщих. Силікон 200&nbsp;°C — еталон із коефіцієнтом рівно 1,000, тож його вибір відтворює
                опубліковані дані без змін.
              </p>

              <h3>Що пропонує селектор</h3>
              <dl class="conv-list">
                <div><dt>ПВХ</dt><dd>70 °C · ×0,579</dd></div>
                <div><dt>ПВХ/нейлон THHN</dt><dd>90 °C · ×0,687</dd></div>
                <div><dt>Зшитий ПЕ / EPR</dt><dd>90 °C · ×0,687</dd></div>
                <div><dt>ПВХ термостійкий</dt><dd>105 °C · ×0,751</dd></div>
                <div><dt>ETFE (Tefzel)</dt><dd>150 °C · ×0,893</dd></div>
                <div><dt>Силікон</dt><dd>180 °C · ×0,962</dd></div>
                <div><dt>Силікон, FEP</dt><dd>200 °C · ×1,000</dd></div>
                <div><dt>PTFE / PFA</dt><dd>260 °C · ×1,090</dd></div>
              </dl>

              <h3>Правило, на якому найчастіше помиляються</h3>
              <p>
                <strong>Усе коло працює за температурою свого найслабшого місця, і це майже ніколи не
                дріт.</strong> Клема автомата, сертифікована на 75&nbsp;°C, обмежує всю трасу 75&nbsp;°C
                незалежно від того, що написано на ізоляції — NEC&nbsp;110.14(C) прямо це фіксує, а більшість
                апаратів до 100&nbsp;А сертифіковані взагалі на 60&nbsp;°C. Купити силікон на 200&nbsp;°C,
                порахувати за його колонкою 200&nbsp;°C, а потім затиснути в наконечник на 75&nbsp;°C — це
                типовий шлях до згорілого з'єднання. Саме тому консервативна колонка 60&nbsp;°C у цій таблиці
                лишається незмінною, що б ви не обрали: для більшості реальних установок керує саме вона.
              </p>
              <p>
                Висока робоча температура дає запас у гарячому корпусі, живучість поруч із випуском чи
                нагрівачем і можливість нести повний струм, коли довкола вже 80&nbsp;°C. Вона не дає права
                проганяти більший струм через ті самі клеми.
              </p>

              <h3>Як обирати</h3>
              <p>
                <strong>ПВХ</strong> дешевий, стійкий до стирання й дубіє на морозі; розм'якшується там, де
                гаряче, і виділяє хлористий водень під час пожежі — тому в тунелях і на суднах його заміняють
                безгалогенні компаунди. <strong>Зшитий поліетилен</strong> — це той самий клас ціни, але
                краще тримає температуру й не тече. <strong>Силікон</strong> — найгнучкіший у списку з великим
                відривом і витримує 200&nbsp;°C, але легко ріжеться й протирається, тож потребує захисної
                трубки скрізь, де може тертися. <strong>PTFE і PFA</strong> найкращі електрично й термічно і
                байдужі майже до всіх розчинників — за кілька разів більшу ціну й помітно меншу гнучкість.
                <strong>ETFE</strong> — компроміс, на якому зупинилась авіація: тонка стінка, міцний,
                150&nbsp;°C.
              </p>

              <h3>Дві речі, яких тут не враховано</h3>
              <p>
                Товщина стінки. Товста оболонка — це тепловкривало, тож два кабелі на 90&nbsp;°C різної
                конструкції несуть різний струм. Даташити рідко подають товщину в порівнюваному вигляді, тож
                тут використано лише робочу температуру.
              </p>
              <p>
                Номінальна напруга — зовсім окрема властивість. Версії однієї ізоляції на 600&nbsp;В,
                1&nbsp;кВ і 3&nbsp;кВ мають однакову робочу температуру й різняться лише стінкою. Перевіряйте
                її окремо — ніщо на цій сторінці не каже, чи витримає ізоляція вашу напругу.
              </p>
            </section>

            <section id="conversions">
              <h2>AWG у мм² — коротко</h2>
              <p>
                Номінальні перерізи міді за ASTM&nbsp;B258 і найближчий метричний розмір кабелю, який ринок
                реально продає під кожним із них.
              </p>
{conv_html([
    ("0 AWG", "53,49 мм² · ≈ 50 мм²"),
    ("2 AWG", "33,62 мм² · ≈ 35 мм²"),
    ("4 AWG", "21,15 мм² · ≈ 25 мм²"),
    ("6 AWG", "13,30 мм² · ≈ 16 мм²"),
    ("8 AWG", "8,37 мм² · ≈ 10 мм²"),
    ("10 AWG", "5,26 мм² · ≈ 6 мм²"),
    ("12 AWG", "3,31 мм² · ≈ 4 мм²"),
    ("14 AWG", "2,08 мм² · ≈ 2,5 мм²"),
    ("16 AWG", "1,31 мм² · ≈ 1,5 мм²"),
    ("18 AWG", "0,823 мм² · ≈ 1 мм²"),
    ("20 AWG", "0,518 мм² · ≈ 0,5 мм²"),
    ("22 AWG", "0,326 мм² · ≈ 0,35 мм²"),
])}
              <p>
                Число праворуч — це розмір, який зазвичай називає постачальник. Воно майже завжди більше за
                справжню площу AWG, тож метричний кабель під виглядом AWG-еквівалента безпечний за струмом і
                оманливий за ціною міді.
              </p>
            </section>

            <section id="faq">
              <h2>Часті запитання</h2>
{faq_html(UK_FAQ)}
            </section>

            <section id="source">
              <h2>Подивитися код або виправити його</h2>
              <p>
                Ця сторінка з відкритим кодом. Дані таблиці, обидва переклади, калькулятор і цей
                текст створює один генератор — саме тому англійська та українська версії не можуть
                розійтися.
              </p>
              <ul>
                <li><strong>src/build.py</strong> — таблиця струмів, тексти, FAQ і розмітка JSON-LD</li>
                <li><strong>src/template.html</strong> — каркас сторінки та калькулятор</li>
                <li><strong>src/test.js</strong> — тести, що ганяють калькулятор на зібраних сторінках</li>
              </ul>
              <p>
                Помітили хибне число або хочете додати калібр? Створіть issue чи надішліть pull
                request на <a href="https://github.com/66Ton99/homepage" target="_blank"
                rel="noopener noreferrer">github.com/66Ton99/homepage</a>. Особливо вітаються
                виправлення з посиланням на даташит або стандарт — найменш надійні рядки AWG 24–30,
                бо вони орієнтовні для тонкожильного силіконового дроту, а не взяті з однієї
                авторитетної таблиці.
              </p>
            </section>"""

UK = {
    "LANG": "uk",
    "JS_LOCALE": "uk-UA",
    "OG_LOCALE": "uk_UA",
    "OG_LOCALE_ALT": "en_US",
    "CANONICAL": UK_URL,
    "TITLE": "Таблиця AWG в ампери та калькулятор перерізу дроту",
    "OG_TITLE": "Таблиця AWG в ампери та калькулятор перерізу дроту",
    "DESC": "Таблиця AWG в ампери для мідного дроту 30–0 AWG: реальний переріз у мм², струм за "
    "60 °C і 200 °C, калькулятор жилок, поправок на пучок і падіння напруги.",
    "OG_IMAGE": f"{BASE}/og-awg-to-amps-uk.png",
    "OG_IMAGE_ALT": "Таблиця AWG в ампери та калькулятор перерізу дроту",
    "HOME_HREF": "/uk",
    "BRAND": "AWG / АМПЕРИ",
    "TOPBAR_META": "Гнучка луджена мідь · силіконова ізоляція",
    "TOPBAR_SIGNAL": "довідкова збірка",
    "LANG_NAV_LABEL": "Мова",
    "LANG_LINKS": '<a href="/awg-to-amps" hreflang="en" lang="en">EN</a>'
    '<span aria-current="true" lang="uk">УК</span>',
    "BREADCRUMB_LABEL": "Навігаційний ланцюжок",
    "BC_HOME": "66ton99.org.ua",
    "BC_CURRENT": "AWG в ампери",
    "EYEBROW": "Переріз дроту / 30—0 AWG · мідь",
    "H1": "AWG в ампери: таблиця і калькулятор",
    "HERO_P": "Робочий довідник для гнучкого тонкожильного монтажного дроту, від 30 AWG до 0 AWG. "
    "Дивіться допустимий струм за реальним перерізом жили в мм², а потім перевіряйте в калькуляторі "
    "власну конструкцію жилок, матеріал жили, температурний клас ізоляції, поправку на пучок і падіння "
    "напруги на постійному чи змінному струмі.",
    "MAP_ALT": "Абстрактна схема провідників і шляхів тепловідведення",
    "MAP_CAPTION": "провідники / тепловий шлях",
    "LAYOUT_LABEL": "Таблиця AWG і калькулятор перерізу",
    "KICKER_TABLE": "Довідкова таблиця",
    "H2_TABLE": "AWG → переріз міді → струм",
    "P_TABLE": "Силові розміри від 30 AWG до 0 AWG, разом із ринковим випадком «4 AWG / 25 мм²». Оберіть "
    "будь-який калібр, щоб підставити типову конструкцію з жилок 0,08 мм у калькулятор.",
    "COUNT": "17 калібрів",
    "TABLE_CAPTION": "AWG в ампери: переріз міді в мм², довідковий допустимий струм за 60 °C і 200 °C, опір жили та максимальна траса за падіння 3%, для постійного або змінного струму",
    "TH_GAUGE": "Калібр",
    "TH_AREA": "Номінальна мідь",
    "TH_BUNDLE": "≤3 жили",
    "TH_SINGLE": "1 жила",
    "TH_R": "Опір",
    "TH_LEN": "Макс. траса",
    "TH_POWER": "Макс. потужність",
    "U_R_DC": "мОм/м · пост.",
    "U_LEN_DC": "м @3% · 24 В пост.",
    "U_POWER_DC": "на 24 В пост.",
    "U_MM2": "мм²",
    "U_60": "60°C / А",
    "U_200": "200°C / А",
    "U_FREE": "вільне повітря / А",
    "TABLE_NOTE": "<strong>Умови:</strong> мідний монтажний дріт, довкілля 30°C. Колонки 60°C — "
    "консервативний щоденний орієнтир. Колонки 200°C — граничні температури провідника, а не безпечні для "
    "дотику чи для клем робочі значення. Понад три жили потребують додаткового зниження струму. Рядки "
    "AWG 24–30 є орієнтовними для тонкожильного силіконового дроту й потребують звірки з даташитом "
    "конкретного кабелю.",
    "MATERIALS": material_json("uk"),
    "DEFAULT_MATERIAL": DEFAULT_MATERIAL,
    "INSULATIONS": insulation_json("uk"),
    "INSULATION_OPTIONS": insulation_options("uk"),
    "INSULATION_LABEL": "Ізоляція",
    "TEMP_LABEL": "°C",
    "INSULATION_NOTE": "<strong>Силікон, 200 °C.</strong> Робоча температура жили 200 °C, струм ×1,000 відносно опублікованих даних для силікону.",

    "MATERIAL_OPTIONS": material_options("uk"),
    "MATERIAL_LABEL": "Матеріал жили",
    "IACS_LABEL": "% IACS",
    "MATERIAL_NOTE_DEFAULT": "<strong>Мідь, луджена.</strong> 96% IACS, ρ = 0,01823 Ом·мм²/м, "
    "струм ×0,98 відносно відпаленої міді.",
    "MODE_VOLTAGE": "{ dc: 24, ac1: 230, ac3: 400 }",
    "DEF_FREQ": "50",
    "MODE_LEGEND": "\u0420\u0456\u0434 \u0441\u0442\u0440\u0443\u043c\u0443",
    "MODE_DC": "\u041f\u043e\u0441\u0442\u0456\u0439\u043d\u0438\u0439",
    "MODE_AC1": "\u0417\u043c\u0456\u043d\u043d\u0438\u0439 1\u0444",
    "MODE_AC3": "\u0417\u043c\u0456\u043d\u043d\u0438\u0439 3\u0444",
    "MODE_NOTE_DC": "<strong>\u041f\u043e\u0441\u0442\u0456\u0439\u043d\u0438\u0439 \u0441\u0442\u0440\u0443\u043c.</strong> \u041f\u0430\u0434\u0456\u043d\u043d\u044f \u043d\u0430\u043f\u0440\u0443\u0433\u0438 \u0440\u0430\u0445\u0443\u0454\u0442\u044c\u0441\u044f \u043f\u043e \u0432\u0441\u044c\u043e\u043c\u0443 \u043a\u043e\u043b\u0443, \u0442\u0443\u0434\u0438 \u0439 \u043d\u0430\u0437\u0430\u0434.",
    "TABLE_MODE_DC": "\u0426\u0456 \u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044f \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u043e \u0434\u043b\u044f \u043f\u043e\u0441\u0442\u0456\u0439\u043d\u043e\u0433\u043e \u0441\u0442\u0440\u0443\u043c\u0443.",
    "L_FREQ": "\u0427\u0430\u0441\u0442\u043e\u0442\u0430 / \u0413\u0446",
    "L_PF": "\u041a\u043e\u0435\u0444. \u043f\u043e\u0442\u0443\u0436\u043d\u043e\u0441\u0442\u0456 cos \u03c6",
    "D_SKIN": "\u0421\u043a\u0456\u043d-\u0435\u0444\u0435\u043a\u0442",
    "SCROLL_HINT": "Гортайте таблицю вбік — опір і максимальна траса →",
    "KICKER_CALC": "Живий розрахунок",
    "H2_CALC": "Калькулятор перерізу дроту",
    "P_CALC": "Вкажіть кількість жилок і їхній діаметр — і отримайте допустимий струм саме цього перерізу за "
    "обома температурними режимами: з інтерполяцією між рядками таблиці, а не з округленням до рядка.",
    "L_STRANDS": "Кількість жилок",
    "L_DIAM": "Діаметр жилки / мм",
    "L_INSTALL": "Прокладання / групування",
    "INSTALL_OPTIONS": build_options(
        {
            "bundle": "До 3 струмопровідних жил у кабелі",
            "free": "Одна жила у вільному повітрі",
            "4-6": "4–6 жил / зниження 80%",
            "7-9": "7–9 жил / зниження 70%",
            "10-20": "10–20 жил / зниження 50%",
            "21-30": "21–30 жил / зниження 45%",
            "31-40": "31–40 жил / зниження 40%",
            "41-plus": "41+ жил / зниження 35%",
        }
    ),
    "OPT_TITLE": "Додаткові перевірки",
    "OPT_NOTE": "За замовчуванням: 24 В · 2 м · 35 А · 30°C · 50 Гц",
    "OPTIONAL": "необов'язково",
    "L_VOLT": "Напруга системи / В",
    "L_LEN": "Довжина в один бік / м",
    "L_LOAD": "Струм навантаження / А",
    "L_AMB": "Довкілля / °C",
    "BTN_CALC": "Розрахувати",
    "BTN_COPY": "Копіювати", 
    "BTN_RESET": "Скинути",
    "RESULTS_TITLE": "Результат / показники",
    "M_AREA": "Розрахований переріз",
    "M_GAUGE": "Еквівалентний калібр",
    "SHARED_CTX": "до 3 жил у кабелі · довкілля 30°C",
    "AMP_GRID_LABEL": "Допустимий струм за температурою провідника",
    "C_NORMAL": "Звичайний режим",
    "C_HIGH": "Високотемпературна межа",
    "CTX_60": "провідник 60°C",
    "CTX_200": "провідник 200°C",
    "D_DROP": "Падіння напруги",
    "D_PCT": "Відсоток падіння",
    "D_LOSS": "Втрати в дроті",
    "MSG_START": "Введіть реальну конструкцію провідника, щоб почати.",
    "SOURCE_NOTE": 'Значення для малих калібрів звірені з <a '
    'href="https://www.amphenol.co.jp/military/techinfo/CurrentCarryingCapacity.html" target="_blank" '
    'rel="noopener noreferrer">даними Amphenol Japan щодо струмового навантаження кабелів</a>. Площі AWG '
    'відповідають <a href="https://store.astm.org/b0258-18r26.html" target="_blank" '
    'rel="noopener noreferrer">ASTM B258</a>. Остаточний вибір перерізу має враховувати конкретний дріт, '
    "клеми, запобіжник, корпус і вимоги місцевих норм.",
    "CONTENT": UK_CONTENT,
    "QUICKNAV_TITLE": "На цій сторінці",
    "QUICKNAV": quicknav(
        [
            ("#chart", "Таблиця AWG в ампери"),
            ("#calculator", "Калькулятор перерізу"),
            ("#how-to-read", "Як читати таблицю"),
            ("#how-it-works", "Як працює калькулятор"),
            ("#materials", "Матеріали жили"),
            ("#insulation", "Ізоляція"),
            ("#conversions", "AWG у мм²"),
            ("#faq", "Часті запитання"),
            ("#source", "Подивитися код"),
            ("/awg-to-amps", "English version"),
        ]
    ),
    "FOOTER_L": "AWG / АМПЕРИ — технічний довідник",
    "FOOTER_R": "Не замінює даташит виробника або чинні електротехнічні норми.",
    "I18N": json.dumps(
        {
            "uArea": "мм²",
            "copied": "\u0421\u043a\u043e\u043f\u0456\u0439\u043e\u0432\u0430\u043d\u043e",
            "customMaterial": "Власна",
            "customInsulation": "Власна",
            "insulationNote": "<strong>{name}, {c} °C.</strong> Робоча температура жили {c} °C, струм ×{factor} відносно опублікованих даних для силікону 200 °C.",
            "materialNote": "<strong>{name}.</strong> {iacs}% IACS, ρ = {rho} Ом·мм²/м, струм ×{factor} відносно відпаленої міді.",
            "unitHighTemp": "°C / А",
            "uHz": "\u0413\u0446",
            "unitResistDc": "мОм/м · пост.",
            "modeTag": {
                "dc": "пост.",
                "ac1": "1ф",
                "ac3": "3ф",
            },
            "unitResistAc": "мОм/м · {f} Гц",
            "unitLength": "м @3% · {u} В {m}",
            "unitPower": "на {u} В {m}",
            "uKilowatt": "кВт",
            "labelSystemVoltage": "\u041d\u0430\u043f\u0440\u0443\u0433\u0430 \u0441\u0438\u0441\u0442\u0435\u043c\u0438 / \u0412",
            "labelLineVoltage": "\u041b\u0456\u043d\u0456\u0439\u043d\u0430 \u043d\u0430\u043f\u0440\u0443\u0433\u0430 / \u0412",
            "modeShort": {
                "dc": "\u043f\u043e\u0441\u0442\u0456\u0439\u043d\u0438\u0439",
                "ac1": "\u0437\u043c\u0456\u043d\u043d\u0438\u0439 1\u0444",
                "ac3": "\u0437\u043c\u0456\u043d\u043d\u0438\u0439 3\u0444",
            },
            "modeNote": {
                "dc": "<strong>\u041f\u043e\u0441\u0442\u0456\u0439\u043d\u0438\u0439 \u0441\u0442\u0440\u0443\u043c.</strong> \u041f\u0430\u0434\u0456\u043d\u043d\u044f \u043d\u0430\u043f\u0440\u0443\u0433\u0438 \u0440\u0430\u0445\u0443\u0454\u0442\u044c\u0441\u044f \u043f\u043e \u0432\u0441\u044c\u043e\u043c\u0443 \u043a\u043e\u043b\u0443, \u0442\u0443\u0434\u0438 \u0439 \u043d\u0430\u0437\u0430\u0434.",
                "ac1": "<strong>\u041e\u0434\u043d\u043e\u0444\u0430\u0437\u043d\u0438\u0439 \u0437\u043c\u0456\u043d\u043d\u0438\u0439.</strong> \u0416\u0438\u043b\u0438 \u0434\u0432\u0456, \u0442\u043e\u0436 \u043f\u0430\u0434\u0456\u043d\u043d\u044f \u0432\u0441\u0435 \u0449\u0435 \u0440\u0430\u0445\u0443\u0454\u0442\u044c\u0441\u044f \u0442\u0443\u0434\u0438 \u0439 \u043d\u0430\u0437\u0430\u0434, \u0430\u043b\u0435 \u0437 \u043f\u043e\u043f\u0440\u0430\u0432\u043a\u043e\u044e \u043d\u0430 cos \u03c6. \u0414\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u0438\u0439 \u0441\u0442\u0440\u0443\u043c \u0442\u0430\u043a\u0438\u0439 \u0441\u0430\u043c\u0438\u0439, \u044f\u043a \u0434\u043b\u044f \u043f\u043e\u0441\u0442\u0456\u0439\u043d\u043e\u0433\u043e: \u043d\u0430 50\u201360 \u0413\u0446 \u0441\u043a\u0456\u043d-\u0435\u0444\u0435\u043a\u0442 \u043c\u0435\u043d\u0448\u0438\u0439 \u0437\u0430 0,1 % \u043d\u0430\u0432\u0456\u0442\u044c \u0434\u043b\u044f 0 AWG.",
                "ac3": "<strong>\u0422\u0440\u0438\u0444\u0430\u0437\u043d\u0438\u0439 \u0437\u043c\u0456\u043d\u043d\u0438\u0439.</strong> \u041f\u0430\u0434\u0456\u043d\u043d\u044f \u0434\u043e\u0440\u0456\u0432\u043d\u044e\u0454 \u221a3\u00b7I\u00b7R\u00b7L \u043c\u0456\u0436 \u043b\u0456\u043d\u0456\u044f\u043c\u0438 \u043d\u0430 \u0434\u043e\u0432\u0436\u0438\u043d\u0456 \u0432 \u043e\u0434\u0438\u043d \u0431\u0456\u043a, \u0430 \u0442\u0440\u0438 \u0444\u0430\u0437\u043d\u0456 \u0436\u0438\u043b\u0438 \u2014 \u0446\u0435 \u0440\u0456\u0432\u043d\u043e \u0432\u0438\u043f\u0430\u0434\u043e\u043a \u00ab\u22643 \u0436\u0438\u043b\u0438\u00bb \u0456\u0437 \u0442\u0430\u0431\u043b\u0438\u0446\u0456.",
            },
            "tableModeNote": {
                "dc": "\u0426\u0456 \u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044f \u043d\u0430\u0432\u0435\u0434\u0435\u043d\u043e \u0434\u043b\u044f \u043f\u043e\u0441\u0442\u0456\u0439\u043d\u043e\u0433\u043e \u0441\u0442\u0440\u0443\u043c\u0443.",
                "ac1": "\u0426\u0456 \u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044f \u0431\u0435\u0437 \u0437\u043c\u0456\u043d \u0434\u0456\u044e\u0442\u044c \u0456 \u0434\u043b\u044f \u043e\u0434\u043d\u043e\u0444\u0430\u0437\u043d\u043e\u0433\u043e \u0437\u043c\u0456\u043d\u043d\u043e\u0433\u043e \u0441\u0442\u0440\u0443\u043c\u0443 50\u201360 \u0413\u0446: \u0433\u043b\u0438\u0431\u0438\u043d\u0430 \u0441\u043a\u0456\u043d-\u0448\u0430\u0440\u0443 \u0432 \u043c\u0456\u0434\u0456 \u2014 \u0431\u043b\u0438\u0437\u044c\u043a\u043e 9,4 \u043c\u043c \u043d\u0430 50 \u0413\u0446, \u0449\u043e \u043d\u0430\u0431\u0430\u0433\u0430\u0442\u043e \u0431\u0456\u043b\u044c\u0448\u0435 \u0437\u0430 \u0440\u0430\u0434\u0456\u0443\u0441 4,1 \u043c\u043c \u043d\u0430\u0432\u0456\u0442\u044c \u0443 \u0436\u0438\u043b\u0438 0 AWG, \u0442\u043e\u0436 \u043f\u0440\u0438\u0440\u0456\u0441\u0442 \u043e\u043f\u043e\u0440\u0443 \u043b\u0438\u0448\u0430\u0454\u0442\u044c\u0441\u044f \u043c\u0435\u043d\u0448\u0438\u043c \u0437\u0430 0,1 %.",
                "ac3": "\u041a\u043e\u043b\u043e\u043d\u043a\u0438 \u00ab\u0443 \u043a\u0430\u0431\u0435\u043b\u0456\u00bb \u0437\u043d\u0438\u0436\u0435\u043d\u043e \u043d\u0430 \u043a\u043e\u0435\u0444\u0456\u0446\u0456\u0454\u043d\u0442 0,915 \u0437\u0430 IEC 60364-5-52: \u0442\u0440\u0438 \u0441\u0442\u0440\u0443\u043c\u043e\u043f\u0440\u043e\u0432\u0456\u0434\u043d\u0456 \u0436\u0438\u043b\u0438 \u0433\u0440\u0456\u044e\u0442\u044c \u043a\u0430\u0431\u0435\u043b\u044c \u0441\u0438\u043b\u044c\u043d\u0456\u0448\u0435 \u0437\u0430 \u0434\u0432\u0456. \u041a\u043e\u043b\u043e\u043d\u043a\u0438 \u0432\u0456\u043b\u044c\u043d\u043e\u0433\u043e \u043f\u043e\u0432\u0456\u0442\u0440\u044f \u043e\u043f\u0438\u0441\u0443\u044e\u0442\u044c \u043e\u0434\u043d\u0443 \u0436\u0438\u043b\u0443 \u0456 \u043d\u0435 \u0437\u043c\u0456\u043d\u044e\u044e\u0442\u044c\u0441\u044f.",
            },
            "msgSkinRange": "\u041f\u043e\u043d\u0430\u0434 \u043f\u0440\u0438\u0431\u043b\u0438\u0437\u043d\u043e 1 \u043a\u0413\u0446 \u043d\u0430 \u043d\u0430\u0439\u0431\u0456\u043b\u044c\u0448\u0438\u0445 \u043a\u0430\u043b\u0456\u0431\u0440\u0430\u0445 \u0444\u043e\u0440\u043c\u0443\u043b\u0430 \u0441\u043a\u0456\u043d-\u0435\u0444\u0435\u043a\u0442\u0443 \u0432\u0438\u0445\u043e\u0434\u0438\u0442\u044c \u0437\u0430 \u043c\u0435\u0436\u0456 \u043f\u0435\u0440\u0435\u0432\u0456\u0440\u0435\u043d\u043e\u0433\u043e \u0434\u0456\u0430\u043f\u0430\u0437\u043e\u043d\u0443, \u0442\u043e\u0436 \u043e\u043f\u0456\u0440 \u043d\u0430 \u0417\u0421 \u0432\u0432\u0430\u0436\u0430\u0439\u0442\u0435 \u043e\u0440\u0456\u0454\u043d\u0442\u043e\u0432\u043d\u0438\u043c.",
            "uAmp": "А",
            "uVolt": "В",
            "uWatt": "Вт",
            "below30": "менше 30 AWG",
            "below0": "більше 0 AWG",
            "instFree": "одна жила / вільне повітря",
            "instBundle": "до 3 жил у кабелі",
            "conductorSuffix": "°C провідник",
            "ambientDefault": "довкілля 30°C (типово)",
            "ambientSuffix": "°C довкілля",
            "noMargin": "Немає запасу",
            "stDanger": "Потрібен тепловий запас",
            "stReady": "Струм розраховано",
            "stAboveBoth": "Вище обох режимів",
            "stAbove60": "Вище режиму 60°C",
            "stWithin": "У межах обох режимів",
            "msgDanger": "Задана температура довкілля виходить за межі одного з довідкових діапазонів. "
            "Перегляньте обидва температурні результати, перш ніж обирати нижчий тепловий режим або іншу "
            "кабельну систему.",
            "msgReady": "Допустимий струм розраховано. Додайте струм навантаження, напругу системи та "
            "довжину в один бік, щоб перевірити запас і падіння напруги.",
            "msgAboveBoth": "<strong>{i} А</strong> перевищує і режим 60°C (<strong>{a60} А</strong>), і "
            "режим 200°C (<strong>{a200} А</strong>). Збільште переріз, покращте охолодження або зменште "
            "навантаження.",
            "msgAbove60": "<strong>{i} А</strong> перевищує консервативний режим 60°C "
            "(<strong>{a60} А</strong>), але вкладається в межу 200°C (<strong>{a200} А</strong>). "
            "Перевірте конкретний дріт, клеми, запобіжник, корпус і місцеві норми перед застосуванням.",
            "msgWithin": "<strong>{i} А</strong> вкладається в обидва температурні режими. Значення 60°C "
            "залишається консервативною щоденною базою; перед остаточним застосуванням перевірте клеми, "
            "запобіжник, корпус і обмеження виробника.",
        },
        ensure_ascii=False,
        indent=None,
    ),
}


# --------------------------------------------------------------------------
# JSON-LD
# --------------------------------------------------------------------------


def build_jsonld(cfg, faq_items):
    url = cfg["CANONICAL"]
    lang = cfg["LANG"]
    title = cfg["TITLE"].replace("&amp;", "&")

    publisher = {
        "@type": "Organization",
        "@id": f"{BASE}/#organization",
        "name": "66ton99.org.ua",
        "url": f"{BASE}/",
    }

    graph = [
        publisher,
        {
            "@type": "WebSite",
            "@id": f"{BASE}/#website",
            "url": f"{BASE}/",
            "name": "66ton99.org.ua",
            "publisher": {"@id": f"{BASE}/#organization"},
            "inLanguage": ["en", "uk"],
        },
        {
            "@type": "WebPage",
            "@id": f"{url}#webpage",
            "url": url,
            "name": title,
            "description": cfg["DESC"],
            "inLanguage": lang,
            "isPartOf": {"@id": f"{BASE}/#website"},
            "breadcrumb": {"@id": f"{url}#breadcrumb"},
            "primaryImageOfPage": {"@id": f"{url}#primaryimage"},
            "about": {"@id": f"{url}#dataset"},
            "mainEntity": {"@id": f"{url}#calculator"},
        },
        {
            "@type": "ImageObject",
            "@id": f"{url}#primaryimage",
            "url": cfg["OG_IMAGE"],
            "contentUrl": cfg["OG_IMAGE"],
            "width": 1200,
            "height": 630,
            "caption": cfg["OG_IMAGE_ALT"],
        },
        {
            "@type": "BreadcrumbList",
            "@id": f"{url}#breadcrumb",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": cfg["BC_HOME"],
                    "item": f"{BASE}{cfg['HOME_HREF']}",
                },
                {"@type": "ListItem", "position": 2, "name": cfg["BC_CURRENT"]},
            ],
        },
        {
            "@type": "WebApplication",
            "@id": f"{url}#calculator",
            "name": cfg["H2_CALC"],
            "url": f"{url}#calculator",
            "applicationCategory": "UtilitiesApplication",
            "applicationSubCategory": "Engineering calculator",
            "operatingSystem": "Any (web browser)",
            "browserRequirements": "Requires JavaScript",
            "inLanguage": lang,
            "isAccessibleForFree": True,
            "publisher": {"@id": f"{BASE}/#organization"},
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "featureList": cfg["FEATURES"],
        },
        {
            "@type": "Dataset",
            "@id": f"{url}#dataset",
            "name": cfg["TABLE_CAPTION"],
            "description": cfg["DESC"],
            "url": f"{url}#chart",
            "inLanguage": lang,
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "creator": {"@id": f"{BASE}/#organization"},
            "variableMeasured": [
                {"@type": "PropertyValue", "name": "AWG size", "minValue": 0, "maxValue": 30},
                {
                    "@type": "PropertyValue",
                    "name": "Nominal copper cross-section",
                    "unitText": "mm2",
                    "minValue": 0.051,
                    "maxValue": 53.49,
                },
                {
                    "@type": "PropertyValue",
                    "name": "Ampacity",
                    "unitText": "A",
                    "minValue": 2,
                    "maxValue": 348,
                },
                {
                    "@type": "PropertyValue",
                    "name": "Conductor resistance",
                    "unitText": "mOhm/m",
                    "minValue": 0.327,
                    "maxValue": 343,
                },
                {
                    "@type": "PropertyValue",
                    "name": "Maximum run length at 3% voltage drop",
                    "unitText": "m",
                },
                {
                    "@type": "PropertyValue",
                    "name": "Maximum transmissible load",
                    "unitText": "W",
                },
                {
                    "@type": "PropertyValue",
                    "name": "Conductor conductivity",
                    "unitText": "% IACS",
                    "minValue": 30,
                    "maxValue": 105,
                },
            ],
        },
        {
            "@type": "FAQPage",
            "@id": f"{url}#faq",
            "inLanguage": lang,
            "isPartOf": {"@id": f"{url}#webpage"},
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": strip_tags(q),
                    "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)},
                }
                for q, a in faq_items
            ],
        },
    ]

    return json.dumps(
        {"@context": "https://schema.org", "@graph": graph},
        ensure_ascii=False,
        indent=2,
    )


EN["FEATURES"] = [
    "AWG to mm² conversion",
    "Copper cross-section from strand count and strand diameter",
    "Ampacity at 60 °C and 200 °C conductor temperature",
    "Ambient temperature derating",
    "Bundle and grouping derating",
    "DC voltage drop, drop percentage and wire power loss",
]
UK["FEATURES"] = [
    "Переведення AWG у мм²",
    "Переріз міді за кількістю та діаметром жилок",
    "Допустимий струм за 60 °C і 200 °C",
    "Поправка на температуру довкілля",
    "Поправка на групування жил у пучку",
    "Падіння напруги, його відсоток і втрати потужності",
]


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------


def render(cfg, faq_items, out_path):
    template = (HERE / "template.html").read_text(encoding="utf-8")
    values = dict(cfg)
    values["TBODY"] = build_tbody(cfg["LANG"])
    values["JSONLD"] = build_jsonld(cfg, faq_items)

    for key, value in values.items():
        if key == "FEATURES":
            continue
        template = template.replace("{{" + key + "}}", str(value))

    leftover = set(re.findall(r"\{\{([A-Z_0-9]+)\}\}", template))
    if leftover:
        raise SystemExit(f"Unreplaced tokens in {out_path.name}: {sorted(leftover)}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(template, encoding="utf-8")
    print(f"wrote {out_path.relative_to(OUT)}  ({len(template):,} bytes)")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    render(EN, EN_FAQ, OUT / "_pages" / "awg-to-amps.html")
    render(UK, UK_FAQ, OUT / "_pages" / "uk-awg-to-amps.html")

    (OUT / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        "# Explicitly allow AI/answer engines to read the reference data\n"
        "User-agent: GPTBot\n"
        "Allow: /\n"
        "\n"
        "User-agent: ClaudeBot\n"
        "Allow: /\n"
        "\n"
        "User-agent: PerplexityBot\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {BASE}/sitemap.xml\n",
        encoding="utf-8",
    )
    print("wrote robots.txt")

    def alt_links(en_href, uk_href, indent=4):
        pad = " " * indent
        return (
            f'{pad}<xhtml:link rel="alternate" hreflang="en" href="{en_href}"/>\n'
            f'{pad}<xhtml:link rel="alternate" hreflang="uk" href="{uk_href}"/>\n'
            f'{pad}<xhtml:link rel="alternate" hreflang="x-default" href="{en_href}"/>'
        )

    home_en, home_uk = f"{BASE}/", f"{BASE}/uk"
    home_alts = alt_links(home_en, home_uk)
    page_alts = alt_links(EN_URL, UK_URL)

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>{home_en}</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
{home_alts}
  </url>
  <url>
    <loc>{home_uk}</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
{home_alts}
  </url>
  <url>
    <loc>{EN_URL}</loc>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
{page_alts}
  </url>
  <url>
    <loc>{UK_URL}</loc>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
{page_alts}
  </url>
</urlset>
"""
    (OUT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print("wrote sitemap.xml")


if __name__ == "__main__":
    main()
