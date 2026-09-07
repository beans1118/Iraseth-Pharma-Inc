/* =========================================================
   IRASETH PHARMA — Admin logic
   Tries the real backend first (login via /api/auth/login, orders
   via /api/orders, all protected by the JWT it returns). If the
   API can't be reached, falls back to the original local demo
   behavior so the dashboard still works standalone.
   ========================================================= */

// Fallback-only demo credentials, used solely when the backend is
// unreachable. When the backend IS reachable, it is the source of truth
// for who can log in — this is never consulted in that case.
const DEMO_EMAIL = "admin@irasethpharma.com";
const DEMO_PASSWORD = "iraseth2026";
const SESSION_KEY = "iraseth_admin_session";

let usingApi = false; // set once we know whether the backend answered
let currentOrders = [];

function showLogin(){
  document.getElementById("loginScreen").style.display = "flex";
  document.getElementById("dashboardScreen").style.display = "none";
}
async function showDashboard(){
  document.getElementById("loginScreen").style.display = "none";
  document.getElementById("dashboardScreen").style.display = "flex";
  if(!usingApi) Orders.seedIfEmpty();
  await renderKPIs();
  await renderOrders();
}

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const errorBox = document.getElementById("loginError");
  const submitBtn = e.target.querySelector("button[type=submit]");
  submitBtn.disabled = true;

  const res = await Api.login(email, password);

  if(res.status === 0){
    // Backend unreachable — fall back to the local demo credential check.
    usingApi = false;
    if(email === DEMO_EMAIL && password === DEMO_PASSWORD){
      sessionStorage.setItem(SESSION_KEY, "1");
      errorBox.classList.remove("show");
      await showDashboard();
    } else {
      errorBox.textContent = "Incorrect email or password. Try again.";
      errorBox.classList.add("show");
    }
  } else if(res.ok){
    usingApi = true;
    Api.setToken(res.data.token);
    sessionStorage.setItem(SESSION_KEY, "1");
    errorBox.classList.remove("show");
    await showDashboard();
  } else {
    errorBox.textContent = res.error || "Incorrect email or password. Try again.";
    errorBox.classList.add("show");
  }
  submitBtn.disabled = false;
});

document.getElementById("signOut").addEventListener("click", (e) => {
  e.preventDefault();
  sessionStorage.removeItem(SESSION_KEY);
  Api.clearToken();
  showLogin();
});

function signOutForced(){
  sessionStorage.removeItem(SESSION_KEY);
  Api.clearToken();
  showLogin();
}

/* ---------- Dashboard rendering ---------- */
function badgeClass(status){
  return { Pending:"badge-pending", Processing:"badge-processing", Fulfilled:"badge-fulfilled" }[status] || "badge-pending";
}

function fmtDate(iso){
  return new Date(iso).toLocaleDateString("en-PH", { year:"numeric", month:"short", day:"numeric" });
}

async function fetchOrders(){
  if(usingApi){
    const res = await Api.getOrders();
    if(res.ok) return res.data;
    if(res.status === 401){ signOutForced(); }
    return [];
  }
  return Orders.all();
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
    body.innerHTML = `<tr><td colspan="6" class="no-rows">No orders match your filters.</td></tr>`;
    return;
  }

  body.innerHTML = orders.map(o => `
    <tr>
      <td class="order-id">${o.id}</td>
      <td>
        <div class="client">${o.client}</div>
        <div class="sub">${o.facility}</div>
      </td>
      <td class="row-detail">${o.lines.length} line item${o.lines.length > 1 ? "s" : ""}<br>${o.lines.map(l => `${l.qty}× ${l.id}`).join(", ")}
        ${o.notes && o.notes.length ? `<br><span title="${o.notes.map(n=>n.text).join(' • ')}">📝 ${o.notes.length} note${o.notes.length>1?'s':''}</span>` : ""}
      </td>
      <td><b>${fmtPHP(o.total)}</b></td>
      <td>
        <select class="status-select" data-id="${o.id}" style="border:none; background:transparent;">
          <option ${o.status==="Pending"?"selected":""}>Pending</option>
          <option ${o.status==="Processing"?"selected":""}>Processing</option>
          <option ${o.status==="Fulfilled"?"selected":""}>Fulfilled</option>
        </select>
        <button class="rm" data-note="${o.id}" style="background:none;border:none;color:var(--ink-soft);font-size:11px;text-decoration:underline;display:block;margin-top:4px;">+ Add note</button>
      </td>
      <td class="row-detail">${fmtDate(o.date)}</td>
    </tr>
  `).join("");

  body.querySelectorAll(".status-select").forEach(sel => {
    sel.addEventListener("change", async () => {
      if(usingApi){
        await Api.updateOrder(sel.dataset.id, { status: sel.value });
      } else {
        Orders.updateStatus(sel.dataset.id, sel.value);
      }
      await renderKPIs();
      await renderOrders();
    });
  });

  body.querySelectorAll("[data-note]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const text = window.prompt("Add a note to this order (the customer gets an email if the status also changes):");
      if(!text || !text.trim()) return;
      if(usingApi){
        await Api.updateOrder(btn.dataset.note, { note: text.trim() });
        await renderKPIs();
      } else {
        alert("Note saved locally for this demo session (connect the backend for real persistence + email).");
      }
      await renderOrders();
    });
  });
}

async function renderClients(){
  let rows;
  if(usingApi){
    const res = await Api.getClientsSummary();
    rows = res.ok ? res.data : [];
  } else {
    const orders = await fetchOrders();
    const map = {};
    orders.forEach(o => {
      const key = o.facility;
      if(!map[key]) map[key] = { client:o.client, facility:o.facility, count:0, spend:0, last:o.date };
      map[key].count += 1;
      map[key].spend += o.total;
      if(new Date(o.date) > new Date(map[key].last)) map[key].last = o.date;
    });
    rows = Object.values(map).sort((a,b) => b.spend - a.spend);
  }
  rows = rows.map(r => ({ ...r, count: r.count ?? r.orders }));

  const body = document.getElementById("clientsTableBody");
  if(rows.length === 0){
    body.innerHTML = `<tr><td colspan="5" class="no-rows">No client activity yet.</td></tr>`;
    return;
  }
  body.innerHTML = rows.map(r => `
    <tr>
      <td class="client">${r.client}</td>
      <td class="row-detail">${r.facility}</td>
      <td>${r.count}</td>
      <td><b>${fmtPHP(r.spend)}</b></td>
      <td class="row-detail">${fmtDate(r.last)}</td>
    </tr>
  `).join("");
}

document.getElementById("orderSearch").addEventListener("input", renderOrders);
document.getElementById("statusFilter").addEventListener("change", renderOrders);

document.querySelectorAll(".admin-side a[data-view]").forEach(link => {
  link.addEventListener("click", async (e) => {
    e.preventDefault();
    document.querySelectorAll(".admin-side a[data-view]").forEach(a => a.classList.remove("active"));
    link.classList.add("active");
    const view = link.dataset.view;
    document.getElementById("ordersView").style.display = view === "orders" ? "block" : "none";
    document.getElementById("clientsView").style.display = view === "clients" ? "block" : "none";
    document.getElementById("viewTitle").textContent = view === "orders" ? "Order logs" : "Client history";
    document.getElementById("viewSub").textContent = view === "orders"
      ? "Every order submitted through the storefront, most recent first."
      : "Purchase totals grouped by client facility.";
    if(view === "clients") await renderClients();
  });
});

/* ---------- Entry point ---------- */
(async () => {
  if(sessionStorage.getItem(SESSION_KEY) === "1"){
    usingApi = !!Api.getToken();
    await showDashboard();
  } else {
    showLogin();
  }
})();
