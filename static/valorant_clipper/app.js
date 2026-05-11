const $ = (id) => document.getElementById(id);

let currentJob = null;
let pollTimer = null;
let videos = [];

function formatSeconds(value) {
  if (!Number.isFinite(value)) return "-";
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function formatSize(bytes) {
  if (!Number.isFinite(bytes)) return "";
  const gb = bytes / 1024 / 1024 / 1024;
  if (gb >= 1) return `${gb.toFixed(2)} GB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function setStatus(text, detail = "") {
  $("statusText").textContent = text;
  $("statusDetail").textContent = detail;
}

function setProgress(value) {
  $("progressBar").style.width = `${Math.round((value || 0) * 100)}%`;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body.detail || body.error || message;
    } catch (_) {}
    throw new Error(message);
  }
  return response.json();
}

async function loadDefaults() {
  const data = await api("/api/defaults");
  $("sourceDir").value = data.source_dir;
  $("outputDir").value = data.output_dir;
}

function renderVideoOptions() {
  const select = $("videoSelect");
  select.innerHTML = "";
  for (const video of videos) {
    const option = document.createElement("option");
    option.value = video.path;
    option.textContent = `${video.name} · ${formatSeconds(video.duration)} · ${formatSize(video.size_bytes)}`;
    select.appendChild(option);
  }
  $("videoCount").textContent = videos.length ? `${videos.length} 个视频` : "";
}

async function scanVideos() {
  setStatus("扫描中", "正在读取视频时长");
  const root = encodeURIComponent($("sourceDir").value.trim());
  const recursive = $("recursive").checked ? "true" : "false";
  videos = await api(`/api/videos?root=${root}&recursive=${recursive}`);
  renderVideoOptions();
  setStatus("扫描完成", videos.length ? "选择一个视频开始剪辑" : "没有找到视频");
}

async function choosePath(kind, targetInput, prompt) {
  setStatus("等待选择", "系统选择框已经打开");
  const data = await api("/api/choose-path", {
    method: "POST",
    body: JSON.stringify({ kind, prompt }),
  });
  $(targetInput).value = data.path;
  if (targetInput === "sourceDir") {
    await scanVideos();
  } else {
    setStatus("输出目录已选择", data.path);
  }
}

function pathFromDrop(event) {
  const uriList = event.dataTransfer.getData("text/uri-list");
  const text = event.dataTransfer.getData("text/plain");
  const raw = uriList || text;
  if (!raw) return "";

  const firstLine = raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line && !line.startsWith("#"));
  if (!firstLine) return "";

  try {
    if (firstLine.startsWith("file://")) {
      return decodeURIComponent(new URL(firstLine).pathname);
    }
  } catch (_) {}
  return firstLine;
}

function setupDropZone() {
  const dropZone = $("dropZone");

  for (const eventName of ["dragenter", "dragover"]) {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("isDragging");
    });
  }

  for (const eventName of ["dragleave", "drop"]) {
    dropZone.addEventListener(eventName, () => dropZone.classList.remove("isDragging"));
  }

  dropZone.addEventListener("drop", async (event) => {
    event.preventDefault();
    const path = pathFromDrop(event);
    if (!path) {
      setStatus("无法读取拖入路径", "请使用“选择文件夹”或“选择视频文件”按钮");
      return;
    }
    $("sourceDir").value = path;
    await scanVideos();
  });
}

function jobPayload() {
  const maxSeconds = $("maxSeconds").value.trim();
  return {
    input_path: $("videoSelect").value,
    output_dir: $("outputDir").value.trim(),
    confidence: Number($("confidence").value),
    framerate: Number($("framerate").value),
    seconds_before: Number($("secondsBefore").value),
    seconds_after: Number($("secondsAfter").value),
    merge_gap_seconds: Number($("mergeGap").value),
    max_seconds: maxSeconds ? Number(maxSeconds) : null,
    strict_own_kills: $("strictOwnKills").checked,
    min_event_seconds: Number($("minEventSeconds").value),
    copy_streams: $("copyStreams").checked,
  };
}

function renderClips(segments) {
  const grid = $("clipGrid");
  grid.innerHTML = "";
  if (!segments.length) {
    grid.className = "clipGrid empty";
    const empty = document.createElement("p");
    empty.textContent = "没有检测到高光片段。可以降低置信度，或增加测试秒数后重试。";
    grid.appendChild(empty);
    return;
  }

  grid.className = "clipGrid";
  for (const segment of segments) {
    const card = document.createElement("article");
    card.className = "clipCard";
    card.innerHTML = `
      <video src="${segment.url}" controls preload="metadata"></video>
      <div class="clipMeta">
        <strong>${segment.name}</strong>
        <span>${segment.start.toFixed(2)}s - ${segment.end.toFixed(2)}s · ${segment.duration.toFixed(2)}s</span>
        <div class="clipFacts">
          <span class="pill kill">约 ${segment.kills || 1} 杀</span>
        </div>
      </div>
    `;
    grid.appendChild(card);
  }
}

async function pollJob() {
  if (!currentJob) return;
  const job = await api(`/api/jobs/${currentJob}`);
  setProgress(job.progress);
  setStatus(job.status === "error" ? "出错了" : job.status === "done" ? "剪辑完成" : "运行中", job.message);
  $("logBox").textContent = (job.logs || []).join("\n");

  if (job.status === "done" || job.status === "error") {
    clearInterval(pollTimer);
    pollTimer = null;
    $("startButton").disabled = false;
    renderClips(job.segments || []);
  }
}

async function startJob() {
  if (!$("videoSelect").value) {
    setStatus("没有选择视频", "先扫描并选择一个素材");
    return;
  }
  $("startButton").disabled = true;
  $("clipGrid").innerHTML = "<p>正在处理，片段出来后会自动显示。</p>";
  $("clipGrid").className = "clipGrid empty";
  setProgress(0);
  setStatus("任务已提交", "准备启动后台剪辑");

  const job = await api("/api/jobs", {
    method: "POST",
    body: JSON.stringify(jobPayload()),
  });
  currentJob = job.id;
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollJob, 1200);
  await pollJob();
}

window.addEventListener("DOMContentLoaded", async () => {
  $("scanButton").addEventListener("click", () => scanVideos().catch((error) => setStatus("扫描失败", error.message)));
  $("refreshVideos").addEventListener("click", () => scanVideos().catch((error) => setStatus("扫描失败", error.message)));
  $("chooseFolderButton").addEventListener("click", () => choosePath("folder", "sourceDir", "选择素材文件夹").catch((error) => setStatus("选择失败", error.message)));
  $("chooseFileButton").addEventListener("click", () => choosePath("file", "sourceDir", "选择 Valorant 视频").catch((error) => setStatus("选择失败", error.message)));
  $("chooseOutputButton").addEventListener("click", () => choosePath("folder", "outputDir", "选择输出目录").catch((error) => setStatus("选择失败", error.message)));
  $("startButton").addEventListener("click", () => startJob().catch((error) => {
    $("startButton").disabled = false;
    setStatus("启动失败", error.message);
  }));

  setupDropZone();
  await loadDefaults();
  await scanVideos();
});
