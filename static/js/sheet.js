(() => {
  "use strict";
  // Gelatina: aperta (achata) ao tocar e balança ao soltar.
  const JELLY = "button.btn,.icon-btn,.tab,.mode-btn,.link-btn";
  let held = null;
  const wobble = (el) => {
    el.classList.remove("jelly");
    void el.offsetWidth;
    el.classList.add("jelly");
    window.setTimeout(() => el.classList.remove("jelly"), 650);
  };
  document.addEventListener("pointerdown", (event) => {
    const el = event.target.closest(JELLY);
    if (!el || el.disabled) return;
    held = el;
    el.classList.remove("jelly");
    el.classList.add("is-pressed");
  });
  const release = () => {
    if (!held) return;
    const el = held;
    held = null;
    el.classList.remove("is-pressed");
    wobble(el);
  };
  document.addEventListener("pointerup", release);
  document.addEventListener("pointercancel", release);
  document.addEventListener("keyup", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const el = event.target.closest?.(JELLY);
    if (el && !el.disabled) wobble(el);
  });
})();

(() => {
  "use strict";
  const sheet = document.getElementById("sheet");
  const scrim = document.getElementById("scrim");
  if (!sheet || !scrim) return;
  const tabs = [...sheet.querySelectorAll("[data-tab]")];
  const panels = [...sheet.querySelectorAll("[data-panel]")];

  function selectTab(name) {
    tabs.forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.tab === name)));
    panels.forEach((panel) => { panel.hidden = panel.dataset.panel !== name; });
  }
  function openSheet(name) {
    if (name) selectTab(name);
    sheet.inert = false;
    sheet.classList.add("is-open");
    scrim.classList.add("is-open");
  }
  function closeSheet() {
    sheet.classList.remove("is-open");
    scrim.classList.remove("is-open");
    sheet.inert = true;
  }

  tabs.forEach((tab) => tab.addEventListener("click", () => selectTab(tab.dataset.tab)));
  document.getElementById("details-btn")?.addEventListener("click", () => openSheet());
  document.querySelectorAll("[data-open]").forEach((el) =>
    el.addEventListener("click", () => openSheet(el.dataset.open)));
  document.getElementById("sheet-close")?.addEventListener("click", closeSheet);
  scrim.addEventListener("click", closeSheet);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeSheet();
  });

  // Toque na imagem: alterna entre HUD completo e HUD mínimo (só cronômetro e botões).
  const stage = document.getElementById("video-panel");
  stage?.querySelector(".video-frame")?.addEventListener("click", () => stage.classList.toggle("hud-min"));
})();
