// history.js v1 — ดึง /api/history แล้ว render สรุป/กราฟ/ตาราง

const ICONS = { ambulance: "🚑", firetruck: "🚒", police: "🚔" };
const LAO   = { ambulance: "ລົດພະຍາບານ", firetruck: "ລົດດັບເພີງ", police: "ຕຳຫຼວດ" };
const SHORT = { ambulance: "amb", firetruck: "fire", police: "police" };

let currentRange = "7d";

async function loadHistory() {
  try {
    const res  = await fetch(`/api/history?range=${currentRange}`);
    const data = await res.json();
    renderSummary(data);
    renderDaily(data.daily);
    renderHourly(data.hourly, data.peakHour);
    renderCameras(data.byCamera);
    renderRecent(data.recent);
  } catch (e) {
    console.warn("history load error:", e);
  }
}

function renderSummary(d) {
  const t = d.totals || {};
  document.getElementById("sumAll").textContent    = (t.all || 0).toLocaleString();
  document.getElementById("sumAmb").textContent    = (t.ambulance || 0).toLocaleString();
  document.getElementById("sumFire").textContent   = (t.firetruck || 0).toLocaleString();
  document.getElementById("sumPolice").textContent = (t.police || 0).toLocaleString();
  document.getElementById("sumPeak").textContent   =
    d.peakHour === null || d.peakHour === undefined ? "–" : `${d.peakHour}:00`;
}

function renderDaily(daily) {
  const el = document.getElementById("dailyChart");
  const max = Math.max(1, ...daily.map(d => d.total));
  const H = 150;
  el.innerHTML = daily.map(d => {
    const stackPx = Math.round(d.total / max * H);
    const seg = cls => d[cls]
      ? `<div class="day-seg ${SHORT[cls]}" style="height:${Math.max(Math.round(d[cls] / d.total * stackPx), 1)}px"></div>`
      : "";
    return `<div class="day-col" title="${d.date} · ${d.total}">
      <div class="day-total">${d.total || ""}</div>
      <div class="day-stack" style="height:${stackPx}px">
        ${seg("ambulance")}${seg("firetruck")}${seg("police")}
      </div>
      <div class="day-label">${fmtDay(d.date)}</div>
    </div>`;
  }).join("");
}

function renderHourly(hourly, peak) {
  const el = document.getElementById("hourlyChart");
  const max = Math.max(1, ...hourly.map(h => h.count));
  const H = 120;
  el.innerHTML = hourly.map(h => {
    const px  = Math.round(h.count / max * H);
    const cls = h.count === 0 ? "empty" : (h.hour === peak ? "peak" : "");
    const lbl = h.hour % 3 === 0 ? h.hour : "";
    return `<div class="hour-bar-wrap">
      <div class="hour-bar ${cls}" style="height:${Math.max(px, 2)}px" title="${h.hour}:00 · ${h.count}"></div>
      <div class="hour-lbl">${lbl}</div>
    </div>`;
  }).join("");
}

function renderCameras(cams) {
  const el = document.getElementById("cameraBars");
  const max = Math.max(1, ...cams.map(c => c.count));
  el.innerHTML = cams.map(c => {
    const pct = Math.round(c.count / max * 100);
    return `<div class="cam-row">
      <div class="cam-name">${c.label}</div>
      <div class="cam-track"><div class="cam-fill" style="width:${Math.max(pct, 2)}%"></div></div>
      <div class="cam-count">${c.count}</div>
    </div>`;
  }).join("");
}

function renderRecent(recent) {
  const el = document.getElementById("recentTable");
  if (!recent || recent.length === 0) {
    el.innerHTML = '<div class="hist-empty">ຍັງບໍ່ມີຂໍ້ມູນການກວດຈັບ</div>';
    return;
  }
  el.innerHTML = recent.map(r => `
    <div class="rec-row">
      <div class="rec-ico">${ICONS[r.name] || "🚨"}</div>
      <div class="rec-name ${SHORT[r.name] || ""}">${LAO[r.name] || r.name}</div>
      <div class="rec-cam">${r.cam}</div>
      <div class="rec-time">${r.t}</div>
    </div>`).join("");
}

function fmtDay(dateStr) {
  const p = dateStr.split("-");           // YYYY-MM-DD → D/M
  return p.length === 3 ? `${+p[2]}/${+p[1]}` : dateStr;
}

// ===== Range tabs =====
document.getElementById("rangeTabs").addEventListener("click", e => {
  const btn = e.target.closest(".range-btn");
  if (!btn) return;
  document.querySelectorAll(".range-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  currentRange = btn.dataset.range;
  loadHistory();
});

loadHistory();
