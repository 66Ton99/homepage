const fs = require("fs");
const { JSDOM } = require("jsdom");

let failures = 0;
let total = 0;
function checkClose(label, actual, expected, tol) {
  total++;
  const ok = Math.abs(actual - expected) <= tol;
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${label}: ${actual}${ok ? "" : `  (expected ~${expected})`}`);
}

function check(label, actual, expected) {
  total++;
  const ok = String(actual) === String(expected);
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${label}: ${actual}${ok ? "" : `  (expected ${expected})`}`);
}

async function run(file, label, expect) {
  console.log(`\n== ${label} ==`);
  const html = fs.readFileSync(file, "utf8");
  const dom = new JSDOM(html, {
    runScripts: "dangerously", pretendToBeVisual: true,
    url: "https://66ton99.org.ua/awg-to-amps",
  });
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

async function runBasics() {
  await run("../site/_pages/awg-to-amps.html", "EN", {
    area: "8.29 mm²",
    gauge: "≈ 8 AWG",
    status: "Within both references",
    drop: "0.264 V",
  });
  await run("../site/_pages/uk-awg-to-amps.html", "UK", {
    area: "8,29 мм²",
    gauge: "≈ 8 AWG",
    status: "У межах обох режимів",
    drop: "0,264 В",
  });
}

// ---------------------------------------------------------------------------
// DC / AC mode switching
// ---------------------------------------------------------------------------
async function runModes(file, label, expect) {
  console.log(`\n== ${label}: current mode ==`);
  const dom = new JSDOM(fs.readFileSync(file, "utf8"), {
    runScripts: "dangerously", pretendToBeVisual: true,
    url: "https://66ton99.org.ua/awg-to-amps",
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
  checkClose("0 AWG at 400 Hz raises resistance ~15.5%", highF, 15.5, 0.2);

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
  $("frequency").value = expect.freq;
  $("frequency").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  $("strandCount").value = "1650";
  $("strandCount").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  $("systemVoltage").value = "24";
  $("systemVoltage").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  check("0 AWG DC resistance", cellNum("0", "js-r").toFixed(3), "0.341");
  checkClose("0 AWG DC run @3% on 24 V", cellNum("0", "js-len"), 9.6, 0.1);
  checkClose("22 AWG DC run @3% on 24 V", cellNum("22", "js-len"), 1.3, 0.1);

  pick("ac3");   // voltage should follow the mode to 400 V
  check("voltage follows the mode", $("systemVoltage").value, expect.v3);
  // the run gets *longer* on three-phase: the rated current it must hold is lower
  checkClose("0 AWG 3-phase run @3%", cellNum("0", "js-len"), expect.run3, 1);
  checkClose("22 AWG 3-phase run @3%", cellNum("22", "js-len"), expect.run3small, 0.5);
  check("length header names the voltage", $("thLengthUnit").textContent.includes(expect.v3), true);

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
  check("0 AWG ampacity derated at 400 Hz", cellNum("0", "js-b60").toFixed(0), "93");
  check("22 AWG ampacity unchanged at 400 Hz", cellNum("22", "js-b60").toFixed(0), "5");
  checkClose("0 AWG AC resistance at 400 Hz", cellNum("0", "js-r"), 0.393, 0.003);
  check("resistance header names the frequency", $("thResistUnit").textContent.includes("400"), true);

  pick("dc");
  check("back to DC restores resistance", cellNum("0", "js-r").toFixed(3), "0.341");

  // ---- conductor material ----
  const setMat = (v) => {
    $("material").value = v;
    $("modeBar").dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  };
  pick("dc");
  setMat("cu");
  const cuAmps = cellNum("0", "js-b60");
  const cuOhms = cellNum("0", "js-r");
  // capture the run under whatever voltage the earlier checks left set, rather
  // than assuming the default
  const cuRun = cellNum("0", "js-len");
  check("copper is the reference", cuAmps.toFixed(1), "112.0");

  setMat("al");
  // I goes as sqrt(conductivity); 61.2% IACS predicts 0.782, and NEC 310.16
  // gives 0.774 averaged over 6 AWG to 4/0
  checkClose("aluminium carries ~78% of copper", cellNum("0", "js-b60") / cuAmps, 0.782, 0.002);
  checkClose("aluminium resistance is 1/0.612 of copper", cellNum("0", "js-r") / cuOhms, 1 / 0.612, 0.01);
  check("aluminium shortens the run", cellNum("0", "js-len") < cuRun, true);

  setMat("cusn");
  checkClose("tinning costs about 2%", cellNum("0", "js-b60") / cuAmps, 0.980, 0.002);

  setMat("ccs");
  checkClose("copper-clad steel is ~55%", cellNum("0", "js-b60") / cuAmps, 0.548, 0.003);

  setMat("custom");
  check("custom shows the conductivity box", $("customIacs").hidden, false);
  $("conductivity").value = "50";
  $("conductivity").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  checkClose("50% IACS gives 1/sqrt(2) of copper", cellNum("0", "js-b60") / cuAmps, Math.SQRT1_2, 0.003);
  $("conductivity").value = "5000";
  $("conductivity").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  check("absurd conductivity is clamped", cellNum("0", "js-b60") / cuAmps < 1.06, true);

  setMat("cu");
  check("back to copper restores the reference", cellNum("0", "js-b60").toFixed(1), "112.0");
  check("copper is not the default, so it reaches the URL", dom.window.location.href.includes("mat=cu&") || dom.window.location.href.endsWith("mat=cu"), true);
  setMat("cusn");
  check("tinned copper is the default and leaves the URL clean", dom.window.location.href.includes("mat="), false);
  setMat("cu");

  // ---- insulation sets the conductor temperature rating ----
  const setIns = (v) => {
    $("insulation").value = v;
    $("modeBar").dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  };
  setMat("cu");
  setIns("sil200");
  check("silicone 200 is the reference", cellNum("0", "js-b200").toFixed(1), "224.0");
  check("the 60 C column is not touched by insulation", cellNum("0", "js-b60").toFixed(1), "112.0");

  setIns("thhn");
  // sqrt((90-30)/(1+a*70)) / sqrt((200-30)/(1+a*180)) = 0.687
  checkClose("90 C insulation scales to 0.687", cellNum("0", "js-b200") / 224, 0.687, 0.003);
  check("header follows the rating", $("thHighTempUnit").textContent.startsWith("90"), true);

  setIns("pvc70");
  checkClose("70 C insulation scales to 0.579", cellNum("0", "js-b200") / 224, 0.579, 0.003);
  check("a 70 C rating drops below the 60 C reference column",
        cellNum("0", "js-b200") > cellNum("0", "js-b60"), true);

  setIns("ptfe");
  checkClose("260 C insulation scales to 1.090", cellNum("0", "js-b200") / 224, 1.090, 0.003);

  setIns("custom");
  check("custom shows the temperature box", $("customTemp").hidden, false);
  $("tempRating").value = "200";
  $("tempRating").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  check("custom 200 C equals silicone", cellNum("0", "js-b200").toFixed(1), "224.0");

  setIns("sil200");
  check("silicone leaves insulation out of the URL", dom.window.location.href.includes("ins="), false);

  // ---- three loaded conductors derate the in-cable columns ----
  pick("dc");
  $("frequency").value = expect.freq;
  $("frequency").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  const dcB60 = cellNum("0", "js-b60");
  const dcF60 = cellNum("0", "js-f60");
  check("0 AWG in-cable on DC", dcB60.toFixed(0), "112");

  pick("ac1");
  // Same two loaded conductors as DC, so no conductor-count derate - but skin
  // and proximity still cost 0.30% on 0 AWG, and that must be visible.
  check("single-phase shows the AC penalty on 0 AWG", cell("0", "js-b60"), expect.ac1Zero);
  check("single-phase differs from DC", cellNum("0", "js-b60") < dcB60, true);
  check("single-phase is within 0.5% of DC", (dcB60 - cellNum("0", "js-b60")) / dcB60 < 0.005, true);
  check("nothing measurable at 8 AWG", cellNum("8", "js-b60").toFixed(1), "35.0");

  pick("ac3");
  check("three-phase derates the in-cable column", cellNum("0", "js-b60").toFixed(0), "102");
  check("three-phase derates 200 C too", cellNum("0", "js-b200").toFixed(0), "205");
  // free air must not pick up the conductor-count factor, only the AC penalty
  check("free air escapes the 3-phase derate", (dcF60 - cellNum("0", "js-f60")) / dcF60 < 0.005, true);
  checkClose("small gauges derate too", cellNum("22", "js-b60"), 4.6, 0.1);

  // ---- the same amps buy very different power per mode ----
  pick("dc");
  $("frequency").value = expect.freq;
  $("frequency").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  $("systemVoltage").value = "24";
  $("systemVoltage").dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  checkClose("0 AWG delivers ~2.7 kW on 24 V DC", cellNum("0", "js-p"), 2.69, 0.02);
  check("small gauges are quoted in watts", cell("30", "js-p").includes(expect.watt), true);

  pick("ac1");
  check("voltage follows to mains single-phase", $("systemVoltage").value, expect.v1);
  checkClose("0 AWG delivers the 1-phase power", cellNum("0", "js-p"), expect.p1, 0.2);

  pick("ac3");
  // 112 A x 0.915 = 102.5 A carried into the power column
  checkClose("0 AWG delivers the 3-phase power", cellNum("0", "js-p"), expect.p3, 0.5);
  check("power header names the voltage", $("thPowerUnit").textContent.includes(expect.v3), true);
}


const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function runUrl(file, label, expect) {
  console.log(`\n== ${label}: shareable URL ==`);
  const path = (w) => w.location.href.replace("https://66ton99.org.ua", "");
  const base = expect.path;

  // 1. state travels into the URL
  const dom = new JSDOM(fs.readFileSync(file, "utf8"), {
    runScripts: "dangerously", pretendToBeVisual: true,
    url: "https://66ton99.org.ua" + base,
  });
  const d = dom.window.document;
  const w = dom.window;
  const $ = (id) => d.getElementById(id);
  const pick = (v) => {
    d.querySelector(`input[name="currentMode"][value="${v}"]`).checked = true;
    $("modeBar").dispatchEvent(new w.Event("change", { bubbles: true }));
  };
  const set = (id, v) => {
    $(id).value = v;
    $(id).dispatchEvent(new w.Event("input", { bubbles: true }));
  };

  check("defaults leave the URL clean", path(w), base);
  pick("ac3");
  check("mode reaches the URL immediately", path(w), base + "?mode=ac3&u=" + expect.v3);
  set("loadCurrent", "50");
  await wait(500);
  check("calculator inputs reach the URL", path(w).includes("a=50"), true);
  check("only non-defaults are written", path(w).includes("d=0.08"), false);
  pick("dc");
  check("returning to DC drops mode and voltage", path(w), base + "?a=50");
  $("resetButton").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  await wait(500);
  check("reset restores a clean URL", path(w), base);

  // a gauge picked from the table travels as a gauge, not as a strand count
  d.querySelector('tr[data-gauge="20"] .row-btn')
    .dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  await wait(500);
  check("a table pick writes the gauge", path(w), base + "?awg=20");
  check("the gauge replaces the construction", path(w).includes("n="), false);
  set("strandCount", "120");
  await wait(500);
  check("a hand-typed construction drops back to strands", path(w), base + "?n=120");
  $("resetButton").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  await wait(500);
  check("the default construction is not a preset", path(w), base);

  // 2. a mode remembered from a previous visit must not rewrite the address bar
  const remembered = new JSDOM(fs.readFileSync(file, "utf8"), {
    runScripts: "dangerously", pretendToBeVisual: true,
    url: "https://66ton99.org.ua" + base,
    beforeParse(win) {
      win.localStorage.setItem("awg-current-mode", "ac3");
    },
  });
  await wait(500);
  check("a remembered mode is applied",
        remembered.window.document.querySelector("input[name=currentMode]:checked").value, "ac3");
  check("a remembered mode leaves the URL clean", path(remembered.window), base);

  // 3. the URL is honoured on arrival
  const shared = new JSDOM(fs.readFileSync(file, "utf8"), {
    runScripts: "dangerously", pretendToBeVisual: true,
    url: "https://66ton99.org.ua" + base + "?mode=ac3&n=4208&u=400&a=50&f=400",
  });
  const s2 = shared.window.document;
  const g2 = (id) => s2.getElementById(id);
  check("shared link restores mode", s2.querySelector("input[name=currentMode]:checked").value, "ac3");
  check("shared link restores strands", g2("strandCount").value, "4208");
  check("shared link restores voltage", g2("systemVoltage").value, "400");
  check("shared link restores frequency", g2("frequency").value, "400");
  check("shared link opens the optional section", g2("optionalChecks").open, true);

  const picked = new JSDOM(fs.readFileSync(file, "utf8"), {
    runScripts: "dangerously", pretendToBeVisual: true,
    url: "https://66ton99.org.ua" + base + "?awg=20",
  }).window.document;
  check("a gauge link restores the construction", picked.getElementById("strandCount").value, "103");
  check("a gauge link keeps the default strand diameter",
        picked.getElementById("strandDiameter").value, "0.08");
  check("a gauge link selects the row", picked.querySelector("tr.is-selected").dataset.gauge, "20");

  const explicit = new JSDOM(fs.readFileSync(file, "utf8"), {
    runScripts: "dangerously", pretendToBeVisual: true,
    url: "https://66ton99.org.ua" + base + "?awg=20&n=4208",
  }).window.document;
  check("an explicit strand count outranks the gauge",
        explicit.getElementById("strandCount").value, "4208");

  const bogus = new JSDOM(fs.readFileSync(file, "utf8"), {
    runScripts: "dangerously", pretendToBeVisual: true,
    url: "https://66ton99.org.ua" + base + "?awg=99",
  }).window.document;
  check("a gauge that is not in the table is ignored",
        bogus.getElementById("strandCount").value, "1650");

  const mat = new JSDOM(fs.readFileSync(file, "utf8"), {
    runScripts: "dangerously", pretendToBeVisual: true,
    url: "https://66ton99.org.ua" + base + "?mat=al",
  }).window.document;
  check("shared link restores the material", mat.getElementById("material").value, "al");

  const ins = new JSDOM(fs.readFileSync(file, "utf8"), {
    runScripts: "dangerously", pretendToBeVisual: true,
    url: "https://66ton99.org.ua" + base + "?ins=thhn",
  }).window.document;
  check("shared link restores the insulation", ins.getElementById("insulation").value, "thhn");
  check("shared link retitles the column",
        ins.getElementById("thHighTempUnit").textContent.startsWith("90"), true);
  check("shared link applies it to the table",
        mat.querySelector('tr[data-gauge="0"] .js-b60').textContent, expect.alZero);
  check("shared link recalculates", g2("areaResult").textContent.startsWith(expect.area), true);

  // a conductor of exactly 0 AWG computes to about -0.0006 and must not be
  // reported as larger than 0 AWG
  const zero = new JSDOM(fs.readFileSync(file, "utf8"), {
    runScripts: "dangerously", pretendToBeVisual: true,
    url: "https://66ton99.org.ua" + base + "?n=10641&d=0.08",
  }).window.document;
  check("exactly 0 AWG reads as 0 AWG", zero.getElementById("gaugeResult").textContent, "≈ 0 AWG");

  // 3. parameters must not spawn a second indexable URL
  check("canonical ignores the query string",
        s2.querySelector('link[rel=canonical]').href, "https://66ton99.org.ua" + base);
}

// One entry point. There used to be two, and the first one's process.exit()
// killed the second mid-run — silently, because the exit code was still 0.
(async () => {
  await runBasics();
  await runUrl("../site/_pages/awg-to-amps.html", "EN",
    { path: "/awg-to-amps", area: "21.15", v3: "208", alZero: "87.6 A" });
  await runUrl("../site/_pages/uk-awg-to-amps.html", "UK",
    { path: "/uk/awg-to-amps", area: "21,15", v3: "400", alZero: "87,6 А" });
  await runModes("../site/_pages/awg-to-amps.html", "EN",
    { skin50: "+0.01%", lineLabel: "Line voltage / V", watt: "W", ac1Zero: "111.8 A",
      v1: "120", v3: "208", freq: "60",
      run3: 105.3, run3small: 14.4, p1: 13.4, p3: 36.8 });
  await runModes("../site/_pages/uk-awg-to-amps.html", "UK",
    { skin50: "+0,01%", lineLabel: "Лінійна напруга / В", watt: "Вт", ac1Zero: "111,8 А",
      v1: "230", v3: "400", freq: "50",
      run3: 202.5, run3small: 27.6, p1: 25.7, p3: 70.9 });
  console.log(
    failures
      ? `\n${failures} of ${total} checks FAILED`
      : `\nAll ${total} checks passed.`
  );
  process.exit(failures ? 1 : 0);
})();
