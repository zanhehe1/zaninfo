let currentBot = null;
let logInterval = null;

function updateClock() {
  const now = new Date();
  document.getElementById("clock").textContent = now.toLocaleTimeString("vi-VN", { hour12: false });
  document.getElementById("date").textContent = now.toLocaleDateString("vi-VN");
}
setInterval(updateClock, 1000);
updateClock();

function fmtSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + " KB";
  return (bytes/1024/1024).toFixed(1) + " MB";
}

async function loadAll() {
  try {
    const r = await fetch("/api/bots");
    const d = await r.json();
    const grid = document.getElementById("botsGrid");
    if (!d.bots || d.bots.length === 0) {
      grid.innerHTML = '<div class="empty">Chưa có bot nào. Bấm <b>Tạo Bot Mới</b> để bắt đầu.</div>';
      return;
    }
    grid.innerHTML = d.bots.map(b => `
      <div class="bot-card" onclick="openBot('${b.id}')">
        <div class="bot-card-header">
          <div class="bot-card-name">🤖 ${b.id}</div>
          <div class="bot-card-status ${b.status.status === 'running' ? 'status-running' : 'status-stopped'}">
            ${b.status.status === 'running' ? '● RUNNING' : '○ STOPPED'}
          </div>
        </div>
        <div class="bot-card-info">
          Main: <code>${b.main_file}</code><br>
          Python: <code>${b.python_version}</code><br>
          ${b.note ? 'Note: ' + b.note + '<br>' : ''}
          Tạo: ${b.created}
        </div>
      </div>
    `).join("");
  } catch (e) {
    console.error(e);
  }
}

function openCreateModal() {
  document.getElementById("newBotId").value = "";
  document.getElementById("newMainFile").value = "start.py";
  document.getElementById("newPython").value = "python";
  document.getElementById("newNote").value = "";
  document.getElementById("createModal").classList.add("active");
}

function closeCreateModal() {
  document.getElementById("createModal").classList.remove("active");
}

async function createBot() {
  const bot_id = document.getElementById("newBotId").value.trim();
  const main_file = document.getElementById("newMainFile").value.trim() || "start.py";
  const python_version = document.getElementById("newPython").value;
  const note = document.getElementById("newNote").value.trim();

  if (!bot_id) {
    alert("Nhập ID bot");
    return;
  }

  try {
    const r = await fetch("/api/bots/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bot_id, main_file, python_version, note })
    });
    const d = await r.json();
    if (d.status === "ok") {
      closeCreateModal();
      loadAll();
    } else {
      alert("Lỗi: " + d.message);
    }
  } catch (e) {
    alert("Lỗi: " + e);
  }
}

function openBot(id) {
  currentBot = id;
  document.getElementById("botModalName").textContent = id;
  document.getElementById("botModal").classList.add("active");
  loadBotLog();
  loadBotFiles();
  if (logInterval) clearInterval(logInterval);
  logInterval = setInterval(loadBotLog, 3000);
}

function closeBotModal() {
  document.getElementById("botModal").classList.remove("active");
  currentBot = null;
  if (logInterval) {
    clearInterval(logInterval);
    logInterval = null;
  }
}

async function botAction(action) {
  if (!currentBot) return;
  try {
    const r = await fetch(`/api/bots/${currentBot}/${action}`, { method: "POST" });
    const d = await r.json();
    console.log(action, d);
  } catch (e) {
    alert("Lỗi: " + e);
  }
}

async function clearLog() {
  if (!currentBot) return;
  await fetch(`/api/bots/${currentBot}/clear-log`, { method: "POST" });
  loadBotLog();
}

async function deleteBot() {
  if (!currentBot) return;
  if (!confirm("Xóa bot " + currentBot + "?")) return;
  await fetch(`/api/bots/${currentBot}/delete`, { method: "DELETE" });
  closeBotModal();
  loadAll();
}

async function loadBotLog() {
  if (!currentBot) return;
  try {
    const r = await fetch(`/api/bots/${currentBot}/logs?lines=300`);
    const d = await r.json();
    const c = document.getElementById("console");
    c.innerHTML = "";
    if (!d.logs) {
      c.innerHTML = '<div class="console-line info">[SYSTEM] Chưa có log</div>';
      return;
    }
    const lines = d.logs.split("\n");
    for (const line of lines) {
      const div = document.createElement("div");
      div.className = "console-line";
      if (/error|exception|traceback|fail|lỗi/i.test(line)) div.classList.add("err");
      else if (/success|ok|started|connected|online/i.test(line)) div.classList.add("ok");
      else if (/warn|warning|cảnh báo/i.test(line)) div.classList.add("warn");
      else div.classList.add("info");
      div.textContent = line;
      c.appendChild(div);
    }
    c.scrollTop = c.scrollHeight;
  } catch (e) {
    console.error(e);
  }
}

async function loadBotFiles() {
  if (!currentBot) return;
  try {
    const r = await fetch(`/api/bots/${currentBot}/files`);
    const d = await r.json();
    const list = document.getElementById("filesList");
    if (!d.files || d.files.length === 0) {
      list.innerHTML = '<div class="empty">Chưa có file nào</div>';
      return;
    }
    list.innerHTML = d.files.map(f => `
      <div class="file-item">
        <i class="fas fa-file-code"></i>
        <span class="file-name">${f.name}</span>
        <span class="file-size">${fmtSize(f.size)}</span>
        <span class="file-actions">
          <button onclick="deleteFile('${f.name}')" title="Xóa">🗑️</button>
        </span>
      </div>
    `).join("");
  } catch (e) {
    console.error(e);
  }
}

async function deleteFile(path) {
  if (!currentBot) return;
  if (!confirm("Xóa " + path + "?")) return;
  await fetch(`/api/bots/${currentBot}/file?path=${encodeURIComponent(path)}`, { method: "DELETE" });
  loadBotFiles();
}

function switchTab(event, tab) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
  event.target.classList.add("active");
  document.getElementById("tab-" + tab).classList.add("active");
}

// ============ UPLOAD ============
const uploadZone = document.getElementById("uploadZone");
const fileInput = document.getElementById("fileInput");
const zipInput = document.getElementById("zipInput");

uploadZone.addEventListener("click", () => fileInput.click());
uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.classList.add("dragover"); });
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", async e => {
  e.preventDefault();
  uploadZone.classList.remove("dragover");
  await uploadFiles(e.dataTransfer.files);
});

fileInput.addEventListener("change", async () => {
  await uploadFiles(fileInput.files);
  fileInput.value = "";
});

zipInput.addEventListener("change", async () => {
  if (!currentBot || !zipInput.files[0]) return;
  const fd = new FormData();
  fd.append("file", zipInput.files[0]);
  try {
    const r = await fetch(`/api/bots/${currentBot}/upload-zip`, { method: "POST", body: fd });
    const d = await r.json();
    if (d.status === "ok") loadBotFiles();
    else alert("Lỗi: " + d.message);
  } catch (e) {
    alert("Lỗi: " + e);
  }
  zipInput.value = "";
});

async function uploadFiles(files) {
  if (!currentBot || !files.length) return;
  const fd = new FormData();
  for (const f of files) {
    fd.append("file", f, f.webkitRelativePath || f.name);
  }
  try {
    const r = await fetch(`/api/bots/${currentBot}/upload`, { method: "POST", body: fd });
    const d = await r.json();
    if (d.status === "ok") loadBotFiles();
    else alert("Lỗi: " + d.message);
  } catch (e) {
    alert("Lỗi: " + e);
  }
}

// ============ PING ============
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
      st.innerHTML = d.last.ok ? '<span class="pulse"></span> Hoạt động' : 'Lỗi';
      st.className = "stat-value " + (d.last.ok ? "ok" : "err");
      document.getElementById("ping-elapsed").textContent = d.last.elapsed;
    }
  } catch (e) { console.error(e); }
}

async function loadPingLogs() {
  try {
    const r = await fetch("/api/ping/logs");
    const d = await r.json();
    const box = document.getElementById("ping-log");
    if (!d.logs || d.logs.length === 0) {
      box.innerHTML = '<div class="empty">Chưa có log ping</div>';
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
  } catch (e) { console.error(e); }
}

async function pingNow() {
  try {
    await fetch("/api/ping/now");
    loadPingStatus();
    loadPingLogs();
  } catch (e) { alert("Lỗi: " + e); }
}

loadAll();
loadPingStatus();
loadPingLogs();
setInterval(loadAll, 10000);
setInterval(loadPingStatus, 15000);
setInterval(loadPingLogs, 30000);
