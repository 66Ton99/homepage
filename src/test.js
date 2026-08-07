const fs = require("fs");
const { JSDOM } = require("jsdom");

let failures = 0;
function check(label, actual, expected) {
  const ok = String(actual) === String(expected);
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${label}: ${actual}${ok ? "" : `  (expected ${expected})`}`);
}

async function run(file, label, expect) {
  console.log(`\n== ${label} ==`);
  const html = fs.readFileSync(file, "utf8");
  const dom = new JSDOM(html, { runScripts: "dangerously", pretendToBeVisual: true });
  const { document } = dom.window;
  const $ = (id) => document.getElementById(id);

  // static table is present in source, before any JS
  check("static rows in DOM", document.querySelectorAll("tbody tr[data-gauge]").length, 17);

  // default calculation ran on load (1650 strands x 0.08 mm => 8.29 mm2)
  check("area readout", $("areaResult").textContent, expect.area);
  check("equivalent gauge", $("gaugeResult").textContent, expect.gauge);
  check("nearest row selected", document.querySelector("tbody tr.is-selected").dataset.gauge, "8");
  check("status badge", $("statusBadge").textContent, expect.status);

  // voltage drop appears once the optional section is opened
  check("drop hidden initially", $("optionalDropResults").hidden, true);
  $("optionalChecks").open = true;
  $("optionalChecks").dispatchEvent(new dom.window.Event("toggle"));
  check("drop visible after toggle", $("optionalDropResults").hidden, false);
  check("voltage drop", $("dropResult").textContent, expect.drop);

  // clicking a row button loads that gauge preset
  const btn = document.querySelector('tr[data-gauge="4"] .row-btn');
  btn.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  check("preset strand count for 4 AWG", $("strandCount").value, "4208");
  check("selected row after preset", document.querySelector("tbody tr.is-selected").dataset.gauge, "4");

  // reset restores defaults
  $("resetButton").dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  check("strand count after reset", $("strandCount").value, "1650");
  check("area after reset", $("areaResult").textContent, expect.area);
}

(async () => {
  await run("../site/_pages/awg-to-amps.html", "EN", {
    area: "8.29 mm²",
    gauge: "≈ 8 AWG",
    status: "Within both references",
    drop: "0.295 V",
  });
  await run("../site/_pages/uk-awg-to-amps.html", "UK", {
    area: "8,29 мм²",
    gauge: "≈ 8 AWG",
    status: "У межах обох режимів",
    drop: "0,295 В",
  });
  console.log(failures ? `\n${failures} FAILURES` : "\nAll checks passed.");
  process.exit(failures ? 1 : 0);
})();
