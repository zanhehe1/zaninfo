// ============ CLOCK ============
function updateClock() {
  const now = new Date();
  document.getElementById("clock").textContent =
    now.toLocaleTimeString("vi-VN", { hour12: false });
  document.getElementById("date").textContent =
    now.toLocaleDateString("vi-VN");
}
setInterval(updateClock, 1000);
updateClock();

// ============ TAB SWITCH ============
function switchTab(event, tab) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
  event.target.classList.add("active");
  document.getElementById("tab-" + tab).classList.add("active");
}

// ============ CONSOLE ============
let consoleLines = [];

function log(msg, type = "info") {
  const c = document.getElementById("console");
  const time = new Date().toLocaleTimeString("vi-VN", { hour12: false });
  consoleLines.push({ time, msg, type });
  if (consoleLines.length > 500) consoleLines.shift();
  const div = document.createElement("div");
  div.className = "console-line " + type;
  div.textContent = `[${time}] ${msg}`;
  c.appendChild(div);
  c.scrollTop = c.scrollHeight;
}

function clearConsole() {
  consoleLines = [];
  document.getElementById("console").innerHTML =
    '<div class="console-line info">[SYSTEM] Console đã được xóa</div>';
}

function sendCmd() {
  const input = document.getElementById("cmdInput");
  const cmd = input.value.trim();
  if (!cmd) return;
  log(cmd, "cmd");
  input.value = "";
  fetch("/api/cmd", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cmd })
  }).catch(() => {});
}

// ============ BOT CONTROLS ============
async function botAction(action) {
  log(`Đang ${action}...`, "warn");
  try {
    const r = await fetch(`/api/bots/bot1/${action}`, { method: "POST" });
    const d = await r.json();
    log(`${action}: ${d.status}`, d.status.includes("error") ? "err" : "ok");
  } catch (e) {
    log(`${action} lỗi: ${e}`, "err");
  }
}

const startBot = () => botAction("start");
const stopBot = () => botAction("stop");
const restartBot = () => botAction("restart");

// ============ UPLOAD ============
const uploadZone = document.getElementById("uploadZone");
const fileInput = document.getElementById("fileInput");

uploadZone.addEventListener("click", () => fileInput.click());
uploadZone.addEventListener("dragover", e => {
  e.preventDefault();
  uploadZone.classList.add("dragover");
});
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", async e => {
  e.preventDefault();
  uploadZone.classList.remove("dragover");
  for (const file of e.dataTransfer.files) {
    await uploadFile(file);
  }
});
fileInput.addEventListener("change", async () => {
  for (const file of fileInput.files) {
    await uploadFile(file);
  }
  fileInput.value = "";
});

async function uploadFile(file) {
  const fd = new FormData();
  fd.append("file", file);
  log(`Đang upload ${file.name}...`, "warn");
  try {
    const r = await fetch("/api/bots/bot1/upload", { method: "POST", body: fd });
    const d = await r.json();
    if (d.status === "ok") log(`Upload OK: ${file.name}`, "ok");
    else log(`Upload lỗi: ${d.message}`, "err");
  } catch (e) {
    log(`Upload lỗi: ${e}`, "err");
  }
  refreshFiles();
}

async function refreshFiles() {
  try {
    const r = await fetch("/api/bots");
    const d = await r.json();
    const list = document.getElementById("filesList");
    if (!d.bots || d.bots.length === 0) {
      list.innerHTML = '<div class="empty">Chưa có bot nào</div>';
      return;
    }
    list.innerHTML = d.bots.map(b => `
      <div class="file-item">
        <div><i class="fas fa-folder"></i><b>${b.id}</b> — ${b.status.status}</div>
        <div>${b.created}</div>
      </div>
    `).join("");
  } catch (e) {
    console.error(e);
  }
}

async function createBot() {
  const id = prompt("Nhập ID bot mới (chữ + số + _):");
  if (!id) return;
  const r = await fetch("/api/bots/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bot_id: id })
  });
  const d = await r.json();
  if (d.status === "ok") {
    log(`Đã tạo bot ${d.bot_id}`, "ok");
    refreshFiles();
  } else {
    log(`Lỗi: ${d.message}`, "err");
  }
}

// ============ PING MONITOR ============
async function loadPingStatus() {
  try {
    const r = await fetch("/api/ping/status");
    const d = await r.json();
    document.getElementById("ping-total").textContent = d.total;

    if (d.last) {
      const code = document.getElementById("ping-code");
      code.textContent = d.last.status;
      code.className = "stat-value " + (d.last.ok ? "ok" : "err");

      const st = document.getElementById("ping-status");
      st.innerHTML = d.last.ok
        ? '<span class="pulse"></span> Hoạt động'
        : 'Lỗi';
      st.className = "stat-value " + (d.last.ok ? "ok" : "err");

      document.getElementById("ping-elapsed").textContent = d.last.elapsed;
    }
  } catch (e) {
    console.error(e);
  }
}

async function loadPingLogs() {
  try {
    const r = await fetch("/api/ping/logs");
    const d = await r.json();
    const box = document.getElementById("ping-log");
    if (!d.logs || d.logs.length === 0) {
      box.innerHTML = '<div class="empty">Chưa có log</div>';
      return;
    }
    box.innerHTML = d.logs.map(item => `
      <div class="ping-item">
        <span class="ping-time">${item.date} ${item.time}</span>
        <span class="${item.ok ? 'ping-status-ok' : 'ping-status-err'}">
          ${item.ok ? '✅' : '❌'} ${item.status}
        </span>
        <span class="ping-elapsed">${item.elapsed}</span>
      </div>
    `).join("");
  } catch (e) {
    console.error(e);
  }
}

async function pingNow() {
  log("Đang ping thủ công...", "warn");
  try {
    await fetch("/api/ping/now");
    await loadPingStatus();
    await loadPingLogs();
    log("Ping xong", "ok");
  } catch (e) {
    log("Ping lỗi: " + e, "err");
  }
}

// ============ LOOP ============
refreshFiles();
loadPingStatus();
loadPingLogs();
setInterval(loadPingStatus, 10000);
setInterval(loadPingLogs, 30000);
setInterval(refreshFiles, 15000);
log("Panel đã khởi động", "ok");
