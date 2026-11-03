(() => {
  "use strict";

  const body = document.body;
  const pollMs = Math.max(100, Number(body.dataset.pollMs) || 200);

  const elements = {
    cameraPill: document.getElementById("camera-pill"),
    cameraStatusLabel: document.getElementById("camera-status-label"),
    fpsValue: document.getElementById("fps-value"),
    resValue: document.getElementById("res-value"),
    raceTimer: document.getElementById("race-timer"),
    videoPanel: document.getElementById("video-panel"),
    videoFrame: document.querySelector(".video-frame"),
    videoStream: document.getElementById("video-stream"),
    videoPlaceholder: document.getElementById("video-placeholder"),
    videoSubtitle: document.getElementById("video-subtitle"),
    sourceBadge: document.getElementById("source-badge"),
    colorGrid: document.getElementById("color-grid"),
    lineupTag: document.getElementById("lineup-tag"),
    raceStatus: document.getElementById("race-status"),
    rankingTag: document.getElementById("ranking-tag"),
    rankingList: document.getElementById("ranking-list"),
    podiumPanel: document.getElementById("podium-panel"),
    podium: document.getElementById("podium"),
    podiumTag: document.getElementById("podium-tag"),
    armButton: document.getElementById("arm-btn"),
    startButton: document.getElementById("start-btn"),
    finishButton: document.getElementById("finish-btn"),
    resetButton: document.getElementById("reset-btn"),
    fullscreenButton: document.getElementById("fullscreen-btn"),
    fullscreenLabel: document.getElementById("fullscreen-label"),
    soundToggle: document.getElementById("sound-toggle"),
    soundLabel: document.getElementById("sound-label"),
    browserCameraBtn: document.getElementById("browser-camera-btn"),
    browserCameraStart: document.getElementById("browser-camera-start"),
    placeholderTitle: document.getElementById("placeholder-title"),
    placeholderHint: document.getElementById("placeholder-hint"),
    controlsNote: document.getElementById("controls-note"),
    cameraSource: document.getElementById("camera-source"),
    cameraIndex: document.getElementById("camera-index"),
    cameraCapture: document.getElementById("camera-capture"),
    cameraProcess: document.getElementById("camera-process"),
    cameraLine: document.getElementById("camera-line"),
    cameraError: document.getElementById("camera-error"),
    serverClock: document.getElementById("server-clock"),
    toast: document.getElementById("toast"),
  };

  const raceLabels = {
    idle: "Aguardando",
    armed: "Formação",
    running: "Em corrida",
    finished: "Finalizada",
  };

  const controlNotes = {
    idle: "Sorteie 3 carros para começar.",
    armed: "Formação pronta. Clique em Iniciar no momento da largada.",
    running: "Cronômetro ativo. Boa corrida!",
    finished: "Corrida finalizada. Sorteie outra ou resete.",
  };

  const rankingLabels = {
    idle: "Aguardando",
    armed: "Pronto",
    running: "Ao vivo",
    finished: "Final",
  };

  const colorHex = new Map();
  let streamVisible = false;
  let actionPending = false;
  let toastTimer = null;
  let lastRace = { status: "idle", lineup: [], cars: [] };
  let hasRaceState = false;
  let podiumSignature = "";
  let audioContext = null;
  let soundEnabled = true;
  let lastCameraSource = "webcam";
  let lastCameraStreaming = false;
  const browserCamera = {
    active: false,
    stream: null,
    video: null,
    canvas: null,
    context: null,
    timer: null,
    sending: false,
  };

  try {
    soundEnabled = window.localStorage.getItem("toy-car-race-sound") !== "off";
  } catch (error) {
    soundEnabled = true;
  }

  function setStatus(kind, label) {
    elements.cameraPill.className = `status-pill status-pill--${kind}`;
    elements.cameraStatusLabel.textContent = label;
  }

  function formatNumber(value, digits = 1) {
    const number = Number(value);
    return Number.isFinite(number) ? number.toFixed(digits) : "--";
  }

  function formatLine(line) {
    if (!line || !Array.isArray(line.p1) || !Array.isArray(line.p2)) {
      return "--";
    }
    const point = (values) => `${Math.round(values[0] * 100)}%, ${Math.round(values[1] * 100)}%`;
    return `${point(line.p1)} → ${point(line.p2)}`;
  }

  function formatClock(isoDate) {
    const date = isoDate ? new Date(isoDate) : new Date();
    if (Number.isNaN(date.getTime())) {
      return "--:--:--";
    }
    return date.toLocaleTimeString("pt-BR");
  }

  function formatDuration(ms) {
    const total = Math.max(0, Number(ms) || 0);
    const minutes = Math.floor(total / 60000);
    const seconds = (total % 60000) / 1000;
    if (minutes > 0) {
      return `${minutes}:${seconds.toFixed(3).padStart(6, "0").replace(".", ",")}`;
    }
    return seconds.toFixed(3).replace(".", ",");
  }

  function showToast(message, isError = false) {
    if (!elements.toast) {
      return;
    }
    elements.toast.textContent = message;
    elements.toast.classList.toggle("is-error", isError);
    elements.toast.classList.add("is-visible");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      elements.toast.classList.remove("is-visible");
    }, 3000);
  }

  function updateSoundToggle() {
    if (!elements.soundToggle) {
      return;
    }
    const label = soundEnabled ? "Som ligado" : "Som desligado";
    if (elements.soundLabel) {
      elements.soundLabel.textContent = label;
    } else {
      elements.soundToggle.textContent = label;
    }
    elements.soundToggle.setAttribute("aria-pressed", soundEnabled ? "true" : "false");
  }

  function ensureAudio() {
    if (!soundEnabled) {
      return null;
    }
    const AudioCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtor) {
      return null;
    }
    if (!audioContext) {
      try {
        audioContext = new AudioCtor();
      } catch (error) {
        return null;
      }
    }
    if (audioContext.state === "suspended") {
      audioContext.resume().catch(() => {});
    }
    return audioContext;
  }

  function playTone(frequency, delay = 0, duration = 0.14, volume = 0.035) {
    const context = ensureAudio();
    if (!context) {
      return;
    }
    try {
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      const start = context.currentTime + delay;
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(frequency, start);
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(volume, start + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start(start);
      oscillator.stop(start + duration + 0.03);
    } catch (error) {
      return;
    }
  }

  function playFinishTone(position) {
    const frequencies = { 1: 880, 2: 660, 3: 520 };
    const frequency = frequencies[position] || 520;
    playTone(frequency, 0, 0.16, 0.04);
    playTone(frequency * 1.5, 0.08, 0.12, 0.022);
  }

  function playFanfare() {
    [523.25, 659.25, 783.99, 1046.5].forEach((frequency, index) => {
      playTone(frequency, 0.12 + index * 0.1, 0.16, 0.032);
    });
  }

  function announceRaceChanges(previous, next) {
    if (!soundEnabled) {
      return;
    }
    const previousFinished = new Set(
      (Array.isArray(previous?.cars) ? previous.cars : [])
        .filter((car) => car.status === "finished")
        .map((car) => car.color),
    );
    const newFinishes = (Array.isArray(next?.cars) ? next.cars : []).filter(
      (car) => car.status === "finished" && !previousFinished.has(car.color),
    );
    for (const car of newFinishes) {
      playFinishTone(Number(car.position) || 1);
    }
    if (previous?.status !== "finished" && next?.status === "finished") {
      playFanfare();
    }
  }

  function toggleSound() {
    soundEnabled = !soundEnabled;
    try {
      window.localStorage.setItem("toy-car-race-sound", soundEnabled ? "on" : "off");
    } catch (error) {}
    updateSoundToggle();
    if (soundEnabled) {
      ensureAudio();
      playTone(720, 0, 0.12, 0.025);
    } else if (audioContext) {
      audioContext.suspend().catch(() => {});
    }
  }

  function updateFullscreenButton() {
    if (!elements.fullscreenButton) {
      return;
    }
    const active = Boolean(document.fullscreenElement);
    const label = active ? "Sair da tela cheia" : "Tela cheia";
    if (elements.fullscreenLabel) {
      elements.fullscreenLabel.textContent = label;
    } else {
      elements.fullscreenButton.textContent = label;
    }
    elements.fullscreenButton.setAttribute("aria-pressed", active ? "true" : "false");
  }

  async function toggleFullscreen() {
    if (!elements.videoPanel) {
      return;
    }
    if (document.fullscreenElement) {
      try {
        await document.exitFullscreen();
      } catch (error) {
        showToast("Não foi possível sair da tela cheia.", true);
      }
      return;
    }
    if (!elements.videoPanel.requestFullscreen) {
      showToast("Tela cheia não é suportada neste navegador.", true);
      return;
    }
    try {
      await elements.videoPanel.requestFullscreen();
    } catch (error) {
      showToast("Não foi possível ativar a tela cheia.", true);
    }
  }

  function updateBrowserCameraUi() {
    const isBrowser = lastCameraSource === "browser";

    if (elements.browserCameraBtn) {
      elements.browserCameraBtn.classList.toggle("hidden", !isBrowser);
      elements.browserCameraBtn.classList.toggle("is-active", browserCamera.active);
      elements.browserCameraBtn.setAttribute(
        "aria-pressed",
        browserCamera.active ? "true" : "false",
      );
      elements.browserCameraBtn.title = browserCamera.active
        ? "Desligar câmera do dispositivo"
        : "Ativar câmera do dispositivo";
    }

    if (elements.browserCameraStart) {
      const show = isBrowser && !streamVisible;
      elements.browserCameraStart.classList.toggle("hidden", !show);
      elements.browserCameraStart.textContent = browserCamera.active
        ? "Desligar câmera"
        : "Ativar câmera deste dispositivo";
    }

    if (elements.placeholderTitle && isBrowser) {
      elements.placeholderTitle.textContent = browserCamera.active
        ? "Conectando câmera"
        : "Câmera do dispositivo";
    }
    if (elements.placeholderHint && isBrowser) {
      elements.placeholderHint.textContent = browserCamera.active
        ? "Enviando imagens para o servidor..."
        : "Ative a câmera deste dispositivo para começar.";
    }
  }

  async function startBrowserCamera() {
    if (browserCamera.active) {
      return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showToast("Este navegador não oferece acesso à câmera.", true);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      const video = document.createElement("video");
      video.className = "sr";
      video.muted = true;
      video.playsInline = true;
      video.srcObject = stream;
      document.body.append(video);
      await video.play();

      const canvas = document.createElement("canvas");
      canvas.width = 960;
      canvas.height = 540;

      browserCamera.stream = stream;
      browserCamera.video = video;
      browserCamera.canvas = canvas;
      browserCamera.context = canvas.getContext("2d");
      browserCamera.active = true;
      browserCamera.sending = false;
      browserCamera.timer = window.setInterval(
        sendBrowserFrame,
        1000 / 12,
      );

      stream.getVideoTracks().forEach((track) => {
        track.addEventListener("ended", stopBrowserCamera);
      });

      updateBrowserCameraUi();
      showToast("Câmera do dispositivo ativada.");
    } catch (error) {
      showToast(
        "Não foi possível acessar a câmera. Verifique a permissão.",
        true,
      );
    }
  }

  function stopBrowserCamera() {
    if (browserCamera.timer) {
      window.clearInterval(browserCamera.timer);
      browserCamera.timer = null;
    }
    if (browserCamera.stream) {
      browserCamera.stream.getTracks().forEach((track) => track.stop());
    }
    if (browserCamera.video) {
      browserCamera.video.remove();
    }
    browserCamera.stream = null;
    browserCamera.video = null;
    browserCamera.canvas = null;
    browserCamera.context = null;
    browserCamera.active = false;
    browserCamera.sending = false;
    updateBrowserCameraUi();
  }

  async function sendBrowserFrame() {
    const state = browserCamera;
    if (
      !state.active ||
      state.sending ||
      !state.video ||
      !state.context ||
      state.video.readyState < 2
    ) {
      return;
    }
    if (!state.video.videoWidth || !state.video.videoHeight) {
      return;
    }

    state.sending = true;
    try {
      const { video, canvas, context } = state;
      const scale = Math.max(
        canvas.width / video.videoWidth,
        canvas.height / video.videoHeight,
      );
      const sourceWidth = canvas.width / scale;
      const sourceHeight = canvas.height / scale;
      const sourceX = (video.videoWidth - sourceWidth) / 2;
      const sourceY = (video.videoHeight - sourceHeight) / 2;

      context.drawImage(
        video,
        sourceX,
        sourceY,
        sourceWidth,
        sourceHeight,
        0,
        0,
        canvas.width,
        canvas.height,
      );

      const blob = await new Promise((resolve) => {
        canvas.toBlob(resolve, "image/jpeg", 0.72);
      });
      if (!blob) {
        return;
      }
      await fetch("/api/camera/frame", {
        method: "POST",
        headers: { "Content-Type": "image/jpeg" },
        body: blob,
      });
    } catch (error) {
      // Falhas pontuais são refletidas no status da câmera pelo polling.
    } finally {
      state.sending = false;
    }
  }

  function toggleBrowserCamera() {
    if (browserCamera.active) {
      stopBrowserCamera();
    } else {
      startBrowserCamera();
    }
  }

  function updateColorGrid(colors) {
    if (!Array.isArray(colors) || colors.length === 0) {
      return;
    }

    const signature = colors
      .map((color) => `${color.key}:${color.label}:${color.hex}`)
      .join("|");

    if (elements.colorGrid.dataset.signature === signature) {
      return;
    }
    elements.colorGrid.dataset.signature = signature;
    colorHex.clear();

    const fragment = document.createDocumentFragment();
    for (const color of colors) {
      colorHex.set(color.key, color.hex);
      const chip = document.createElement("div");
      chip.className = "color-chip";
      chip.dataset.color = color.key;
      chip.style.setProperty("--chip", color.hex);

      const swatch = document.createElement("span");
      swatch.className = "chip-swatch";
      swatch.setAttribute("aria-hidden", "true");

      const label = document.createElement("span");
      label.className = "chip-label";
      label.textContent = color.label;

      const state = document.createElement("span");
      state.className = "chip-state";
      state.textContent = "Disponível";

      const progress = document.createElement("span");
      progress.className = "chip-progress";
      progress.setAttribute("aria-hidden", "true");
      progress.append(document.createElement("span"));

      chip.style.setProperty("--progress", "0%");
      chip.append(swatch, label, state, progress);
      fragment.append(chip);
    }

    elements.colorGrid.replaceChildren(fragment);
  }

  function updateColorStates(race) {
    const lineup = new Set(Array.isArray(race?.lineup) ? race.lineup : []);
    const cars = new Map(
      (Array.isArray(race?.cars) ? race.cars : []).map((car) => [car.color, car]),
    );

    for (const chip of elements.colorGrid.querySelectorAll(".color-chip")) {
      const key = chip.dataset.color;
      const car = cars.get(key);
      const state = chip.querySelector(".chip-state");
      const inLineup = Boolean(key && lineup.has(key));

      const progress = inLineup
        ? Math.min(1, Math.max(0, Number(car?.progress) || 0))
        : 0;
      chip.classList.toggle("is-lineup", inLineup);
      chip.classList.toggle("is-out", lineup.size > 0 && !inLineup);
      chip.classList.toggle("is-running", car?.status === "running");
      chip.classList.toggle("is-finished", car?.status === "finished");
      chip.classList.toggle("is-missed", car?.status === "missed");
      chip.style.setProperty("--progress", `${Math.round(progress * 100)}%`);
      if (car) {
        chip.title = `${car.label || key}: ${Math.round(progress * 100)}% até a linha`;
      } else {
        chip.removeAttribute("title");
      }

      if (!state) {
        continue;
      }
      if (lineup.size === 0) {
        state.textContent = "Disponível";
      } else if (!inLineup) {
        state.textContent = "Fora";
      } else if (car?.status === "finished") {
        state.textContent = `${car.position}º`;
      } else if (car?.status === "missed") {
        state.textContent = "Sem chegada";
      } else if (car?.status === "running") {
        state.textContent = "Na pista";
      } else {
        state.textContent = "Na largada";
      }
    }

    elements.lineupTag.textContent =
      lineup.size > 0 ? `${lineup.size} sorteadas` : "4 cores";
  }

  function updateCamera(state) {
    const camera = state.camera || {};
    const streaming = camera.status === "streaming";
    const source = camera.source || "webcam";
    lastCameraSource = source;
    lastCameraStreaming = streaming;

    if (streaming) {
      setStatus("live", "Ao vivo");
    } else if (camera.status === "starting") {
      setStatus("waiting", "Conectando");
    } else {
      setStatus("offline", "Offline");
    }

    elements.fpsValue.textContent = streaming ? formatNumber(camera.fps) : "--";
    elements.resValue.textContent =
      camera.width && camera.height ? `${camera.width}×${camera.height}` : "--";

    elements.cameraSource.textContent =
      source === "demo"
        ? "Demonstração"
        : source === "browser"
          ? "Câmera do navegador"
          : "Webcam";
    elements.cameraIndex.textContent =
      source === "webcam" ? String(camera.index ?? "--") : "—";
    elements.cameraCapture.textContent =
      camera.capture_width && camera.capture_height
        ? `${camera.capture_width}×${camera.capture_height}`
        : "--";
    elements.cameraProcess.textContent =
      camera.process_width && camera.process_height
        ? `${camera.process_width}×${camera.process_height}`
        : "--";
    elements.cameraLine.textContent = formatLine(state.config?.line);

    elements.sourceBadge.textContent =
      source === "demo" ? "DEMO" : source === "browser" ? "BROWSER" : "WEBCAM";

    if (camera.error) {
      elements.cameraError.textContent = camera.error;
      elements.cameraError.classList.remove("hidden");
    } else {
      elements.cameraError.textContent = "";
      elements.cameraError.classList.add("hidden");
    }

    if (streaming) {
      elements.videoSubtitle.textContent =
        source === "demo"
          ? "Pista sintética de demonstração em tempo real"
          : source === "browser"
            ? "Câmera do dispositivo processada no servidor"
            : "Transmissão da linha de chegada em tempo real";
    } else if (camera.status === "offline") {
      elements.videoSubtitle.textContent =
        source === "browser"
          ? "Ative a câmera deste dispositivo"
          : "Sem sinal da câmera";
    } else {
      elements.videoSubtitle.textContent =
        source === "browser"
          ? "Aguardando a câmera deste dispositivo"
          : "Aguardando a primeira imagem da câmera";
    }

    if (streaming && !streamVisible) {
      streamVisible = true;
      elements.videoStream.classList.add("is-visible");
      elements.videoPlaceholder.classList.add("is-hidden");
    } else if (source === "browser" && !streaming && !browserCamera.active) {
      streamVisible = false;
      elements.videoStream.classList.remove("is-visible");
      elements.videoPlaceholder.classList.remove("is-hidden");
    }

    updateBrowserCameraUi();
  }

  function emptyState(title, detail) {
    const item = document.createElement("li");
    item.className = "empty-state";
    item.textContent = title;
    const hint = document.createElement("span");
    hint.textContent = detail;
    item.append(hint);
    return item;
  }

  function rankingItem(car) {
    const item = document.createElement("li");
    item.className = "ranking-item";
    if (car.position === 1) {
      item.classList.add("ranking-item--first");
    }

    const position = document.createElement("span");
    position.className = "rank-position";
    position.textContent = `${car.position}º`;

    const swatch = document.createElement("span");
    swatch.className = "rank-color";
    swatch.style.setProperty("--chip", colorHex.get(car.color) || "#94a3b8");
    swatch.setAttribute("aria-hidden", "true");

    const copy = document.createElement("span");
    copy.className = "rank-copy";
    const name = document.createElement("span");
    name.className = "rank-name";
    name.textContent = car.label || car.color;
    const delta = document.createElement("span");
    delta.className = "rank-delta";
    delta.textContent =
      car.position === 1
        ? "Primeiro lugar"
        : `+${formatDuration(car.delta_ms)} s`;
    copy.append(name, delta);

    const time = document.createElement("span");
    time.className = "rank-time";
    time.textContent = `${formatDuration(car.elapsed_ms)} s`;

    item.append(position, swatch, copy, time);
    return item;
  }

  function updateRanking(race) {
    const cars = Array.isArray(race?.cars) ? race.cars : [];
    const finished = cars
      .filter(
        (car) =>
          car.status === "finished" &&
          Number.isFinite(Number(car.position)) &&
          Number.isFinite(Number(car.elapsed_ms)),
      )
      .sort((first, second) => first.position - second.position);

    if (finished.length > 0) {
      elements.rankingList.replaceChildren(...finished.map(rankingItem));
      return;
    }

    if (race?.status === "armed") {
      elements.rankingList.replaceChildren(
        emptyState(
          "Formação pronta.",
          "Clique em Iniciar corrida no momento da largada.",
        ),
      );
    } else if (race?.status === "running") {
      elements.rankingList.replaceChildren(
        emptyState(
          "Corrida em andamento.",
          "As chegadas aparecem aqui em tempo real.",
        ),
      );
    } else if (race?.status === "finished") {
      elements.rankingList.replaceChildren(
        emptyState(
          "Corrida encerrada.",
          "Nenhum carro cruzou a linha de chegada.",
        ),
      );
    } else {
      elements.rankingList.replaceChildren(
        emptyState(
          "Nenhuma corrida iniciada.",
          "O ranking aparece aqui quando os carros cruzarem a linha.",
        ),
      );
    }
  }

  function podiumEntry(car, position) {
    const placeNames = ["first", "second", "third"];
    const item = document.createElement("div");
    item.className = `podium-place podium-place--${placeNames[position - 1]}`;
    if (!car) {
      item.classList.add("is-empty");
    }

    const athlete = document.createElement("div");
    athlete.className = "podium-athlete";

    const swatch = document.createElement("span");
    swatch.className = "podium-color";
    swatch.style.setProperty(
      "--chip",
      car ? colorHex.get(car.color) || "#94a3b8" : "#475569",
    );

    const name = document.createElement("span");
    name.className = "podium-name";
    name.textContent = car ? car.label || car.color : "—";

    const time = document.createElement("span");
    time.className = "podium-time";
    time.textContent = car ? `${formatDuration(car.elapsed_ms)} s` : "Sem chegada";

    athlete.append(swatch, name, time);

    const bar = document.createElement("div");
    bar.className = "podium-bar";
    const rank = document.createElement("span");
    rank.className = "podium-rank";
    rank.textContent = String(position);
    bar.append(rank);

    item.append(athlete, bar);
    return item;
  }

  function updatePodium(race) {
    if (!elements.podiumPanel || !elements.podium) {
      return;
    }

    const finished = (Array.isArray(race?.cars) ? race.cars : [])
      .filter(
        (car) =>
          car.status === "finished" &&
          Number.isFinite(Number(car.position)) &&
          Number.isFinite(Number(car.elapsed_ms)),
      )
      .sort((first, second) => first.position - second.position)
      .slice(0, 3);

    const signature =
      finished.length > 0
        ? finished
            .map((car) => `${car.position}:${car.color}:${car.elapsed_ms}`)
            .join("|")
        : "empty";
    if (signature === podiumSignature) {
      return;
    }
    podiumSignature = signature;

    const byPosition = new Map(
      finished.map((car) => [Number(car.position), car]),
    );
    const fragment = document.createDocumentFragment();
    for (const position of [2, 1, 3]) {
      fragment.append(podiumEntry(byPosition.get(position), position));
    }
    elements.podium.replaceChildren(fragment);
    elements.podiumTag.textContent =
      finished.length > 0 ? `${finished.length} de 3` : "Aguardando";

    elements.podiumPanel.classList.remove("is-animated");
    if (finished.length > 0) {
      void elements.podiumPanel.offsetWidth;
      elements.podiumPanel.classList.add("is-animated");
    }
  }

  function updateControls(race) {
    const status = race?.status || "idle";
    elements.armButton.disabled = actionPending || status === "running";
    elements.startButton.disabled = actionPending || status !== "armed";
    elements.finishButton.disabled = actionPending || status !== "running";
    elements.resetButton.disabled = actionPending || status === "idle";
    elements.controlsNote.textContent = controlNotes[status] || controlNotes.idle;
  }

  function showVictory(race) {
    const box = document.getElementById("victory");
    if (!box) return;
    const top = (race.cars || [])
      .filter((c) => c.status === "finished" && Number.isFinite(Number(c.position)) && Number.isFinite(Number(c.elapsed_ms)))
      .sort((a, b) => a.position - b.position)
      .slice(0, 3);
    if (top.length === 0) return;

    const make = (tag, cls, text) => {
      const node = document.createElement(tag);
      node.className = cls;
      if (text !== undefined) node.textContent = text;
      return node;
    };
    const rand = (a, b) => a + Math.random() * (b - a);
    const palette = ["#d6ff1f", "#ff2bd6", "#f4f4ee", "#ff3b2f"];
    const timers = [];
    const intervals = [];
    const later = (fn, ms) => timers.push(window.setTimeout(fn, ms));
    const every = (fn, ms) => intervals.push(window.setInterval(fn, ms));
    const inner = make("div", "v-inner");
    const row = make("div", "v-row");
    const byPos = new Map(top.map((c) => [Number(c.position), c]));
    const cards = new Map();

    const title = make("h2", "v-title");
    title.setAttribute("aria-label", "Resultado final");
    [..."Resultado final"].forEach((ch, i) => {
      const letter = make("span", "v-letter", ch === " " ? "\u00a0" : ch);
      letter.setAttribute("aria-hidden", "true");
      letter.style.animationDelay = `${0.45 + i * 0.04}s`;
      title.append(letter);
    });

    for (const pos of [2, 1, 3]) {
      const car = byPos.get(pos);
      const card = make("div", `v-card v-card--${pos}`);
      if (!car) {
        card.classList.add("is-empty");
      } else {
        card.style.setProperty("--chip", colorHex.get(car.color) || "#94a3b8");
        if (pos === 1) card.append(make("span", "v-crown"));
        card.append(make("span", "v-rank", `${pos}º`), make("span", "v-swatch"), make("span", "v-name", car.label || car.color));
        if (pos === 1) card.append(make("span", "v-tag", "Campeão"));
        card.append(make("span", "v-time", "0,000 s"));
      }
      cards.set(pos, card);
      row.append(card);
    }

    const again = make("button", "btn is-primary", "Nova corrida");
    const close = make("button", "btn", "Continuar");
    const actions = make("div", "v-actions");
    actions.append(again, close);
    inner.append(title, row, actions);
    box.classList.remove("suspense");
    box.replaceChildren(
      make("div", "v-rays"), make("div", "v-beam v-beam--l"), make("div", "v-beam v-beam--r"),
      make("div", "v-floor"), inner, make("div", "v-flag"),
    );
    box.hidden = false;
    later(() => box.querySelector(".v-flag")?.remove(), 1100);

    const spot = (card) => {
      const b = box.getBoundingClientRect();
      const r = card.getBoundingClientRect();
      return { x: r.left - b.left + r.width / 2, top: r.top - b.top, bottom: r.bottom - b.top };
    };
    function burst(x, y, amount, a0, a1, d0, d1) {
      for (let i = 0; i < amount; i += 1) {
        const bit = make("span", `v-bit v-bit--${i % 3}`);
        const angle = rand(a0, a1);
        const dist = rand(d0, d1);
        const ux = Math.cos(angle) * dist * 0.6;
        const uy = Math.sin(angle) * dist;
        bit.style.cssText = `left:${x}px;top:${y}px;--k:${palette[i % 4]};--ux:${ux}px;--uy:${uy}px;--dx:${ux * 1.7}px;--dy:${uy * 0.2 + rand(140, 300)}px;--rot:${rand(-540, 540)}deg;--d:${rand(1.4, 2.2)}s`;
        bit.addEventListener("animationend", () => bit.remove());
        box.append(bit);
      }
    }
    function rainBit() {
      const bit = make("span", "v-rain");
      bit.style.cssText = `left:${rand(0, 100)}%;--k:${palette[Math.floor(rand(0, 4))]};--sway:${rand(-70, 70)}px;--rot:${rand(-720, 720)}deg;--d:${rand(2.2, 3.6)}s`;
      bit.addEventListener("animationend", () => bit.remove());
      box.append(bit);
    }
    function ring(x, y) {
      const node = make("span", "v-ring");
      node.style.cssText = `left:${x}px;top:${y}px`;
      node.addEventListener("animationend", () => node.remove());
      box.append(node);
    }
    function shake() {
      inner.classList.remove("shake");
      void inner.offsetWidth;
      inner.classList.add("shake");
    }
    function countUp(card, ms) {
      const label = card.querySelector(".v-time");
      const start = performance.now();
      let ticks = 0;
      const step = (now) => {
        const t = Math.min(1, (now - start) / 900);
        label.textContent = `${formatDuration(ms * (1 - Math.pow(1 - t, 3)))} s`;
        const tick = Math.floor(t * 9);
        if (tick > ticks) {
          ticks = tick;
          playTone(640 + tick * 55, 0, 0.03, 0.018);
        }
        if (t < 1 && !box.hidden) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }

    function land(pos, card, car) {
      const p = spot(card);
      ring(p.x, p.bottom);
      burst(p.x, p.top + 20, pos === 1 ? 50 : 26, -Math.PI * 0.95, -Math.PI * 0.05, 120, 300);
      countUp(card, Number(car.elapsed_ms));
      playTone(110, 0, 0.18, 0.07);
      playFinishTone(pos);
      if (navigator.vibrate) navigator.vibrate(pos === 1 ? [80, 40, 160] : 50);
      shake();
      if (pos !== 1) return;
      const b = box.getBoundingClientRect();
      box.append(make("div", "v-flash"));
      burst(0, b.height, 34, -1.3, -0.65, 320, 620);
      burst(b.width, b.height, 34, -2.5, -1.85, 320, 620);
      for (let i = 0; i < 7; i += 1) {
        const spark = make("span", "v-spark");
        const angle = (i / 7) * Math.PI * 2;
        spark.style.cssText = `left:${p.x + Math.cos(angle) * 8.5 * 16}px;top:${(p.top + p.bottom) / 2 + Math.sin(angle) * 6.5 * 16}px;animation-delay:${rand(0, 1)}s`;
        box.append(spark);
      }
      let spawned = 0;
      const id = window.setInterval(() => {
        rainBit();
        rainBit();
        spawned += 1;
        if (spawned > 30) window.clearInterval(id);
      }, 110);
      intervals.push(id);
      playFanfare();
    }

    const reveal = { 3: 1300, 2: 2300, 1: 3900 };
    later(() => {
      box.classList.add("suspense");
      const id = window.setInterval(() => playTone(170, 0, 0.05, 0.03), 75);
      intervals.push(id);
      later(() => window.clearInterval(id), 900);
    }, 3000);
    for (const pos of [3, 2, 1]) {
      const car = byPos.get(pos);
      if (!car) continue;
      const card = cards.get(pos);
      later(() => card.classList.add("is-in"), reveal[pos]);
      later(() => land(pos, card, car), reveal[pos] + 500);
      later(() => {
        card.classList.remove("is-in");
        card.classList.add("is-idle");
      }, reveal[pos] + 1000);
    }
    later(() => actions.classList.add("is-in"), 5900);

    function dismiss() {
      timers.forEach((id) => window.clearTimeout(id));
      intervals.forEach((id) => window.clearInterval(id));
      document.removeEventListener("keydown", onKey);
      box.hidden = true;
      box.replaceChildren();
    }
    function onKey(event) {
      if (event.key === "Escape") dismiss();
    }
    close.addEventListener("click", dismiss);
    again.addEventListener("click", () => {
      dismiss();
      elements.armButton.click();
    });
    document.addEventListener("keydown", onKey);
  }

  function updateRace(race) {
    const previous = lastRace;
    lastRace = race || { status: "idle", lineup: [], cars: [] };
    if (hasRaceState) {
      announceRaceChanges(previous, lastRace);
    } else {
      hasRaceState = true;
    }
    if (previous?.status === "running" && lastRace.status === "finished") {
      showVictory(lastRace);
    }
    if (previous?.status !== lastRace.status) {
      const pill = document.querySelector(".timer-pill");
      if (pill) {
        pill.classList.remove("jelly");
        void pill.offsetWidth;
        pill.classList.add("jelly");
      }
    }
    const status = lastRace.status || "idle";
    elements.raceStatus.textContent = raceLabels[status] || "Aguardando";
    elements.raceStatus.dataset.status = status;
    elements.videoPanel.dataset.race = status;
    elements.rankingTag.textContent = rankingLabels[status] || "Ranking";
    elements.raceTimer.textContent = formatDuration(lastRace.elapsed_ms);
    updateColorStates(lastRace);
    updateRanking(lastRace);
    updatePodium(lastRace);
    updateControls(lastRace);
  }

  function updateClock(serverTime) {
    elements.serverClock.textContent = formatClock(serverTime);
  }

  async function fetchState() {
    const response = await fetch("/api/state", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const state = await response.json();
    updateCamera(state);
    updateColorGrid(state.config?.colors || []);
    updateRace(state.race || { status: "idle", lineup: [], cars: [] });
    updateClock(state.server_time);
    return state;
  }

  async function poll() {
    try {
      await fetchState();
    } catch (error) {
      setStatus("offline", "Servidor offline");
      elements.videoSubtitle.textContent = "Não foi possível falar com o servidor local";
    } finally {
      window.setTimeout(poll, pollMs);
    }
  }

  async function runAction(path) {
    if (actionPending) {
      return;
    }
    if (soundEnabled) {
      ensureAudio();
    }
    actionPending = true;
    updateControls(lastRace);

    try {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      let data = {};
      try {
        data = await response.json();
      } catch (error) {
        data = {};
      }
      if (!response.ok) {
        throw new Error(data.error || "Ação indisponível no momento.");
      }
      actionPending = false;
      await fetchState();
    } catch (error) {
      showToast(error.message || "Não foi possível concluir a ação.", true);
    } finally {
      actionPending = false;
      updateControls(lastRace);
    }
  }

  elements.armButton.addEventListener("click", () => runAction("/api/race/arm"));
  elements.startButton.addEventListener("click", () => runAction("/api/race/start"));
  elements.finishButton.addEventListener("click", () => runAction("/api/race/finish"));
  elements.resetButton.addEventListener("click", () => runAction("/api/race/reset"));
  elements.fullscreenButton.addEventListener("click", toggleFullscreen);
  elements.soundToggle.addEventListener("click", toggleSound);
  elements.browserCameraBtn?.addEventListener("click", toggleBrowserCamera);
  elements.browserCameraStart?.addEventListener("click", toggleBrowserCamera);
  document.addEventListener("fullscreenchange", () => {
    updateFullscreenButton();
  });

  elements.videoStream.addEventListener("load", () => {
    if (
      lastCameraSource === "browser" &&
      !lastCameraStreaming &&
      !browserCamera.active
    ) {
      return;
    }
    streamVisible = true;
    elements.videoStream.classList.add("is-visible");
    elements.videoPlaceholder.classList.add("is-hidden");
    updateBrowserCameraUi();
  });

  elements.videoStream.addEventListener("error", () => {
    streamVisible = false;
    elements.videoStream.classList.remove("is-visible");
    elements.videoPlaceholder.classList.remove("is-hidden");
    updateBrowserCameraUi();
  });

  updateSoundToggle();
  updateFullscreenButton();
  updateControls(lastRace);
  poll();
})();
