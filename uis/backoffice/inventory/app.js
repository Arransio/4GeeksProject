const productBackdrop = document.querySelector("#product-backdrop");
const movementBackdrop = document.querySelector("#movement-backdrop");
const historyBackdrop = document.querySelector("#history-backdrop");
const productForm = document.querySelector("#product-form");
const movementForm = document.querySelector("#movement-form");
const inventoryRows = document.querySelector("#inventory-rows");
const notice = document.querySelector("#notice");

let inventory = [];
let editingProductId = null;
let noticeTimer;

async function request(path, options = {}) {
  const headers = { Accept: "application/json", ...options.headers };
  if (options.body) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || `Error ${response.status}`);
  return payload;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function showNotice(message, isError = false) {
  notice.textContent = message;
  notice.style.background = isError ? "#8e3730" : "#203b34";
  notice.classList.add("visible");
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => notice.classList.remove("visible"), 3800);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium", timeStyle: "short", timeZone: "UTC",
  }).format(new Date(value));
}

function movementLabel(type) {
  return ({
    receipt: "Entrada",
    return: "Devolución",
    sale: "Salida",
    shrinkage: "Merma",
    inventory_gain: "Ajuste positivo",
    adjustment: "Ajuste",
  })[type] || type;
}

function renderInventory() {
  const query = document.querySelector("#search-input").value.trim().toLocaleLowerCase();
  const visibleItems = inventory.filter((item) =>
    `${item.product_id} ${item.name} ${item.unit}`.toLocaleLowerCase().includes(query)
  );
  const lowItems = inventory.filter((item) => item.stock < item.reorder_point);
  const stockedCount = inventory.filter((item) => item.stock > 0).length;

  document.querySelector("#product-count").textContent = inventory.length;
  document.querySelector("#stocked-count").textContent = stockedCount;
  document.querySelector("#low-stock-total").textContent = lowItems.length;
  document.querySelector("#low-stock-count").textContent = lowItems.length;
  document.querySelector("#result-count").textContent = `${visibleItems.length} artículo${visibleItems.length === 1 ? "" : "s"}`;

  const alertBand = document.querySelector("#low-stock-alert");
  alertBand.hidden = lowItems.length === 0;
  if (lowItems.length) {
    const names = lowItems.slice(0, 3).map((item) => item.name).join(", ");
    const remaining = lowItems.length > 3 ? ` y ${lowItems.length - 3} más` : "";
    document.querySelector("#low-stock-description").textContent = `${names}${remaining} por debajo de su punto de reorden.`;
  }

  if (!visibleItems.length) {
    inventoryRows.innerHTML = `<tr><td class="empty-state" colspan="6">${query ? "No hay artículos con esa búsqueda." : "No hay artículos registrados."}</td></tr>`;
    return;
  }
  inventoryRows.innerHTML = visibleItems.map((item) => {
    const isLow = item.stock < item.reorder_point;
    return `<tr>
      <td><div class="item-cell"><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.product_id)}</span></div></td>
      <td><span class="stock-value ${isLow ? "low" : ""}">${Number(item.stock)}</span> <span class="unit-value">${escapeHtml(item.unit)}</span></td>
      <td>${Number(item.reorder_point)} <span class="unit-value">${escapeHtml(item.unit)}</span></td>
      <td>${item.lot_count === undefined ? "—" : Number(item.lot_count)}</td>
      <td><span class="state-pill ${isLow ? "low" : ""}">${isLow ? "Bajo reorden" : "Disponible"}</span></td>
      <td><div class="row-actions"><button class="row-action" type="button" data-action="edit" data-product="${escapeHtml(item.product_id)}">Editar</button><button class="row-action" type="button" data-action="move" data-product="${escapeHtml(item.product_id)}">Movimiento</button><button class="row-action" type="button" data-action="history" data-product="${escapeHtml(item.product_id)}">Historial</button></div></td>
    </tr>`;
  }).join("");

  inventoryRows.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const product = inventory.find((item) => item.product_id === button.dataset.product);
      if (button.dataset.action === "edit") openProductDialog(product);
      if (button.dataset.action === "move") openMovementDialog(product);
      if (button.dataset.action === "history") openHistory(product);
    });
  });
}

async function refreshInventory() {
  try {
    inventory = await request("/api/inventory");
    renderInventory();
  } catch (error) {
    inventoryRows.innerHTML = `<tr><td class="empty-state" colspan="6">${escapeHtml(error.message)}</td></tr>`;
    showNotice(error.message, true);
  }
}

function openProductDialog(product = null) {
  editingProductId = product ? product.product_id : null;
  document.querySelector("#product-dialog-title").textContent = product ? "Editar artículo" : "Nuevo artículo";
  productForm.elements.product_id.disabled = Boolean(product);
  productForm.elements.product_id.value = product?.product_id || "";
  productForm.elements.name.value = product?.name || "";
  productForm.elements.unit.value = product?.unit || "";
  productForm.elements.reorder_point.value = product?.reorder_point ?? 0;
  productForm.querySelector("[type=submit]").textContent = product ? "Guardar cambios" : "Guardar artículo";
  productBackdrop.hidden = false;
  productForm.elements.name.focus();
}

function closeDialog(backdrop) {
  backdrop.hidden = true;
}

async function openMovementDialog(product = null) {
  const selector = movementForm.elements.product_id;
  selector.replaceChildren();
  inventory.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.product_id;
    option.textContent = `${item.name} (${item.product_id})`;
    selector.append(option);
  });
  if (product) selector.value = product.product_id;
  document.querySelector("#movement-lot").value = "";
  document.querySelector("#movement-type").value = "receipt";
  document.querySelector("#movement-quantity").value = "";
  movementForm.elements.reason.value = "";
  await updateLotOptions();
  movementBackdrop.hidden = false;
  selector.focus();
}

async function updateLotOptions() {
  const productId = movementForm.elements.product_id.value;
  const list = document.querySelector("#lot-options");
  list.replaceChildren();
  if (!productId) return;
  try {
    const lots = await request(`/api/products/${encodeURIComponent(productId)}/lots`);
    lots.forEach((lot) => {
      const option = document.createElement("option");
      option.value = lot.lot_id;
      option.label = lot.lot_id;
      list.append(option);
    });
  } catch (error) {
    showNotice(error.message, true);
  }
}

async function openHistory(product) {
  try {
    const movements = await request(`/api/products/${encodeURIComponent(product.product_id)}/movements`);
    document.querySelector("#history-title").textContent = "Movimientos";
    document.querySelector("#history-subtitle").textContent = `${product.name} · ${product.product_id}`;
    const rows = document.querySelector("#history-rows");
    rows.innerHTML = movements.length ? movements.slice().reverse().map((movement) => `
      <tr><td class="muted-cell">${escapeHtml(formatDate(movement.occurred_at))}</td>
        <td>${escapeHtml(movementLabel(movement.movement_type))}</td>
        <td class="stock-value">${movement.quantity > 0 ? "+" : ""}${Number(movement.quantity)} ${escapeHtml(product.unit)}</td>
        <td>${escapeHtml(movement.lot_id)}</td><td>${escapeHtml(movement.reason)}</td></tr>`).join("")
      : '<tr><td class="empty-state" colspan="5">Todavía no hay movimientos.</td></tr>';
    historyBackdrop.hidden = false;
  } catch (error) {
    showNotice(error.message, true);
  }
}

productForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(productForm).entries());
  data.reorder_point = Number(data.reorder_point);
  try {
    if (editingProductId) {
      await request(`/api/products/${encodeURIComponent(editingProductId)}`, { method: "PATCH", body: JSON.stringify({ name: data.name, unit: data.unit, reorder_point: data.reorder_point }) });
      showNotice("Artículo actualizado.");
    } else {
      await request("/api/products", { method: "POST", body: JSON.stringify(data) });
      showNotice("Artículo registrado.");
    }
    closeDialog(productBackdrop);
    await refreshInventory();
  } catch (error) {
    showNotice(error.message, true);
  }
});

movementForm.elements.product_id.addEventListener("change", updateLotOptions);
movementForm.elements.movement_type.addEventListener("change", () => {
  const adjustment = movementForm.elements.movement_type.value === "adjustment";
  document.querySelector("#quantity-label").childNodes[0].textContent = adjustment ? "Cantidad (+/-)" : "Cantidad (> 0)";
  document.querySelector("#movement-quantity").min = adjustment ? "-1000000000" : "1";
});
movementForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(movementForm).entries());
  data.quantity = Number(data.quantity);
  data.movement_id = `MOV-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
  try {
    await request("/api/movements", { method: "POST", body: JSON.stringify(data) });
    closeDialog(movementBackdrop);
    showNotice("Movimiento registrado en el historial.");
    await refreshInventory();
  } catch (error) {
    showNotice(error.message, true);
  }
});

document.querySelector("#new-product-button").addEventListener("click", () => openProductDialog());
document.querySelector("#new-movement-button").addEventListener("click", () => openMovementDialog());
document.querySelector("#refresh-button").addEventListener("click", refreshInventory);
document.querySelector("#search-input").addEventListener("input", renderInventory);
document.querySelectorAll("[data-close]").forEach((button) => {
  button.addEventListener("click", () => {
    const backdrop = { product: productBackdrop, movement: movementBackdrop, history: historyBackdrop }[button.dataset.close];
    closeDialog(backdrop);
  });
});
document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
  backdrop.addEventListener("click", (event) => {
    if (event.target === backdrop) closeDialog(backdrop);
  });
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") [productBackdrop, movementBackdrop, historyBackdrop].forEach(closeDialog);
});

refreshInventory();