"use strict";

const loginPanel = document.querySelector("#login-panel");
const workspace = document.querySelector("#workspace");
const loginForm = document.querySelector("#login-form");
const loginError = document.querySelector("#login-error");
const jobList = document.querySelector("#job-list");
const emptyJobs = document.querySelector("#empty-jobs");
const notice = document.querySelector("#notice");
let polling = false;
let pollTimer = 0;

const stateNames = {
  queued: "En cola",
  running: "Procesando",
  completed: "Completado",
  failed: "Error",
  cancelled: "Cancelado",
  expired: "Caducado",
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || "No se pudo completar la solicitud.");
  return result;
}

function displayAuthenticated(authenticated) {
  loginPanel.hidden = authenticated;
  workspace.hidden = !authenticated;
  if (!authenticated) {
    jobList.replaceChildren();
    emptyJobs.hidden = false;
    window.clearTimeout(pollTimer);
    return;
  }
  loginError.hidden = true;
  void refreshJobs();
}

function showNotice(message, isError = false) {
  notice.textContent = message;
  notice.classList.toggle("error", isError);
  notice.hidden = !message;
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.hidden = true;
  const button = loginForm.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ code: document.querySelector("#access-code").value }),
    });
    document.querySelector("#access-code").value = "";
    displayAuthenticated(true);
  } catch (error) {
    loginError.textContent = error.message;
    loginError.hidden = false;
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#logout-button").addEventListener("click", async () => {
  try {
    await api("/api/logout", { method: "POST", body: "{}" });
  } finally {
    displayAuthenticated(false);
  }
});

document.querySelector("#analyze-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showNotice("");
  const button = document.querySelector("#analyze-button");
  const error = document.querySelector("#analyze-error");
  error.hidden = true;
  const urls = document.querySelector("#video-urls").value.trim().split(/\s+/).filter(Boolean);
  if (!document.querySelector("#analyze-consent").checked) {
    error.textContent = "Confirma que tienes autorización para continuar.";
    error.hidden = false;
    return;
  }
  button.disabled = true;
  try {
    const result = await api("/api/analyze", {
      method: "POST",
      body: JSON.stringify({ urls, authorized: true }),
    });
    document.querySelector("#video-urls").value = "";
    document.querySelector("#analyze-consent").checked = false;
    showNotice(`${result.job_ids.length} análisis añadido${result.job_ids.length === 1 ? "" : "s"} a la cola.`);
    await refreshJobs();
  } catch (requestError) {
    error.textContent = requestError.message;
    error.hidden = false;
  } finally {
    button.disabled = false;
  }
});

async function refreshJobs() {
  if (polling || workspace.hidden) return;
  polling = true;
  try {
    const jobs = await api("/api/jobs");
    renderJobs(jobs);
    const active = jobs.some((job) => job.status === "queued" || job.status === "running");
    window.clearTimeout(pollTimer);
    pollTimer = window.setTimeout(refreshJobs, active ? 1200 : 5000);
  } catch (error) {
    if (error.message === "Inicia sesión para continuar.") {
      displayAuthenticated(false);
    } else {
      showNotice(error.message, true);
      pollTimer = window.setTimeout(refreshJobs, 5000);
    }
  } finally {
    polling = false;
  }
}

function renderJobs(jobs) {
  emptyJobs.hidden = jobs.length > 0;
  const fragment = document.createDocumentFragment();
  for (const job of jobs) fragment.append(makeJobCard(job));
  jobList.replaceChildren(fragment);
}

function makeJobCard(job) {
  const card = document.createElement("article");
  card.className = "job-card";
  const head = document.createElement("div");
  head.className = "job-head";
  const titleBlock = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = job.title;
  const meta = document.createElement("p");
  meta.className = "job-meta";
  meta.textContent = `${job.kind === "inspect" ? "Análisis" : "Descarga"} · ${formatDate(job.createdAt)}`;
  titleBlock.append(title, meta);
  const badge = document.createElement("span");
  badge.className = `status ${job.status}`;
  badge.textContent = stateNames[job.status] || job.status;
  head.append(titleBlock, badge);
  card.append(head);

  if (job.status === "running" && job.progress) card.append(makeProgress(job.progress, job.title));
  if (job.error) {
    const error = document.createElement("p");
    error.className = "form-error";
    error.setAttribute("role", "status");
    error.textContent = job.error;
    card.append(error);
  }
  if (job.kind === "inspect" && job.status === "completed" && Array.isArray(job.metadata)) {
    for (const video of job.metadata) card.append(makeMediaControls(job, video));
  }
  if (job.file && job.status === "completed") {
    const row = document.createElement("div");
    row.className = "job-actions";
    const link = document.createElement("a");
    link.className = "download-link";
    link.href = `/api/jobs/${encodeURIComponent(job.id)}/file`;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = `Guardar archivo · ${formatBytes(job.file.size)} · caduca ${formatDate(job.file.expiresAt)}`;
    row.append(link);
    card.append(row);
  }
  if (job.status === "queued" || job.status === "running") {
    const row = document.createElement("div");
    row.className = "job-actions";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "button cancel";
    cancel.textContent = "Cancelar trabajo";
    cancel.addEventListener("click", async () => {
      cancel.disabled = true;
      try {
        await api(`/api/jobs/${encodeURIComponent(job.id)}`, { method: "DELETE", body: "{}" });
        await refreshJobs();
      } catch (error) {
        showNotice(error.message, true);
      }
    });
    row.append(cancel);
    card.append(row);
  }
  return card;
}

function makeProgress(progress, title) {
  const wrapper = document.createElement("div");
  wrapper.className = "job-progress";
  const meter = document.createElement("progress");
  meter.max = 100;
  meter.setAttribute("aria-label", `Progreso de ${title}`);
  if (typeof progress.percent === "number") meter.value = progress.percent;
  const details = document.createElement("p");
  const speed = progress.speed ? `${formatBytes(progress.speed)}/s` : "velocidad no disponible";
  const eta = progress.eta != null ? `${Math.ceil(progress.eta)} s restantes` : "tiempo estimado no disponible";
  details.textContent = `${progress.phase || "Procesando"} · ${formatBytes(progress.downloaded)} / ${formatBytes(progress.total)} · ${speed} · ${eta}`;
  wrapper.append(meter, details);
  return wrapper;
}

function makeMediaControls(source, video) {
  const section = document.createElement("section");
  section.className = "media-result";
  if (video.thumbnail) {
    const image = document.createElement("img");
    image.src = video.thumbnail;
    image.alt = "Miniatura del video";
    image.loading = "lazy";
    section.append(image);
  } else {
    const placeholder = document.createElement("div");
    placeholder.className = "preview-placeholder";
    placeholder.textContent = "▶";
    section.append(placeholder);
  }
  const summary = document.createElement("div");
  const title = document.createElement("h4");
  title.textContent = video.title;
  const information = document.createElement("p");
  const duration = video.duration == null ? "Duración no disponible" : `${Math.floor(video.duration / 60)}:${String(Math.floor(video.duration % 60)).padStart(2, "0")}`;
  information.textContent = `${duration} · ${video.resolutions.map((value) => `${value}p`).join(" · ") || "audio disponible"}`;
  summary.append(title, information);
  section.append(summary);

  const controls = document.createElement("div");
  controls.className = "download-controls";
  const formatId = `format-${source.id}`;
  const qualityId = `quality-${source.id}`;
  const formatControl = makeSelectControl("Formato", formatId);
  formatControl.select.add(new Option("Video MP4", "mp4"));
  formatControl.select.add(new Option("Audio MP3", "mp3"));
  const qualityControl = makeSelectControl("Calidad", qualityId);
  if (!video.resolutions.length) qualityControl.select.add(new Option("No disponible", "360"));
  else {
    for (const resolution of video.resolutions) {
      qualityControl.select.add(new Option(resolution === 2160 ? "4K · 2160p" : `${resolution}p`, String(resolution)));
    }
  }
  formatControl.select.addEventListener("change", () => {
    qualityControl.select.disabled = formatControl.select.value === "mp3" || !video.resolutions.length;
  });
  qualityControl.select.disabled = !video.resolutions.length;
  controls.append(formatControl.wrapper, qualityControl.wrapper);

  const consentLabel = document.createElement("label");
  consentLabel.className = "check-row download-consent";
  const consent = document.createElement("input");
  consent.type = "checkbox";
  const consentText = document.createElement("span");
  consentText.textContent = "Tengo autorización para descargar este video.";
  consentLabel.append(consent, consentText);
  controls.append(consentLabel);

  const actions = document.createElement("div");
  actions.className = "job-actions";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "button primary";
  button.textContent = "Preparar descarga";
  button.disabled = formatControl.select.value === "mp4" && !video.resolutions.length;
  const updateDownloadAvailability = () => {
    button.disabled = formatControl.select.value === "mp4" && !video.resolutions.length;
  };
  button.addEventListener("click", async () => {
    if (!consent.checked) {
      showNotice("Confirma que tienes autorización antes de crear la descarga.", true);
      return;
    }
    button.disabled = true;
    try {
      await api(`/api/jobs/${encodeURIComponent(source.id)}/download`, {
        method: "POST",
        body: JSON.stringify({
          source_id: source.id,
          video_id: video.id,
          format: formatControl.select.value,
          resolution: Number(qualityControl.select.value),
          authorized: true,
        }),
      });
      showNotice("Descarga añadida a la cola.");
      await refreshJobs();
    } catch (error) {
      showNotice(error.message, true);
    } finally {
      button.disabled = false;
    }
  });
  formatControl.select.addEventListener("change", updateDownloadAvailability);
  actions.append(button);
  section.append(controls, actions);
  return section;
}

function makeSelectControl(label, id) {
  const wrapper = document.createElement("div");
  wrapper.className = "control";
  const fieldLabel = document.createElement("label");
  fieldLabel.htmlFor = id;
  fieldLabel.textContent = label;
  const select = document.createElement("select");
  select.id = id;
  select.className = "select-control";
  wrapper.append(fieldLabel, select);
  return { wrapper, select };
}

function formatBytes(value) {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  const size = Number(value);
  if (size < 1024) return `${Math.round(size)} B`;
  if (size < 1048576) return `${(size / 1024).toFixed(0)} KB`;
  return `${(size / 1048576).toFixed(1)} MB`;
}

function formatDate(value) {
  return new Intl.DateTimeFormat("es", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

async function init() {
  try {
    const session = await api("/api/session");
    displayAuthenticated(session.authenticated);
  } catch {
    displayAuthenticated(false);
  }
}

void init();
