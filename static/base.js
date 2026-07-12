// base.js v1 — shared: clock, sidebar toggle, model/conf

// ===== Clock =====
(function tick() {
  const p  = n => String(n).padStart(2, "0");
  const d  = new Date();
  const el = document.getElementById("clk");
  if (el) el.textContent = `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  setTimeout(tick, 1000);
})();

// ===== Sidebar toggle (persist state) =====
const appSidebar    = document.getElementById("appSidebar");
const sidebarToggle = document.getElementById("sidebarToggle");

if (appSidebar && sidebarToggle) {
  if (localStorage.getItem("sidebarCollapsed") === "true") {
    appSidebar.classList.add("collapsed");
  }
  sidebarToggle.addEventListener("click", () => {
    appSidebar.classList.toggle("collapsed");
    localStorage.setItem("sidebarCollapsed",
      appSidebar.classList.contains("collapsed").toString());
  });
}

// ===== Model + Confidence (global helpers) =====
const modelSelect = document.getElementById("modelSelect");
const confSlider  = document.getElementById("confSlider");
const confVal     = document.getElementById("confVal");

function getModel() { return modelSelect ? modelSelect.value : "m"; }
function getConf()  { return confSlider  ? parseFloat(confSlider.value) : 0.25; }

async function loadSettings() {
  try {
    const res  = await fetch("/api/settings");
    const data = await res.json();
    if (modelSelect) {
      modelSelect.value = data.model;
      _updateFooterModel();
    }
    if (confSlider && confVal) {
      confSlider.value     = data.conf;
      confVal.textContent  = parseFloat(data.conf).toFixed(2);
    }
  } catch (_) {}
}

async function pushSettings() {
  try {
    await fetch("/api/settings", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: getModel(), conf: getConf() }),
    });
    _updateFooterModel();
  } catch (_) {}
}

function _updateFooterModel() {
  const ft = document.getElementById("footerModel");
  if (ft && modelSelect) {
    const opt = modelSelect.options[modelSelect.selectedIndex];
    ft.textContent = opt ? opt.text.split("·")[0].trim() : "";
  }
}

if (modelSelect) {
  modelSelect.addEventListener("change", pushSettings);
}
if (confSlider && confVal) {
  confSlider.addEventListener("input", () => {
    confVal.textContent = parseFloat(confSlider.value).toFixed(2);
  });
  confSlider.addEventListener("change", pushSettings);
}

loadSettings();
