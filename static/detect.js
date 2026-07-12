// detect.js v3 — uses getModel()/getConf() from base.js; tab from URL

// ===== Tab activation =====
let webcamRunning = false;

function activateTab(target) {
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.add("hidden"));
  const pane = document.getElementById(`tab-${target}`);
  if (pane) pane.classList.remove("hidden");
  if (target !== "webcam" && webcamRunning) stopWebcam();
}

const INITIAL_TAB = (window.INITIAL_TAB || "image");
activateTab(INITIAL_TAB);

// ===== Helpers =====
const DET_COLORS = { ambulance: "#ea580c", firetruck: "#dc2626", police: "#2563eb" };
function detColor(name) { return DET_COLORS[name.toLowerCase()] || "#16a34a"; }

function makeDropZone(zoneEl, inputEl, onFileReady) {
  zoneEl.addEventListener("click", () => inputEl.click());
  inputEl.addEventListener("change", () => {
    if (inputEl.files[0]) {
      zoneEl.classList.add("has-file");
      zoneEl.querySelector(".upload-text").textContent = inputEl.files[0].name;
      onFileReady(inputEl.files[0]);
    }
  });
  zoneEl.addEventListener("dragover", e => { e.preventDefault(); zoneEl.classList.add("drag-over"); });
  zoneEl.addEventListener("dragleave", () => zoneEl.classList.remove("drag-over"));
  zoneEl.addEventListener("drop", e => {
    e.preventDefault();
    zoneEl.classList.remove("drag-over");
    const f = e.dataTransfer.files[0];
    if (f) {
      zoneEl.classList.add("has-file");
      zoneEl.querySelector(".upload-text").textContent = f.name;
      onFileReady(f);
    }
  });
}

// ===========================================================
// ຮູບພາບ
// ===========================================================
const imageFile      = document.getElementById("imageFile");
const imageDropZone  = document.getElementById("imageDropZone");
const imageDetectBtn = document.getElementById("imageDetectBtn");
const imageResult    = document.getElementById("imageResult");
const imageMeta      = document.getElementById("imageMeta");
const resultImg      = document.getElementById("resultImg");
const imageDetList   = document.getElementById("imageDetList");

let imageFileObj = null;

makeDropZone(imageDropZone, imageFile, f => {
  imageFileObj = f;
  imageDetectBtn.disabled = false;
  imageResult.classList.add("hidden");
});

imageDetectBtn.addEventListener("click", async () => {
  if (!imageFileObj) return;
  imageDetectBtn.disabled = true;
  imageDetectBtn.textContent = "ກຳລັງກວດຈັບ...";
  imageResult.classList.add("hidden");

  const fd = new FormData();
  fd.append("file", imageFileObj);
  fd.append("model_name", getModel());
  fd.append("conf", getConf());

  try {
    const res  = await fetch("/predict/image", { method: "POST", body: fd });
    const data = await res.json();
    if (data.error) { alert(data.error); return; }

    resultImg.src = `data:image/jpeg;base64,${data.image}`;
    imageMeta.innerHTML =
      `ໂມເດລ: <strong>${data.model_name}</strong> &nbsp;·&nbsp; ${data.model_params} &nbsp;·&nbsp; ` +
      `ປະມວນຜົນໃນ <strong>${data.infer_ms} ms</strong> &nbsp;·&nbsp; ` +
      `ພົບ <strong>${data.detections.length}</strong> ວັດຖຸ`;

    imageDetList.innerHTML = data.detections.length === 0
      ? '<div class="det-item">ບໍ່ພົບວັດຖຸ</div>'
      : data.detections.map(d => `
          <div class="det-item ${d.name.toLowerCase()}">
            <div class="det-name">${d.name}</div>
            <div class="det-conf">${Math.round(d.conf * 100)}% confidence</div>
          </div>`).join("");

    imageResult.classList.remove("hidden");
  } catch (e) {
    alert("ເກີດຂໍ້ຜິດພາດ: " + e.message);
  } finally {
    imageDetectBtn.disabled = false;
    imageDetectBtn.textContent = "ກວດຈັບ";
  }
});

// ===========================================================
// ວິດີໂອ
// ===========================================================
const videoFile       = document.getElementById("videoFile");
const videoDropZone   = document.getElementById("videoDropZone");
const videoDetectBtn  = document.getElementById("videoDetectBtn");
const videoProgress   = document.getElementById("videoProgress");
const progressText    = document.getElementById("progressText");
const videoResult     = document.getElementById("videoResult");
const videoMeta       = document.getElementById("videoMeta");
const videoStats      = document.getElementById("videoStats");
const videoSampleWrap = document.getElementById("videoSampleWrap");
const videoSampleImg  = document.getElementById("videoSampleImg");

let videoFileObj = null;

makeDropZone(videoDropZone, videoFile, f => {
  videoFileObj = f;
  videoDetectBtn.disabled = false;
  videoResult.classList.add("hidden");
});

videoDetectBtn.addEventListener("click", async () => {
  if (!videoFileObj) return;
  videoDetectBtn.disabled = true;
  videoDetectBtn.textContent = "ກຳລັງປະມວນຜົນ...";
  videoResult.classList.add("hidden");
  videoProgress.classList.remove("hidden");
  progressText.textContent = "ກຳລັງສົ່ງ ແລະ ປະມວນຜົນວິດີໂອ... ກະລຸນາລໍຖ້າ";

  const fd = new FormData();
  fd.append("file", videoFileObj);
  fd.append("model_name", getModel());
  fd.append("conf", getConf());

  try {
    const res  = await fetch("/predict/video", { method: "POST", body: fd });
    const data = await res.json();
    if (data.error) { alert(data.error); return; }

    videoMeta.innerHTML =
      `ໂມເດລ: <strong>${data.model_name}</strong> &nbsp;·&nbsp; ${data.model_params}`;

    const totalSec = (data.total_ms / 1000).toFixed(1);
    const detTotal = Object.values(data.detections_summary).reduce((a, b) => a + b, 0);

    videoStats.innerHTML = `
      <div class="vstat-card"><div class="vstat-num">${data.frame_count.toLocaleString()}</div><div class="vstat-lbl">FRAMES</div></div>
      <div class="vstat-card"><div class="vstat-num">${totalSec}s</div><div class="vstat-lbl">ເວລາ</div></div>
      <div class="vstat-card"><div class="vstat-num">${data.avg_ms_per_frame}</div><div class="vstat-lbl">ms / FRAME</div></div>
      <div class="vstat-card"><div class="vstat-num">${detTotal}</div><div class="vstat-lbl">ການກວດຈັບ</div></div>
    ` + Object.entries(data.detections_summary).map(([name, count]) => `
      <div class="vstat-card">
        <div class="vstat-num" style="color:${detColor(name)}">${count}</div>
        <div class="vstat-lbl">${name.toUpperCase()}</div>
      </div>`).join("");

    if (data.sample_frame) {
      videoSampleImg.src = `data:image/jpeg;base64,${data.sample_frame}`;
      videoSampleWrap.classList.remove("hidden");
    } else {
      videoSampleWrap.classList.add("hidden");
    }
    videoResult.classList.remove("hidden");
  } catch (e) {
    alert("ເກີດຂໍ້ຜິດພາດ: " + e.message);
  } finally {
    videoDetectBtn.disabled = false;
    videoDetectBtn.textContent = "ປະມວນຜົນວິດີໂອ";
    videoProgress.classList.add("hidden");
  }
});

// ===========================================================
// Webcam Real-time
// ===========================================================
const webcamVideo   = document.getElementById("webcamVideo");
const webcamCanvas  = document.getElementById("webcamCanvas");
const startBtn      = document.getElementById("startWebcam");
const stopBtn       = document.getElementById("stopWebcam");
const fpsOverlay    = document.getElementById("fpsOverlay");
const modelOverlay  = document.getElementById("modelOverlay");
const webcamError   = document.getElementById("webcamError");
const webcamHint    = document.getElementById("webcamHint");

let webcamStream = null;
let fpsSamples   = [];
const SEND_WIDTH   = 640;
const MIN_INTERVAL = 300;

async function startWebcam() {
  webcamError.classList.add("hidden");
  webcamHint.classList.add("hidden");
  try {
    webcamStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "environment" },
      audio: false,
    });
    webcamVideo.srcObject = webcamStream;
    await webcamVideo.play();
    webcamRunning    = true;
    startBtn.disabled = true;
    stopBtn.disabled  = false;
    fpsOverlay.textContent   = "-- FPS";
    modelOverlay.textContent = "--";
    fpsSamples = [];
    webcamDetectionLoop();
  } catch (err) {
    let msg = "ບໍ່ສາມາດເປີດກ້ອງໄດ້";
    if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError")
      msg = "❌ ບໍ່ໄດ້ຮັບອະນຸຍາດໃຊ້ກ້ອງ — ກະລຸນາອະນຸຍາດໃນ browser ແລ້ວລອງໃໝ່";
    else if (err.name === "NotFoundError")
      msg = "❌ ບໍ່ພົບກ້ອງ — ກະລຸນາເຊື່ອມຕໍ່ webcam ແລ້ວລອງໃໝ່";
    else if (err.name === "NotReadableError")
      msg = "❌ ກ້ອງກຳລັງຖືກໃຊ້ໂດຍ app ອື່ນ — ກະລຸນາປິດ app ອື່ນກ່ອນ";
    else
      msg = `❌ ${err.name}: ${err.message}`;
    webcamError.textContent = msg;
    webcamError.classList.remove("hidden");
  }
}

function stopWebcam() {
  webcamRunning = false;
  if (webcamStream) { webcamStream.getTracks().forEach(t => t.stop()); webcamStream = null; }
  webcamVideo.srcObject = null;
  webcamCanvas.getContext("2d").clearRect(0, 0, webcamCanvas.width, webcamCanvas.height);
  fpsOverlay.textContent = "-- FPS";
  startBtn.disabled = false;
  stopBtn.disabled  = true;
}

async function webcamDetectionLoop() {
  if (!webcamRunning) return;
  const t0 = performance.now();
  try {
    const ratio    = webcamVideo.videoHeight / webcamVideo.videoWidth;
    const sendH    = Math.round(SEND_WIDTH * ratio) || 480;
    const off      = document.createElement("canvas");
    off.width  = SEND_WIDTH; off.height = sendH;
    off.getContext("2d").drawImage(webcamVideo, 0, 0, SEND_WIDTH, sendH);
    const b64 = off.toDataURL("image/jpeg", 0.75);

    const resp = await fetch("/predict/webcam_frame", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: b64, model_name: getModel(), conf: getConf() }),
    });
    const data = await resp.json();

    const elapsed = performance.now() - t0;
    fpsSamples.push(elapsed);
    if (fpsSamples.length > 8) fpsSamples.shift();
    const avgMs = fpsSamples.reduce((a, b) => a + b, 0) / fpsSamples.length;
    const fps   = Math.round(1000 / avgMs);
    fpsOverlay.textContent   = `${fps} FPS · ${Math.round(data.infer_ms)}ms`;
    modelOverlay.textContent = `${data.model_name} · ${data.model_params}`;

    if (fps < 3) webcamHint.classList.remove("hidden");
    drawDetections(data.detections, SEND_WIDTH, sendH);
  } catch (e) { console.warn("webcam frame error:", e); }

  const spent = performance.now() - t0;
  if (webcamRunning) setTimeout(webcamDetectionLoop, Math.max(0, MIN_INTERVAL - spent));
}

function drawDetections(dets, srcW, srcH) {
  const ctx = webcamCanvas.getContext("2d");
  webcamCanvas.width  = webcamVideo.clientWidth  || 640;
  webcamCanvas.height = webcamVideo.clientHeight || 480;
  ctx.clearRect(0, 0, webcamCanvas.width, webcamCanvas.height);
  if (!dets || dets.length === 0) return;

  const scaleX = webcamCanvas.width  / srcW;
  const scaleY = webcamCanvas.height / srcH;
  ctx.font = "bold 13px Inter, 'Segoe UI', sans-serif";

  for (const det of dets) {
    const [x1, y1, x2, y2] = det.box;
    const color = detColor(det.name);
    const label = `${det.name.toUpperCase()} ${Math.round(det.conf * 100)}%`;
    ctx.strokeStyle = color; ctx.lineWidth = 2;
    ctx.strokeRect(x1 * scaleX, y1 * scaleY, (x2 - x1) * scaleX, (y2 - y1) * scaleY);
    const tw = ctx.measureText(label).width;
    ctx.fillStyle = color;
    ctx.fillRect(x1 * scaleX, y1 * scaleY - 20, tw + 10, 20);
    ctx.fillStyle = "#ffffff";
    ctx.fillText(label, x1 * scaleX + 5, y1 * scaleY - 5);
  }
}

startBtn.addEventListener("click", startWebcam);
stopBtn.addEventListener("click",  stopWebcam);
