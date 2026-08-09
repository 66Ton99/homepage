const fs = require("fs");
const { JSDOM } = require("jsdom");

let failures = 0;
function checkClose(label, actual, expected, tol) {
  const ok = Math.abs(actual - expected) <= tol;
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${label}: ${actual}${ok ? "" : `  (expected ~${expected})`}`);
}

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

// ---------------------------------------------------------------------------
// DC / AC mode switching
// ---------------------------------------------------------------------------
async function runModes(file, label, expect) {
  console.log(`\n== ${label}: current mode ==`);
  const dom = new JSDOM(fs.readFileSync(file, "utf8"), {
    runScripts: "dangerously", pretendToBeVisual: true,
  });
  const { document } = dom.window;
  const $ = (id) => document.getElementById(id);
  const pick = (value) => {
    document.querySelector(`input[name="currentMode"][value="${value}"]`).checked = true;
    $("modeBar").dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  };
  const num = (id) => parseFloat($(id).textContent.replace(",", ".").replace(/[^\d.]/g, ""));

  $("optionalChecks").open = true;
  $("optionalChecks").dispatchEvent(new dom.window.Event("toggle"));

  // defaults: 1650 x 0.08 mm = 8.29 mm2, 35 A, 2 m one-way, 24 V
  check("DC is the default", $("modeBar").querySelector("input:checked").value, "dc");
  check("AC fields hidden in DC", document.querySelector(".ac-only").hidden, true);
  const dcDrop = num("dropResult");
  const dcLoss = num("lossResult");
  const dcAmpacity = num("ampacity60Result");

  pick("ac1");
  check("AC fields shown", document.querySelector(".ac-only").hidden, false);
  check("1-phase drop equals DC at cos φ = 1", num("dropResult").toFixed(3), dcDrop.toFixed(3));
  check("1-phase loss equals DC", num("lossResult").toFixed(1), dcLoss.toFixed(1));
  check("ampacity unchanged at 50 Hz", num("ampacity60Result").toFixed(1), dcAmpacity.toFixed(1));
  check("skin effect at 50 Hz is negligible", $("skinResult").textContent, expect.skin50);

  // power factor 0.8 scales the drop but not the loss (loss is I²R)
  $("powerFactor").value = "0.8";
  $("powerFactor").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  check("cos φ 0.8 scales drop", num("dropResult").toFixed(3), (dcDrop * 0.8).toFixed(3));
  check("cos φ does not change loss", num("lossResult").toFixed(1), dcLoss.toFixed(1));
  $("powerFactor").value = "1";
  $("powerFactor").dispatchEvent(new dom.window.Event("input", { bubbles: true }));

  pick("ac3");
  // dcDrop is read back already rounded to 3 dp, so compare with a tolerance
  checkClose("3-phase drop is √3/2 of DC", num("dropResult"), dcDrop * Math.sqrt(3) / 2, 0.001);
  check("3-phase loss is 3/2 of DC", num("lossResult").toFixed(1), (dcLoss * 1.5).toFixed(1));
  check("voltage label switches to line", $("voltageLabel").textContent, expect.lineLabel);

  // 400 Hz on 0 AWG is where skin effect finally bites
  $("strandCount").value = "10643";           // 10643 x 0.08 mm ≈ 53.5 mm2 = 0 AWG
  $("strandCount").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  $("frequency").value = "400";
  $("frequency").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  const highF = parseFloat($("skinResult").textContent.replace(",", ".").replace(/[^\d.]/g, ""));
  // skin + proximity together, per IEC 60287
  checkClose("0 AWG at 400 Hz raises resistance ~16.6%", highF, 16.6, 0.2);

  pick("dc");
  check("back to DC hides AC fields", document.querySelector(".ac-only").hidden, true);

  // ---- the table itself must follow the mode ----
  const cell = (gauge, cls) =>
    document.querySelector(`tr[data-gauge="${gauge}"] .${cls}`).textContent;
  const cellNum = (gauge, cls) =>
    parseFloat(cell(gauge, cls).replace(",", ".").replace(/[^\d.]/g, ""));

  pick("dc");
  // the 400 Hz block above left the frequency set; put it back to mains so the
  // baseline rows are not carrying a skin-effect derate
  $("frequency").value = "50";
  $("frequency").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  $("strandCount").value = "1650";
  $("strandCount").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  $("systemVoltage").value = "24";
  $("systemVoltage").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  check("0 AWG DC resistance", cellNum("0", "js-r").toFixed(3), "0.327");
  checkClose("0 AWG DC run @3% on 24 V", cellNum("0", "js-len"), 9.8, 0.1);
  checkClose("22 AWG DC run @3% on 24 V", cellNum("22", "js-len"), 1.3, 0.1);

  pick("ac3");   // voltage should follow the mode to 400 V
  check("voltage follows the mode", $("systemVoltage").value, "400");
  // the run gets *longer* on three-phase: the rated current it must hold is lower
  checkClose("0 AWG 3-phase run @3% on 400 V", cellNum("0", "js-len"), 206.7, 1);
  checkClose("22 AWG 3-phase run @3% on 400 V", cellNum("22", "js-len"), 28.2, 0.5);
  check("length header names the mode", $("thLengthUnit").textContent.includes("400"), true);

  // a voltage the reader typed must survive a mode change
  $("systemVoltage").value = "48";
  $("systemVoltage").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  pick("ac1");
  check("typed voltage is not overwritten", $("systemVoltage").value, "48");

  // at 400 Hz the ampacity column itself moves on the big gauges
  pick("ac3");
  $("frequency").value = "400";
  $("frequency").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  // 400 Hz skin+proximity on top of the three-phase conductor-count factor
  check("0 AWG ampacity derated at 400 Hz", cellNum("0", "js-b60").toFixed(0), "95");
  check("22 AWG ampacity unchanged at 400 Hz", cellNum("22", "js-b60").toFixed(0), "5");
  checkClose("0 AWG AC resistance at 400 Hz", cellNum("0", "js-r"), 0.381, 0.003);
  check("resistance header names the frequency", $("thResistUnit").textContent.includes("400"), true);

  pick("dc");
  check("back to DC restores resistance", cellNum("0", "js-r").toFixed(3), "0.327");

  // ---- three loaded conductors derate the in-cable columns ----
  pick("dc");
  $("frequency").value = "50";
  $("frequency").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  const dcB60 = cellNum("0", "js-b60");
  const dcF60 = cellNum("0", "js-f60");
  check("0 AWG in-cable on DC", dcB60.toFixed(0), "112");

  pick("ac1");
  check("single-phase matches DC (both are 2 loaded conductors)",
        cellNum("0", "js-b60").toFixed(0), dcB60.toFixed(0));

  pick("ac3");
  check("three-phase derates the in-cable column", cellNum("0", "js-b60").toFixed(0), "102");
  check("three-phase derates 200 C too", cellNum("0", "js-b200").toFixed(0), "205");
  check("free air is a lone conductor, unchanged", cellNum("0", "js-f60").toFixed(0), dcF60.toFixed(0));
  checkClose("small gauges derate too", cellNum("22", "js-b60"), 4.6, 0.1);

  // ---- the same amps buy very different power per mode ----
  pick("dc");
  $("frequency").value = "50";
  $("frequency").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  $("systemVoltage").value = "24";
  $("systemVoltage").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  checkClose("0 AWG delivers ~2.7 kW on 24 V DC", cellNum("0", "js-p"), 2.69, 0.02);
  check("small gauges are quoted in watts", cell("30", "js-p").includes(expect.watt), true);

  pick("ac1");
  check("voltage follows to 230 V", $("systemVoltage").value, "230");
  checkClose("0 AWG delivers ~25.8 kW on 230 V 1-phase", cellNum("0", "js-p"), 25.8, 0.2);

  pick("ac3");
  // 112 A x 0.915 = 102.5 A carried into the power column
  checkClose("0 AWG delivers ~71 kW on 400 V 3-phase", cellNum("0", "js-p"), 71.0, 0.5);
  check("power header names the mode", $("thPowerUnit").textContent.includes("400"), true);
}


(async () => {
  await runModes("../site/_pages/awg-to-amps.html", "EN",
    { skin50: "+0.01%", lineLabel: "Line voltage / V", watt: "W" });
  await runModes("../site/_pages/uk-awg-to-amps.html", "UK",
    { skin50: "+0,01%", lineLabel: "Лінійна напруга / В", watt: "Вт" });
  console.log(failures ? `\n${failures} FAILURES` : "\nAll mode checks passed.");
  process.exit(failures ? 1 : 0);
})();
