// app.js v3 — Dashboard: stats polling, signal/log/count updates

const ICONS = { ambulance: "🚑", firetruck: "🚒", police: "🚔" };

async function refreshStats() {
  try {
    const res  = await fetch("/stats");
    const data = await res.json();

    updateSignals(data.signals);
    updateCounts(data.counts);
    updateLog(data.log);

    const infEl = document.getElementById("footerInf");
    if (infEl) {
      infEl.textContent = `ໃຊ້ເວລາ: ${data.infer_ms ? data.infer_ms + " ms" : "--"}`;
    }

    if (data.model_info) {
      const mi = data.model_info;
      const ft = document.getElementById("footerModel");
      if (ft) ft.textContent = mi.name;
      const ps = document.getElementById("pageSub");
      if (ps) ps.textContent = `${mi.name} · ${mi.params}`;
    }
  } catch (_) {}
}

function updateSignals(signals) {
  document.querySelectorAll(".traffic-light").forEach(el => {
    const cam   = el.dataset.cam;
    const sig   = signals[cam] || "STOP";
    const clear = sig === "CLEAR";
    el.querySelector(".tl-bulb.r").classList.toggle("on", !clear);
    el.querySelector(".tl-bulb.g").classList.toggle("on",  clear);
    const status = el.querySelector(".tl-status");
    status.textContent = clear ? "CLEAR" : "STOP";
    status.className   = "tl-status " + (clear ? "clear" : "stop");
  });
}

function updateCounts(counts) {
  document.getElementById("cntAmb").textContent    = counts.ambulance || 0;
  document.getElementById("cntFire").textContent   = counts.firetruck || 0;
  document.getElementById("cntPolice").textContent = counts.police    || 0;
}

function updateLog(log) {
  const list = document.getElementById("alertList");
  if (!log || log.length === 0) {
    list.innerHTML = '<div class="empty-hint">ລໍຖ້າການກວດຈັບ...</div>';
    return;
  }
  list.innerHTML = log.map(item => `
    <div class="alert-item ${item.name}">
      <div class="alert-icon">${ICONS[item.name] || "🚨"}</div>
      <div class="alert-body">
        <div class="alert-type">${item.name}</div>
        <div class="alert-meta">${item.cam} · ${item.conf}% · ${item.t}</div>
      </div>
    </div>
  `).join("");
}

setInterval(refreshStats, 1000);
refreshStats();
