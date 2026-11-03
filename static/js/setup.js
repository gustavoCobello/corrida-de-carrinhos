(() => {
  "use strict";

  const body = document.body;
  const pollMs = Math.max(200, Number(body.dataset.pollMs) || 500);
  const initial = window.__SETUP_INITIAL__ || {};

  const elements = {
    frame: document.getElementById("calibration-frame"),
    canvas: document.getElementById("setup-canvas"),
    stream: document.getElementById("setup-stream"),
    placeholder: document.getElementById("stream-placeholder"),
    hint: document.getElementById("setup-hint"),
    stepBadge: document.getElementById("step-badge"),
    point1: document.getElementById("point-1"),
    point2: document.getElementById("point-2"),
    result: document.getElementById("result-readout"),
    pixelReadout: document.getElementById("pixel-readout"),
    saveButton: document.getElementById("save-btn"),
    clearButton: document.getElementById("clear-btn"),
    saveNote: document.getElementById("save-note"),
    modeLine: document.getElementById("mode-line"),
    modeRoi: document.getElementById("mode-roi"),
    cameraPill: document.getElementById("camera-pill"),
    cameraStatusLabel: document.getElementById("camera-status-label"),
    cameraFps: document.getElementById("camera-fps"),
    cameraSource: document.getElementById("camera-source"),
    cameraCapture: document.getElementById("camera-capture"),
    cameraProcess: document.getElementById("camera-process"),
    cameraError: document.getElementById("camera-error"),
    savedLine: document.getElementById("saved-line"),
    savedRoi: document.getElementById("saved-roi"),
    liveBadge: document.getElementById("live-badge"),
    liveLabel: document.getElementById("live-label"),
    sourceBadge: document.getElementById("source-badge"),
    serverClock: document.getElementById("server-clock"),
    toast: document.getElementById("toast"),
  };

  const state = {
    mode: "line",
    draft: [],
    saving: false,
    streamVisible: false,
    saved: {
      line: initial.line || null,
      roi: initial.roi || null,
    },
    process: {
      width: initial.process?.[0] || 960,
      height: initial.process?.[1] || 540,
    },
    camera: {},
  };

  let toastTimer = null;

  function clamp01(value) {
    return Math.min(1, Math.max(0, value));
  }

  function formatPercent(value) {
    return `${(value * 100).toFixed(1).replace(".", ",")}%`;
  }

  function formatPoint(point) {
    if (!Array.isArray(point) || point.length !== 2) {
      return "--";
    }
    return `${formatPercent(point[0])}, ${formatPercent(point[1])}`;
  }

  function formatPixels(point) {
    if (!Array.isArray(point) || point.length !== 2) {
      return "--";
    }
    return `${Math.round(point[0] * state.process.width)}, ${Math.round(point[1] * state.process.height)}`;
  }

  function formatClock(isoDate) {
    const date = isoDate ? new Date(isoDate) : new Date();
    if (Number.isNaN(date.getTime())) {
      return "--:--:--";
    }
    return date.toLocaleTimeString("pt-BR");
  }

  function setStatus(kind, label) {
    elements.cameraPill.className = `status-pill status-pill--${kind}`;
    elements.cameraStatusLabel.textContent = label;
  }

  function showToast(message, isError = false) {
    elements.toast.textContent = message;
    elements.toast.classList.toggle("is-error", isError);
    elements.toast.classList.add("is-visible");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      elements.toast.classList.remove("is-visible");
    }, 2800);
  }

  function roiFromPoints(points) {
    if (points.length !== 2) {
      return null;
    }
    const [a, b] = points;
    return {
      x: Math.min(a[0], b[0]),
      y: Math.min(a[1], b[1]),
      w: Math.abs(a[0] - b[0]),
      h: Math.abs(a[1] - b[1]),
    };
  }

  function roiFromDraft() {
    return roiFromPoints(state.draft);
  }

  function draftDistance() {
    if (state.draft.length !== 2) {
      return 0;
    }
    const [a, b] = state.draft;
    return Math.hypot(a[0] - b[0], a[1] - b[1]);
  }

  function draftValid() {
    if (state.draft.length !== 2) {
      return false;
    }
    if (state.mode === "line") {
      return draftDistance() > 0.02;
    }
    const roi = roiFromDraft();
    return Boolean(roi && roi.w > 0.02 && roi.h > 0.02);
  }

  function updateHint() {
    const count = state.draft.length;
    if (state.mode === "line") {
      if (count === 0) {
        elements.hint.textContent = "Clique no primeiro ponto da linha de chegada.";
      } else if (count === 1) {
        elements.hint.textContent = "Agora clique no segundo ponto, na outra extremidade da linha.";
      } else if (draftValid()) {
        elements.hint.textContent = "Confira o traçado e clique em Salvar linha.";
      } else {
        elements.hint.textContent = "Os pontos estão muito próximos. Clique em dois pontos distintos.";
      }
    } else if (count === 0) {
      elements.hint.textContent = "Clique no primeiro canto da área que contém a pista.";
    } else if (count === 1) {
      elements.hint.textContent = "Clique no canto oposto para fechar a área de interesse.";
    } else if (draftValid()) {
      elements.hint.textContent = "Confira a área destacada e clique em Salvar ROI.";
    } else {
      elements.hint.textContent = "A área é muito pequena. Clique em dois cantos mais afastados.";
    }
  }

  function updateReadout() {
    elements.point1.textContent = formatPoint(state.draft[0]);
    elements.point2.textContent = formatPoint(state.draft[1]);

    if (state.mode === "line") {
      if (state.draft.length === 2) {
        elements.result.textContent = `${formatPoint(state.draft[0])} → ${formatPoint(state.draft[1])}`;
        elements.pixelReadout.textContent = `${formatPixels(state.draft[0])} → ${formatPixels(state.draft[1])}`;
      } else {
        elements.result.textContent = "--";
        elements.pixelReadout.textContent = "--";
      }
    } else {
      const roi = roiFromDraft();
      if (roi) {
        elements.result.textContent = `x ${formatPercent(roi.x)} · y ${formatPercent(roi.y)} · ${formatPercent(roi.w)} × ${formatPercent(roi.h)}`;
        elements.pixelReadout.textContent = `${Math.round(roi.x * state.process.width)}, ${Math.round(roi.y * state.process.height)} · ${Math.round(roi.w * state.process.width)} × ${Math.round(roi.h * state.process.height)}`;
      } else {
        elements.result.textContent = "--";
        elements.pixelReadout.textContent = "--";
      }
    }

    const count = state.draft.length;
    if (count === 0) {
      elements.stepBadge.textContent = "Passo 1 de 2";
    } else if (count === 1) {
      elements.stepBadge.textContent = "Passo 2 de 2";
    } else {
      elements.stepBadge.textContent = "Pronto";
    }

    elements.saveButton.textContent = state.mode === "line" ? "Salvar linha" : "Salvar ROI";
    elements.saveButton.disabled = !draftValid() || state.saving;
    elements.clearButton.disabled = count === 0 || state.saving;

    if (state.saving) {
      elements.saveNote.textContent = "Salvando...";
    } else if (draftValid()) {
      elements.saveNote.textContent = "Seleção pronta. Salve para aplicar ao vídeo.";
    } else {
      elements.saveNote.textContent = "Clique em dois pontos para liberar o salvamento.";
    }
  }

  function updateModeUi() {
    const isLine = state.mode === "line";
    elements.modeLine.classList.toggle("is-active", isLine);
    elements.modeRoi.classList.toggle("is-active", !isLine);
    elements.modeLine.setAttribute("aria-selected", String(isLine));
    elements.modeRoi.setAttribute("aria-selected", String(!isLine));
    elements.saveButton.textContent = isLine ? "Salvar linha" : "Salvar ROI";
    updateHint();
    updateReadout();
  }

  function updateSavedInfo() {
    const line = state.saved.line;
    if (line && Array.isArray(line.p1) && Array.isArray(line.p2)) {
      elements.savedLine.textContent = `${formatPoint(line.p1)} → ${formatPoint(line.p2)}`;
    } else {
      elements.savedLine.textContent = "--";
    }

    const roi = state.saved.roi;
    if (!roi) {
      elements.savedRoi.textContent = "--";
    } else if (roi.x === 0 && roi.y === 0 && roi.w === 1 && roi.h === 1) {
      elements.savedRoi.textContent = "quadro inteiro";
    } else {
      elements.savedRoi.textContent = `x ${formatPercent(roi.x)} · y ${formatPercent(roi.y)} · ${formatPercent(roi.w)} × ${formatPercent(roi.h)}`;
    }
  }

  function contentRect() {
    const rect = elements.frame.getBoundingClientRect();
    const aspect = state.process.width / state.process.height;
    let width = rect.width;
    let height = width / aspect;
    if (height > rect.height) {
      height = rect.height;
      width = height * aspect;
    }
    return {
      left: (rect.width - width) / 2,
      top: (rect.height - height) / 2,
      width,
      height,
    };
  }

  function canvasPoint(point) {
    const content = contentRect();
    return {
      x: content.left + point[0] * content.width,
      y: content.top + point[1] * content.height,
    };
  }

  function resizeCanvas() {
    const rect = elements.frame.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) {
      return;
    }
    const dpr = window.devicePixelRatio || 1;
    elements.canvas.width = Math.round(rect.width * dpr);
    elements.canvas.height = Math.round(rect.height * dpr);
    elements.canvas.style.width = `${rect.width}px`;
    elements.canvas.style.height = `${rect.height}px`;
    draw();
  }

  function drawSavedLayer(ctx) {
    const line = state.saved.line;
    if (line && Array.isArray(line.p1) && Array.isArray(line.p2)) {
      const a = canvasPoint(line.p1);
      const b = canvasPoint(line.p2);
      ctx.save();
      ctx.setLineDash([6, 5]);
      ctx.strokeStyle = "rgba(245, 247, 250, 0.9)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = "rgba(245, 247, 250, 0.9)";
      for (const point of [a, b]) {
        ctx.beginPath();
        ctx.arc(point.x, point.y, 3.5, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }

    const roi = state.saved.roi;
    if (roi && !(roi.x === 0 && roi.y === 0 && roi.w === 1 && roi.h === 1)) {
      const a = canvasPoint([roi.x, roi.y]);
      const b = canvasPoint([roi.x + roi.w, roi.y + roi.h]);
      ctx.save();
      ctx.setLineDash([5, 5]);
      ctx.strokeStyle = "rgba(251, 191, 36, 0.8)";
      ctx.lineWidth = 1.5;
      ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
      ctx.restore();
    }
  }

  function drawDraftLayer(ctx) {
    if (state.mode === "roi" && state.draft.length === 2) {
      const roi = roiFromDraft();
      const a = canvasPoint([roi.x, roi.y]);
      const b = canvasPoint([roi.x + roi.w, roi.y + roi.h]);
      ctx.save();
      ctx.fillStyle = "rgba(34, 211, 238, 0.1)";
      ctx.fillRect(a.x, a.y, b.x - a.x, b.y - a.y);
      ctx.setLineDash([7, 5]);
      ctx.strokeStyle = "#22d3ee";
      ctx.lineWidth = 2;
      ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
      ctx.restore();
    }

    if (state.mode === "line" && state.draft.length === 2) {
      const a = canvasPoint(state.draft[0]);
      const b = canvasPoint(state.draft[1]);
      ctx.save();
      ctx.strokeStyle = "#22d3ee";
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
      ctx.restore();
    }

    state.draft.forEach((point, index) => {
      const canvas = canvasPoint(point);
      ctx.save();
      ctx.fillStyle = "#22d3ee";
      ctx.strokeStyle = "#041016";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(canvas.x, canvas.y, 5.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = "#041016";
      ctx.font = "700 9px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(String(index + 1), canvas.x, canvas.y + 0.5);
      ctx.restore();
    });
  }

  function draw() {
    const ctx = elements.canvas.getContext("2d");
    if (!ctx) {
      return;
    }
    const dpr = window.devicePixelRatio || 1;
    const width = elements.canvas.width / dpr;
    const height = elements.canvas.height / dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    drawSavedLayer(ctx);
    drawDraftLayer(ctx);
  }

  function onCanvasClick(event) {
    const rect = elements.frame.getBoundingClientRect();
    const content = contentRect();
    const x = (event.clientX - rect.left - content.left) / content.width;
    const y = (event.clientY - rect.top - content.top) / content.height;
    if (x < 0 || x > 1 || y < 0 || y > 1) {
      return;
    }

    if (state.draft.length >= 2) {
      state.draft = [];
    }
    state.draft.push([clamp01(x), clamp01(y)]);
    updateHint();
    updateReadout();
    draw();
  }

  function switchMode(mode) {
    if (state.mode === mode) {
      return;
    }
    state.mode = mode;
    state.draft = [];
    updateModeUi();
    draw();
  }

  function clearDraft() {
    state.draft = [];
    updateHint();
    updateReadout();
    draw();
  }

  async function saveSelection() {
    if (!draftValid() || state.saving) {
      return;
    }

    const mode = state.mode;
    const draft = state.draft.map((point) => [...point]);
    state.saving = true;
    updateReadout();

    try {
      let response;
      if (mode === "line") {
        response = await fetch("/api/config/line", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ p1: draft[0], p2: draft[1] }),
        });
      } else {
        response = await fetch("/api/config/roi", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ roi: roiFromPoints(draft) }),
        });
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Falha ao salvar a calibração.");
      }

      if (mode === "line") {
        state.saved.line = data.line;
      } else {
        state.saved.roi = data.roi;
      }

      if (state.mode === mode) {
        state.draft = [];
      }
      updateModeUi();
      updateSavedInfo();
      draw();
      showToast(
        mode === "line"
          ? "Linha de chegada salva e aplicada ao vídeo."
          : "Área de interesse salva e aplicada ao vídeo.",
      );
    } catch (error) {
      showToast(error.message || "Não foi possível salvar.", true);
    } finally {
      state.saving = false;
      updateReadout();
    }
  }

  function updateCamera(camera) {
    const streaming = camera.status === "streaming";

    if (streaming) {
      setStatus("live", "Ao vivo");
    } else if (camera.status === "starting") {
      setStatus("waiting", "Conectando");
    } else {
      setStatus("offline", "Offline");
    }

    elements.cameraFps.textContent = streaming
      ? `${Number(camera.fps || 0).toFixed(1)} FPS`
      : "-- FPS";
    elements.cameraSource.textContent =
      camera.source === "demo" ? "Demonstração" : "Webcam";
    elements.cameraCapture.textContent =
      camera.capture_width && camera.capture_height
        ? `${camera.capture_width}×${camera.capture_height}`
        : "--";
    elements.cameraProcess.textContent =
      camera.process_width && camera.process_height
        ? `${camera.process_width}×${camera.process_height}`
        : "--";

    elements.sourceBadge.textContent = camera.source === "demo" ? "DEMO" : "WEBCAM";
    elements.liveBadge.classList.toggle("is-offline", !streaming);
    elements.liveLabel.textContent = streaming ? "AO VIVO" : "SEM SINAL";

    if (camera.error) {
      elements.cameraError.textContent = camera.error;
      elements.cameraError.classList.remove("hidden");
    } else {
      elements.cameraError.textContent = "";
      elements.cameraError.classList.add("hidden");
    }

    if ((streaming || camera.status === "offline") && !state.streamVisible) {
      state.streamVisible = true;
      elements.placeholder.classList.add("is-hidden");
    }
  }

  async function poll() {
    try {
      const response = await fetch("/api/state", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      state.camera = data.camera || {};

      if (state.camera.process_width && state.camera.process_height) {
        state.process.width = state.camera.process_width;
        state.process.height = state.camera.process_height;
      }

      if (data.config?.line) {
        state.saved.line = data.config.line;
      }
      if (data.config?.roi) {
        state.saved.roi = data.config.roi;
      }

      updateCamera(state.camera);
      updateSavedInfo();
      elements.serverClock.textContent = formatClock(data.server_time);
      draw();
    } catch (error) {
      setStatus("offline", "Servidor offline");
    } finally {
      window.setTimeout(poll, pollMs);
    }
  }

  elements.modeLine.addEventListener("click", () => switchMode("line"));
  elements.modeRoi.addEventListener("click", () => switchMode("roi"));
  elements.canvas.addEventListener("click", onCanvasClick);
  elements.saveButton.addEventListener("click", saveSelection);
  elements.clearButton.addEventListener("click", clearDraft);
  elements.stream.addEventListener("load", () => {
    state.streamVisible = true;
    elements.placeholder.classList.add("is-hidden");
  });
  elements.stream.addEventListener("error", () => {
    state.streamVisible = false;
    elements.placeholder.classList.remove("is-hidden");
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      clearDraft();
    }
  });

  if (typeof ResizeObserver !== "undefined") {
    new ResizeObserver(resizeCanvas).observe(elements.frame);
  } else {
    window.addEventListener("resize", resizeCanvas);
  }

  updateModeUi();
  updateSavedInfo();
  resizeCanvas();
  poll();
})();
