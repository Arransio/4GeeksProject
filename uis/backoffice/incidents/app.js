const actorInput = document.querySelector("#actor-input");
const incidentRows = document.querySelector("#incident-rows");
const severitySummary = document.querySelector("#severity-summary");
const modal = document.querySelector("#modal-backdrop");
const form = document.querySelector("#incident-form");
const detailPanel = document.querySelector("#detail-panel");
const panelScrim = document.querySelector("#panel-scrim");
const notice = document.querySelector("#notice");

document.querySelectorAll("[data-app-link]").forEach((link) => {
  const appName = link.dataset.appLink;
  link.href = `${window.location.protocol}//${window.location.hostname}:${link.dataset.port}/`;
  if (appName === "incidents") {
    link.classList.add("active");
    link.setAttribute("aria-current", "page");
  }
});

let catalogs;
let currentIncident;
let noticeTimer;

actorInput.value = localStorage.getItem("incident-manager-actor") || "";
actorInput.addEventListener("change", () => {
  localStorage.setItem("incident-manager-actor", actorInput.value.trim());
});

async function request(path, options = {}) {
  const headers = { Accept: "application/json", ...options.headers };
  if (options.body) headers["Content-Type"] = "application/json";
  if (options.method && options.method !== "GET") {
    const actor = actorInput.value.trim();
    if (!actor) throw new Error("Indica tu correo de HealthCore para registrar la autoria.");
    headers["X-Actor"] = actor;
  }
  const response = await fetch(path, { ...options, headers });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Error ${response.status}`);
  return payload;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function setOptions(select, values, placeholder) {
  select.replaceChildren();
  if (placeholder) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;
    select.append(option);
  }
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  }
}

function formatDate(value) {
  if (!value) return "Sin fecha";
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium", timeStyle: "short", timeZone: "UTC",
  }).format(new Date(value));
}

function severityTone(value) {
  const normalized = value.toLocaleLowerCase();
  if (/critical|critica|cr[ií]tica|high|alta|urgente/.test(normalized)) return "severity-high";
  if (/medium|media|moderada/.test(normalized)) return "severity-medium";
  if (/low|baja|menor/.test(normalized)) return "severity-low";
  return "";
}

function summaryTone(value) {
  const normalized = value.toLocaleLowerCase();
  if (/critical|critica|cr[ií]tica|high|alta|urgente/.test(normalized)) return "tone-high";
  if (/medium|media|moderada/.test(normalized)) return "tone-medium";
  if (/low|baja|menor/.test(normalized)) return "tone-low";
  return "";
}

function showNotice(message, isError = false) {
  notice.textContent = message;
  notice.style.background = isError ? "#8e3730" : "#203b34";
  notice.classList.add("visible");
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => notice.classList.remove("visible"), 3800);
}

function currentFilters() {
  const params = new URLSearchParams();
  const filters = {
    status: document.querySelector("#filter-status").value,
    severity: document.querySelector("#filter-severity").value,
    responsible_area: document.querySelector("#filter-area").value,
  };
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
  return params.toString();
}

async function loadIncidents() {
  try {
    const query = currentFilters();
    const incidents = await request(`/api/incidents${query ? `?${query}` : ""}`);
    document.querySelector("#result-count").textContent = `${incidents.length} resultado${incidents.length === 1 ? "" : "s"}`;
    if (!incidents.length) {
      incidentRows.innerHTML = '<tr><td class="empty-state" colspan="7">No hay incidencias que coincidan con estos filtros.</td></tr>';
      return;
    }
    incidentRows.innerHTML = incidents.map((incident) => `
      <tr>
        <td><a class="incident-link" href="#${encodeURIComponent(incident.incident_id)}" data-open="${escapeHtml(incident.incident_id)}"><strong>${escapeHtml(incident.title)}</strong><span>${escapeHtml(incident.incident_id)} · ${escapeHtml(incident.channel)}</span></a></td>
        <td>${escapeHtml(incident.incident_type)}</td>
        <td><span class="pill ${severityTone(incident.severity)}">${escapeHtml(incident.severity)}</span></td>
        <td>${escapeHtml(incident.responsible_area)}</td>
        <td><span class="pill">${escapeHtml(incident.status)}</span></td>
        <td class="muted-cell">${escapeHtml(formatDate(incident.updated_at))}</td>
        <td><button class="row-action" type="button" data-open="${escapeHtml(incident.incident_id)}">Ver</button></td>
      </tr>`).join("");
    incidentRows.querySelectorAll("[data-open]").forEach((element) => {
      element.addEventListener("click", (event) => {
        event.preventDefault();
        openIncident(element.dataset.open);
      });
    });
  } catch (error) {
    showNotice(error.message, true);
    incidentRows.innerHTML = `<tr><td class="empty-state" colspan="7">${escapeHtml(error.message)}</td></tr>`;
  }
}

async function loadSummary() {
  try {
    const summary = await request("/api/summary/open-by-severity");
    const entries = Object.entries(summary);
    severitySummary.innerHTML = entries.length ? entries.map(([severity, count]) => `
      <article class="summary-item ${summaryTone(severity)}">
        <span class="summary-label">${escapeHtml(severity)}</span>
        <strong class="summary-number">${Number(count)}</strong>
      </article>`).join("") : '<div class="summary-placeholder">Sin severidades configuradas.</div>';
    document.querySelector("#updated-label").textContent = `Actualizado ${new Intl.DateTimeFormat("es-ES", { timeStyle: "short" }).format(new Date())}`;
  } catch (error) {
    severitySummary.innerHTML = `<div class="summary-placeholder">${escapeHtml(error.message)}</div>`;
  }
}

async function refreshDashboard() {
  await Promise.all([loadIncidents(), loadSummary()]);
}

function openDialog(incident = null) {
  currentIncident = incident;
  const isEditing = Boolean(incident);
  document.querySelector("#dialog-title").textContent = isEditing ? "Editar incidencia" : "Nueva incidencia";
  const submitButton = form.querySelector("[type=submit]");
  submitButton.textContent = isEditing ? "Guardar cambios" : "Registrar incidencia";
  for (const fieldName of ["incident_type", "severity", "channel", "responsible_area"]) {
    const choices = {
      incident_type: catalogs.incident_types,
      severity: catalogs.severities,
      channel: catalogs.channels,
      responsible_area: catalogs.areas,
    }[fieldName];
    setOptions(form.elements[fieldName], choices);
  }
  form.elements.title.value = incident?.title || "";
  form.elements.description.value = incident?.description || "";
  for (const fieldName of ["incident_type", "severity", "channel", "responsible_area"]) {
    form.elements[fieldName].value = incident?.[fieldName] || "";
    form.elements[fieldName].disabled = isEditing && fieldName === "responsible_area";
  }
  modal.hidden = false;
  form.elements.title.focus();
}

function closeDialog() {
  modal.hidden = true;
  currentIncident = null;
  form.reset();
}

function eventLabel(event) {
  if (event.event_type === "created") return "Incidencia registrada";
  if (event.event_type === "status_changed") return "Cambio de estado";
  if (event.event_type === "responsibility_changed") return "Cambio de área responsable";
  return `Actualización: ${event.field_name || "campo"}`;
}

async function openIncident(incidentId) {
  try {
    const [incident, history] = await Promise.all([
      request(`/api/incidents/${encodeURIComponent(incidentId)}`),
      request(`/api/incidents/${encodeURIComponent(incidentId)}/history`),
    ]);
    const body = document.querySelector("#detail-body");
    const transitions = catalogs.transitions[incident.status] || [];
    body.innerHTML = `
      <p class="detail-id">${escapeHtml(incident.incident_id)} · Creada ${escapeHtml(formatDate(incident.created_at))}</p>
      <section class="detail-section">
        <h3>${escapeHtml(incident.title)}</h3>
        <p class="detail-description">${escapeHtml(incident.description)}</p>
        <dl class="detail-grid">
          <div><dt>Tipo</dt><dd>${escapeHtml(incident.incident_type)}</dd></div>
          <div><dt>Severidad</dt><dd><span class="pill ${severityTone(incident.severity)}">${escapeHtml(incident.severity)}</span></dd></div>
          <div><dt>Canal</dt><dd>${escapeHtml(incident.channel)}</dd></div>
          <div><dt>Última actualización</dt><dd>${escapeHtml(formatDate(incident.updated_at))}</dd></div>
        </dl>
      </section>
      <section class="detail-section">
        <div class="detail-controls">
          <label>Área responsable<select id="assign-area"></select></label>
          <label>Estado<select id="transition-status"></select></label>
          <button class="primary-button" type="button" id="save-workflow">Guardar cambios operativos</button>
        </div>
      </section>
      <section class="detail-section">
        <div class="section-heading"><h3>Historial de actividad</h3><button class="text-button" type="button" id="edit-incident">Editar</button></div>
        <ol class="timeline">${history.slice().reverse().map((event) => `
          <li><strong>${escapeHtml(eventLabel(event))}</strong>
            <span>${escapeHtml(event.actor)} · ${escapeHtml(formatDate(event.occurred_at))}</span>
            ${event.field_name ? `<span>${escapeHtml(event.old_value || "-" )} → ${escapeHtml(event.new_value || "-")}</span>` : ""}
          </li>`).join("")}</ol>
      </section>`;
    setOptions(body.querySelector("#assign-area"), catalogs.areas);
    body.querySelector("#assign-area").value = incident.responsible_area;
    setOptions(body.querySelector("#transition-status"), transitions, "Sin cambio de estado");
    body.querySelector("#save-workflow").addEventListener("click", async () => {
      try {
        const area = body.querySelector("#assign-area").value;
        const status = body.querySelector("#transition-status").value;
        if (area !== incident.responsible_area) {
          await request(`/api/incidents/${encodeURIComponent(incidentId)}`, {
            method: "PATCH", body: JSON.stringify({ responsible_area: area }),
          });
        }
        if (status) {
          await request(`/api/incidents/${encodeURIComponent(incidentId)}`, {
            method: "PATCH", body: JSON.stringify({ status }),
          });
        }
        showNotice("Cambios operativos registrados.");
        await refreshDashboard();
        await openIncident(incidentId);
      } catch (error) {
        showNotice(error.message, true);
      }
    });
    body.querySelector("#edit-incident").addEventListener("click", () => openDialog(incident));
    detailPanel.classList.add("open");
    detailPanel.setAttribute("aria-hidden", "false");
    panelScrim.hidden = false;
  } catch (error) {
    showNotice(error.message, true);
  }
}

function closeDetail() {
  detailPanel.classList.remove("open");
  detailPanel.setAttribute("aria-hidden", "true");
  panelScrim.hidden = true;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(form).entries());
  if (currentIncident) delete data.responsible_area;
  try {
    const path = currentIncident
      ? `/api/incidents/${encodeURIComponent(currentIncident.incident_id)}`
      : "/api/incidents";
    await request(path, {
      method: currentIncident ? "PATCH" : "POST",
      body: JSON.stringify(data),
    });
    closeDialog();
    showNotice(currentIncident ? "Incidencia actualizada." : "Incidencia registrada.");
    await refreshDashboard();
    if (currentIncident) await openIncident(currentIncident.incident_id);
  } catch (error) {
    showNotice(error.message, true);
  }
});

document.querySelector("#new-incident-button").addEventListener("click", () => openDialog());
document.querySelector("#close-dialog").addEventListener("click", closeDialog);
document.querySelector("#cancel-dialog").addEventListener("click", closeDialog);
modal.addEventListener("click", (event) => { if (event.target === modal) closeDialog(); });
document.querySelector("#close-detail").addEventListener("click", closeDetail);
panelScrim.addEventListener("click", closeDetail);
document.querySelector("#refresh-button").addEventListener("click", refreshDashboard);
document.querySelector("#clear-filters").addEventListener("click", () => {
  document.querySelectorAll(".filters select").forEach((select) => { select.value = ""; });
  loadIncidents();
});
document.querySelectorAll(".filters select").forEach((select) => select.addEventListener("change", loadIncidents));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeDialog();
    closeDetail();
  }
});

async function initialize() {
  try {
    catalogs = await request("/api/catalogs");
    setOptions(document.querySelector("#filter-status"), catalogs.statuses, "Todos");
    setOptions(document.querySelector("#filter-severity"), catalogs.severities, "Todas");
    setOptions(document.querySelector("#filter-area"), catalogs.areas, "Todas");
    await refreshDashboard();
  } catch (error) {
    showNotice(`No se pudo cargar la configuracion de catalogos: ${error.message}`, true);
    incidentRows.innerHTML = `<tr><td class="empty-state" colspan="7">El servicio requiere catalogos aprobados antes de operar.</td></tr>`;
  }
}

initialize();