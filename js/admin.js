/* =========================================================
   IRASETH PHARMA — Backend console logic
   Requires a reachable backend — there is no offline/demo login
   fallback anymore, since this screen now controls real inventory
   and real user accounts. Every action here is logged server-side.
   ========================================================= */

const SESSION_KEY = "iraseth_admin_session";
let currentUser = null;   // { email, name, role }
let currentOrders = [];
let currentStock = [];
let socket = null;

/* ---------- Small helpers ---------- */
function fmtDate(iso){
  if(!iso) return "—";
  return new Date(iso).toLocaleString("en-PH", { year:"numeric", month:"short", day:"numeric", hour:"2-digit", minute:"2-digit" });
}
function fmtDuration(seconds){
  if(seconds === null || seconds === undefined) return "In progress";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if(h) return `${h}h ${m}m`;
  if(m) return `${m}m ${s}s`;
  return `${s}s`;
}
function roleLabel(role){
  return { superadmin:"Superadmin", admin:"Admin", subadmin:"Sub-admin" }[role] || role;
}
function actionLabel(action){
  return { opening:"Opening stock", monthly_opening:"Monthly opening", release:"Released", supply:"Supplied" }[action] || action;
}
function toast(msg){
  const el = document.getElementById("toast");
  if(!el) return;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 3200);
}
function canWriteStock(){ return currentUser && (currentUser.role === "superadmin" || currentUser.role === "subadmin"); }
function canWriteOrders(){ return currentUser && (currentUser.role === "superadmin" || currentUser.role === "subadmin"); }
function isLogViewer(){ return currentUser && (currentUser.role === "superadmin" || currentUser.role === "admin"); }
function isSuperadmin(){ return currentUser && currentUser.role === "superadmin"; }

/* ---------- Auth screens ---------- */
function showLogin(){
  document.getElementById("loginScreen").style.display = "flex";
  document.getElementById("dashboardScreen").style.display = "none";
  if(socket){ socket.disconnect(); socket = null; }
}

async function showDashboard(){
  document.getElementById("loginScreen").style.display = "none";
  document.getElementById("dashboardScreen").style.display = "flex";

  document.getElementById("roleBadge").textContent = roleLabel(currentUser.role);
  document.getElementById("userNameLabel").textContent = currentUser.name || currentUser.email;

  // Hide nav links the current role isn't allowed to see.
  document.querySelectorAll(".admin-side a[data-role-gate]").forEach(a => {
    const allowed = a.dataset.roleGate.split(",");
    a.style.display = allowed.includes(currentUser.role) ? "" : "none";
  });

  // Every role gets a History button in this column now; only the Supply/
  // Release controls inside it are conditional on write permission, so the
  // column itself always stays visible.

  connectSocket();
  await switchView("inventory");
}

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const errorBox = document.getElementById("loginError");
  const submitBtn = e.target.querySelector("button[type=submit]");
  submitBtn.disabled = true;

  const res = await Api.login(email, password);

  if(res.ok){
    Api.setToken(res.data.token);
    currentUser = res.data.user;
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(currentUser));
    errorBox.classList.remove("show");
    await showDashboard();
  } else {
    errorBox.textContent = res.status === 0
      ? "Can't reach the backend. Is the API server running?"
      : (res.error || "Incorrect email or password.");
    errorBox.classList.add("show");
  }
  submitBtn.disabled = false;
});

document.getElementById("signOut").addEventListener("click", async (e) => {
  e.preventDefault();
  await Api.logout(); // stamps logout_at + duration on the session log
  sessionStorage.removeItem(SESSION_KEY);
  Api.clearToken();
  currentUser = null;
  showLogin();
});

function signOutForced(){
  sessionStorage.removeItem(SESSION_KEY);
  Api.clearToken();
  currentUser = null;
  showLogin();
}

/* ---------- Real-time (Socket.IO) ---------- */
function connectSocket(){
  if(Api.mock){
    // Demo Mode has no server to push events from — every mutation already
    // re-renders locally, so mark the status dot accordingly instead of
    // trying (and failing) to open a real WebSocket.
    const dot = document.getElementById("liveDot");
    const label = document.getElementById("liveLabel");
    dot?.classList.remove("offline");
    if(label) label.textContent = "Demo mode";
    return;
  }
  if(typeof io === "undefined") return; // CDN unreachable — dashboard still works, just not live
  socket = io(SOCKET_BASE, { transports: ["websocket", "polling"] });
  const dot = document.getElementById("liveDot");
  const label = document.getElementById("liveLabel");

  socket.on("connect", () => {
    dot?.classList.remove("offline");
    if(label) label.textContent = "Live";
    socket.emit("join", { room: "inventory" });
    if(isLogViewer()) socket.emit("join", { room: "logs" });
  });
  socket.on("disconnect", () => {
    dot?.classList.add("offline");
    if(label) label.textContent = "Reconnecting…";
  });

  socket.on("stock:update", (product) => {
    const idx = currentStock.findIndex(p => p.id === product.id);
    if(idx >= 0) currentStock[idx] = product; else currentStock.push(product);
    if(document.getElementById("inventoryView").style.display !== "none") renderInventory();
  });

  socket.on("log:inventory", (entry) => {
    toast(`${entry.actor_name || entry.actor_email} ${entry.action === "release" ? "released" : "added"} ${entry.qty} × ${entry.product_id}`);
    if(document.getElementById("logsView").style.display !== "none") loadInventoryLogs();
    if(document.getElementById("movementsView").style.display !== "none") loadMovements();
  });

  socket.on("log:session", (entry) => {
    if(document.getElementById("logsView").style.display !== "none") loadSessionLogs();
  });
}

/* ---------- Inventory (Real-Time Tracking System) ---------- */
async function loadStock(){
  const res = await Api.getStock();
  if(res.ok){ currentStock = res.data; }
  else if(res.status === 401){ signOutForced(); }
  else { currentStock = []; }
}

function stockBadgeClass(status){
  return { "in-stock":"stock-badge in-stock", "low-stock":"stock-badge low-stock", "out-of-stock":"stock-badge out-of-stock" }[status] || "stock-badge out-of-stock";
}

function renderInventory(){
  const search = (document.getElementById("inventorySearch").value || "").trim().toLowerCase();
  let items = currentStock;
  if(search){
    items = items.filter(p => (p.name || "").toLowerCase().includes(search) || p.id.toLowerCase().includes(search));
  }

  document.getElementById("invKpiTotal").textContent = currentStock.length;
  document.getElementById("invKpiIn").textContent = currentStock.filter(p => p.status === "in-stock").length;
  document.getElementById("invKpiLow").textContent = currentStock.filter(p => p.status === "low-stock").length;
  document.getElementById("invKpiOut").textContent = currentStock.filter(p => p.status === "out-of-stock").length;

  const body = document.getElementById("inventoryTableBody");
  const writable = canWriteStock();

  if(items.length === 0){
    body.innerHTML = `<tr><td colspan="6" class="empty-state">No products match your search.</td></tr>`;
    return;
  }

  body.innerHTML = items.map(p => `
    <tr>
      <td class="row-detail">${p.id}</td>
      <td><b>${p.name || "<span style=color:var(--ink-soft)>Untitled — pending catalog entry</span>"}</b></td>
      <td class="row-detail">${p.description || "—"}</td>
      <td><b>${p.quantity ?? 0}</b></td>
      <td><span class="${stockBadgeClass(p.status)}">${(p.status || "").replace("-", " ")}</span></td>
      <td>
        <div class="qty-actions">
          ${writable ? `
            <input type="number" min="1" value="1" id="qty-${p.id}">
            <button class="mini-btn supply" data-supply="${p.id}">+ Supply</button>
            <button class="mini-btn release" data-release="${p.id}">− Release</button>
          ` : ""}
          <button class="mini-btn" data-history="${p.id}">History</button>
        </div>
      </td>
    </tr>
  `).join("");

  body.querySelectorAll("[data-history]").forEach(btn => {
    btn.addEventListener("click", () => {
      switchView("movements");
      document.getElementById("movementProductFilter").value = btn.dataset.history;
      loadMovements();
    });
  });

  if(writable){
    body.querySelectorAll("[data-supply]").forEach(btn => {
      btn.addEventListener("click", () => doStockAction(btn.dataset.supply, "supply"));
    });
    body.querySelectorAll("[data-release]").forEach(btn => {
      btn.addEventListener("click", () => doStockAction(btn.dataset.release, "release"));
    });
  }
}

async function doStockAction(id, action){
  const qtyInput = document.getElementById(`qty-${id}`);
  const qty = Math.max(1, parseInt(qtyInput.value) || 1);
  const note = action === "release"
    ? (window.prompt("Note for this release (optional) — e.g. order #, reason:") || "")
    : (window.prompt("Note for this supply (optional) — e.g. supplier, PO #:") || "");

  const res = action === "release" ? await Api.releaseStock(id, qty, note) : await Api.supplyStock(id, qty, note);
  if(res.ok){
    toast(`${action === "release" ? "Released" : "Supplied"} ${qty} × ${id}`);
    await loadStock();
    renderInventory();
  } else {
    if(res.status === 401 || res.status === 403){ toast(res.error || "You don't have permission to do that."); return; }
    toast(res.error || "Action failed.");
  }
}

document.getElementById("inventorySearch").addEventListener("input", renderInventory);

/* ---------- Orders ---------- */
function badgeClass(status){
  return { Pending:"badge badge-pending", Processing:"badge badge-processing", Fulfilled:"badge badge-fulfilled" }[status] || "badge badge-pending";
}

async function fetchOrders(){
  const res = await Api.getOrders();
  if(res.ok) return res.data;
  if(res.status === 401) signOutForced();
  return [];
}

async function renderKPIs(){
  const orders = await fetchOrders();
  currentOrders = orders;
  document.getElementById("kpiOrders").textContent = orders.length;
  document.getElementById("kpiPending").textContent = orders.filter(o => o.status === "Pending").length;
  document.getElementById("kpiRevenue").textContent = fmtPHP(orders.reduce((s,o) => s + o.total, 0));
  document.getElementById("kpiClients").textContent = new Set(orders.map(o => o.facility)).size;
}

async function renderOrders(){
  const search = document.getElementById("orderSearch").value.trim().toLowerCase();
  const statusFilter = document.getElementById("statusFilter").value;
  const body = document.getElementById("ordersTableBody");

  let orders = currentOrders;
  if(statusFilter !== "all") orders = orders.filter(o => o.status === statusFilter);
  if(search){
    orders = orders.filter(o =>
      o.id.toLowerCase().includes(search) ||
      o.client.toLowerCase().includes(search) ||
      o.facility.toLowerCase().includes(search)
    );
  }

  if(orders.length === 0){
    body.innerHTML = `<tr><td colspan="6" class="empty-state">No orders match your filters.</td></tr>`;
    return;
  }

  const writable = canWriteOrders();

  body.innerHTML = orders.map(o => `
    <tr>
      <td class="row-detail">${o.id}</td>
      <td>
        <div><b>${o.client}</b></div>
        <div class="row-detail">${o.facility}</div>
      </td>
      <td class="row-detail">${o.lines.length} line item${o.lines.length > 1 ? "s" : ""}<br>${o.lines.map(l => `${l.qty}× ${l.id}`).join(", ")}
        ${o.notes && o.notes.length ? `<br><span title="${o.notes.map(n=>n.text).join(' • ')}">📝 ${o.notes.length} note${o.notes.length>1?'s':''}</span>` : ""}
      </td>
      <td><b>${fmtPHP(o.total)}</b></td>
      <td>
        ${writable ? `
          <select class="status-select" data-id="${o.id}" style="border:1px solid var(--line); border-radius:6px; padding:4px;">
            <option ${o.status==="Pending"?"selected":""}>Pending</option>
            <option ${o.status==="Processing"?"selected":""}>Processing</option>
            <option ${o.status==="Fulfilled"?"selected":""}>Fulfilled</option>
          </select>
          <button data-note="${o.id}" style="background:none;border:none;color:var(--ink-soft);font-size:11px;text-decoration:underline;display:block;margin-top:4px;">+ Add note</button>
        ` : `<span class="${badgeClass(o.status)}">${o.status}</span>`}
      </td>
      <td class="row-detail">${fmtDate(o.date)}</td>
    </tr>
  `).join("");

  if(writable){
    body.querySelectorAll(".status-select").forEach(sel => {
      sel.addEventListener("change", async () => {
        await Api.updateOrder(sel.dataset.id, { status: sel.value });
        await renderKPIs();
        await renderOrders();
      });
    });
    body.querySelectorAll("[data-note]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const text = window.prompt("Add a note to this order (the customer gets an email if the status also changes):");
        if(!text || !text.trim()) return;
        await Api.updateOrder(btn.dataset.note, { note: text.trim() });
        await renderOrders();
      });
    });
  }
}

async function renderClients(){
  const res = await Api.getClientsSummary();
  const rows = res.ok ? res.data : [];
  const body = document.getElementById("clientsTableBody");
  if(rows.length === 0){
    body.innerHTML = `<tr><td colspan="5" class="empty-state">No client activity yet.</td></tr>`;
    return;
  }
  body.innerHTML = rows.map(r => `
    <tr>
      <td><b>${r.client}</b></td>
      <td class="row-detail">${r.facility}</td>
      <td>${r.orders}</td>
      <td><b>${fmtPHP(r.spend)}</b></td>
      <td class="row-detail">${fmtDate(r.last)}</td>
    </tr>
  `).join("");
}

document.getElementById("orderSearch").addEventListener("input", renderOrders);
document.getElementById("statusFilter").addEventListener("change", renderOrders);

/* ---------- Stock movements (released & supplied — ALL roles) ---------- */
function timelineDotClass(action){
  return { opening:"dot-opening", monthly_opening:"dot-monthly", release:"dot-release", supply:"dot-supply" }[action] || "dot-supply";
}

async function renderMovementChips(){
  // A quick-jump row of product IDs that actually have activity, so on a
  // phone you can tap instead of typing an exact ID into the filter box.
  const res = await Api.getStockMovements({});
  const chipsEl = document.getElementById("movementProductChips");
  if(!res.ok){ chipsEl.innerHTML = ""; return; }
  const ids = [...new Set(res.data.map(l => l.product_id))].sort().slice(0, 24);
  const current = document.getElementById("movementProductFilter").value.trim();
  chipsEl.innerHTML = `<button class="chip ${!current ? "active" : ""}" data-chip="">All products</button>` +
    ids.map(id => `<button class="chip ${id === current ? "active" : ""}" data-chip="${id}">${id}</button>`).join("");
  chipsEl.querySelectorAll("[data-chip]").forEach(chip => {
    chip.addEventListener("click", () => {
      document.getElementById("movementProductFilter").value = chip.dataset.chip;
      loadMovements();
    });
  });
}

async function loadMovements(){
  const product = document.getElementById("movementProductFilter").value.trim();
  const action = document.getElementById("movementActionFilter").value;
  const params = {};
  if(product) params.product = product;
  if(action !== "all") params.action = action;

  const res = await Api.getStockMovements(params);
  const el = document.getElementById("movementsTimeline");
  if(!res.ok){ el.innerHTML = `<div class="empty-state">${res.error || "Could not load stock movements."}</div>`; return; }
  const rows = res.data;
  if(rows.length === 0){ el.innerHTML = `<div class="empty-state">No stock movements match your filter yet.</div>`; return; }

  el.innerHTML = rows.map(l => `
    <div class="timeline-item">
      <div class="timeline-dot ${timelineDotClass(l.action)}"></div>
      <div class="timeline-content">
        <div class="timeline-top">
          <span class="badge badge-${l.action}">${actionLabel(l.action)}</span>
          <span class="timeline-date">${fmtDate(l.at)}</span>
        </div>
        <div class="timeline-product"><b>${l.product_name || l.product_id}</b> <span class="row-detail">${l.product_id}</span></div>
        <div class="timeline-qty">${l.qty} unit${l.qty === 1 ? "" : "s"} &nbsp;·&nbsp; ${l.before} &rarr; ${l.after}</div>
        ${l.note ? `<div class="timeline-note">${l.note}</div>` : ""}
      </div>
    </div>
  `).join("");

  renderMovementChips();
}

document.getElementById("movementProductFilter").addEventListener("input", loadMovements);
document.getElementById("movementActionFilter").addEventListener("change", loadMovements);

/* ---------- Logs (superadmin + admin) ---------- */
async function loadSessionLogs(){
  const role = document.getElementById("sessionRoleFilter").value;
  const user = document.getElementById("sessionLogSearch").value.trim();
  const params = {};
  if(role !== "all") params.role = role;
  if(user) params.user = user;

  const res = await Api.getSessionLogs(params);
  const body = document.getElementById("sessionLogsTableBody");
  if(!res.ok){ body.innerHTML = `<tr><td colspan="5" class="empty-state">${res.error || "Could not load session logs."}</td></tr>`; return; }
  const rows = res.data;
  if(rows.length === 0){ body.innerHTML = `<tr><td colspan="5" class="empty-state">No sessions logged yet.</td></tr>`; return; }

  body.innerHTML = rows.map(s => `
    <tr>
      <td><b>${s.user_name || s.user_email}</b><div class="row-detail">${s.user_email}</div></td>
      <td><span class="badge badge-${s.role}">${roleLabel(s.role)}</span></td>
      <td class="row-detail">${fmtDate(s.login_at)}</td>
      <td class="row-detail">${s.logout_at ? fmtDate(s.logout_at) : "Still signed in"}</td>
      <td>${fmtDuration(s.duration_seconds)}</td>
    </tr>
  `).join("");
}

async function loadInventoryLogs(){
  const action = document.getElementById("invLogActionFilter").value;
  const params = {};
  if(action !== "all") params.action = action;

  const res = await Api.getInventoryLogs(params);
  const body = document.getElementById("invLogsTableBody");
  if(!res.ok){ body.innerHTML = `<tr><td colspan="8" class="empty-state">${res.error || "Could not load inventory logs."}</td></tr>`; return; }
  const rows = res.data;
  if(rows.length === 0){ body.innerHTML = `<tr><td colspan="8" class="empty-state">No stock changes logged yet.</td></tr>`; return; }

  body.innerHTML = rows.map(l => `
    <tr>
      <td><b>${l.product_name || l.product_id}</b><div class="row-detail">${l.product_id}</div></td>
      <td><span class="badge badge-${l.action}">${actionLabel(l.action)}</span></td>
      <td>${l.qty}</td>
      <td class="row-detail">${l.before} → ${l.after}</td>
      <td>${l.actor_name || l.actor_email}</td>
      <td><span class="badge badge-${l.role}">${roleLabel(l.role)}</span></td>
      <td class="row-detail">${l.note || "—"}</td>
      <td class="row-detail">${fmtDate(l.at)}</td>
    </tr>
  `).join("");
}

document.getElementById("sessionLogSearch").addEventListener("input", loadSessionLogs);
document.getElementById("sessionRoleFilter").addEventListener("change", loadSessionLogs);
document.getElementById("invLogActionFilter").addEventListener("change", loadInventoryLogs);

/* ---------- Users & roles (superadmin only) ---------- */
async function loadUsers(){
  const res = await Api.getUsers();
  const body = document.getElementById("usersTableBody");
  if(!res.ok){ body.innerHTML = `<tr><td colspan="4" class="empty-state">${res.error || "Could not load users."}</td></tr>`; return; }
  const rows = res.data;
  body.innerHTML = rows.map(u => `
    <tr>
      <td><b>${u.name}</b></td>
      <td class="row-detail">${u.email}</td>
      <td><span class="badge badge-${u.role}">${roleLabel(u.role)}</span></td>
      <td>
        <button class="mini-btn" data-edit="${u.email}">Edit</button>
        <button class="mini-btn release" data-delete="${u.email}">Remove</button>
      </td>
    </tr>
  `).join("");

  body.querySelectorAll("[data-edit]").forEach(btn => btn.addEventListener("click", () => openUserModal(btn.dataset.edit, rows.find(r => r.email === btn.dataset.edit))));
  body.querySelectorAll("[data-delete]").forEach(btn => btn.addEventListener("click", async () => {
    if(!confirm(`Remove account ${btn.dataset.delete}? This can't be undone.`)) return;
    const res = await Api.deleteUser(btn.dataset.delete);
    if(res.ok){ toast("Account removed."); await loadUsers(); } else { toast(res.error || "Could not remove account."); }
  }));
}

function openUserModal(editEmail, existing){
  document.getElementById("userModal").classList.add("open");
  document.getElementById("userModalTitle").textContent = editEmail ? "Edit account" : "New account";
  document.getElementById("um-name").value = existing?.name || "";
  document.getElementById("um-email").value = existing?.email || "";
  document.getElementById("um-email").disabled = !!editEmail;
  document.getElementById("um-role").value = existing?.role || "subadmin";
  document.getElementById("um-password").value = "";
  document.getElementById("um-password-hint").textContent = editEmail ? "(leave blank to keep current password)" : "";
  document.getElementById("userModal").dataset.editing = editEmail || "";
}
function closeUserModal(){ document.getElementById("userModal").classList.remove("open"); }

document.getElementById("newUserBtn").addEventListener("click", () => openUserModal(null, null));
document.getElementById("userModalCancel").addEventListener("click", closeUserModal);
document.getElementById("userModalSave").addEventListener("click", async () => {
  const editing = document.getElementById("userModal").dataset.editing;
  const name = document.getElementById("um-name").value.trim();
  const email = document.getElementById("um-email").value.trim();
  const role = document.getElementById("um-role").value;
  const password = document.getElementById("um-password").value;

  let res;
  if(editing){
    const payload = { name, role };
    if(password) payload.password = password;
    res = await Api.updateUser(editing, payload);
  } else {
    if(!password){ toast("Password is required for a new account."); return; }
    res = await Api.createUser({ name, email, role, password });
  }

  if(res.ok){ toast("Saved."); closeUserModal(); await loadUsers(); }
  else{ toast(res.error || "Could not save account."); }
});

/* ---------- Backups (superadmin only) ---------- */
async function loadBackups(){
  const res = await Api.listBackups();
  const body = document.getElementById("backupsTableBody");
  if(!res.ok){ body.innerHTML = `<tr><td colspan="3" class="empty-state">${res.error || "Could not load backups."}</td></tr>`; return; }
  const rows = res.data;
  if(rows.length === 0){ body.innerHTML = `<tr><td colspan="3" class="empty-state">No backups yet — run one above.</td></tr>`; return; }
  body.innerHTML = rows.map(b => `
    <tr>
      <td class="row-detail">${b.filename}</td>
      <td class="row-detail">${fmtDate(b.created_at)}</td>
      <td class="row-detail">${Object.entries(b.counts || {}).map(([k,v]) => `${k}: ${v}`).join(" · ")}</td>
    </tr>
  `).join("");
}

document.getElementById("runBackupBtn").addEventListener("click", async () => {
  const btn = document.getElementById("runBackupBtn");
  btn.disabled = true; btn.textContent = "Running…";
  const res = await Api.runBackup();
  btn.disabled = false; btn.textContent = "Run backup now";
  if(res.ok){ toast("Backup complete."); await loadBackups(); } else { toast(res.error || "Backup failed."); }
});

/* ---------- View switching ---------- */
const VIEW_META = {
  inventory: { title:"Inventory", sub:"Live stock levels — release and supply update every connected dashboard instantly." },
  movements: { title:"Stock movements", sub:"Every release and supply, for any role — filter by product to see its full quantity history over time." },
  orders:    { title:"Purchase orders", sub:"Every order submitted through the storefront, most recent first." },
  clients:   { title:"Client history", sub:"Purchase totals grouped by client facility." },
  logs:      { title:"Activity logs", sub:"Who logged in/out, when, for how long — and every stock add/deduct." },
  users:     { title:"Users & roles", sub:"Create staff accounts and assign Superadmin, Admin, or Sub-admin." },
  backup:    { title:"Backups", sub:"Snapshot the full system (products, orders, users, logs) to a downloadable file." },
};

async function switchView(view){
  document.querySelectorAll(".admin-side a[data-view]").forEach(a => a.classList.toggle("active", a.dataset.view === view));
  ["inventory","movements","orders","clients","logs","users","backup"].forEach(v => {
    document.getElementById(v + "View").style.display = v === view ? "block" : "none";
  });
  document.getElementById("orderKpiRow").style.display = (view === "orders") ? "grid" : "none";

  document.getElementById("viewTitle").textContent = VIEW_META[view].title;
  document.getElementById("viewSub").textContent = VIEW_META[view].sub;

  if(view === "inventory"){ await loadStock(); renderInventory(); }
  else if(view === "movements"){ await loadMovements(); }
  else if(view === "orders"){ await renderKPIs(); await renderOrders(); }
  else if(view === "clients"){ await renderClients(); }
  else if(view === "logs"){ await loadSessionLogs(); await loadInventoryLogs(); }
  else if(view === "users"){ await loadUsers(); }
  else if(view === "backup"){ await loadBackups(); }
}

document.querySelectorAll(".admin-side a[data-view]").forEach(link => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    switchView(link.dataset.view);
  });
});

/* ---------- Entry point ---------- */
(async () => {
  await Api.detect();
  if(Api.mock){
    const bar = document.createElement("div");
    bar.style.cssText = "background:var(--red); color:#fff; text-align:center; font-size:12.5px; font-weight:600; padding:8px 16px;";
    bar.textContent = "Demo Mode — no backend detected. All data below is sample data stored only in this browser.";
    document.body.prepend(bar);

    const hint = document.createElement("p");
    hint.className = "login-hint";
    hint.innerHTML = "Demo logins:<br>superadmin@irasethpharma.com / demo-superadmin<br>admin@irasethpharma.com / demo-admin<br>subadmin@irasethpharma.com / demo-subadmin";
    document.querySelector(".login-form")?.appendChild(hint);
  }

  const saved = sessionStorage.getItem(SESSION_KEY);
  if(saved && Api.getToken()){
    currentUser = JSON.parse(saved);
    // Verify the token is still valid (and re-sync role) before trusting it.
    const res = await Api.me();
    if(res.ok){
      currentUser = res.data;
      await showDashboard();
      return;
    }
  }
  showLogin();
})();
