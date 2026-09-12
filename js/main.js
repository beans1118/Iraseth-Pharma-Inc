// Public site logic — catalog rendering, cart drawer, checkout.

let activeCat = new URLSearchParams(location.search).get("cat") || "all";
let query = "";

function showDemoBanner(){
  // intentionally no visible banner — demo/mock mode still runs silently underneath
}

async function loadProducts(){
  const live = await Api.getProducts();
  if(live){
    PRODUCTS = live;
  } else {
    console.warn("Could not reach the product catalog API — is the backend running?");
  }
}

function renderFilters(){
  const el = document.getElementById("filterList");
  if(!el) return;
  const categories = getCategories();
  el.innerHTML = categories.map(c => `
    <button data-cat="${c.id}" class="${c.id === activeCat ? "active" : ""}">${c.label}</button>
  `).join("");
  el.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", () => {
      activeCat = btn.dataset.cat;
      renderFilters();
      renderGrid();
    });
  });
}

const STOCK_LABEL = { "in-stock":"● In stock", "low-stock":"● Low stock", "out-of-stock":"● Out of stock" };

function renderGrid(){
  const grid = document.getElementById("productGrid");
  if(!grid) return;
  const items = PRODUCTS.filter(p => {
    const matchCat = activeCat === "all" || p.category === activeCat;
    const matchQuery = !query || (p.name || "").toLowerCase().includes(query) || p.id.toLowerCase().includes(query);
    return matchCat && matchQuery;
  });

  if(items.length === 0){
    grid.innerHTML = `<p class="empty-state">No products match your search yet.</p>`;
    return;
  }

  grid.innerHTML = items.map(p => `
    <div class="product-card">
      <span class="brand">${p.id}</span>
      <h4 data-view-product="${p.id}">${p.name || "Untitled product"}</h4>
      ${p.description ? `<p style="font-size:12.5px; margin:0;">${p.description}</p>` : ""}
      ${p.category ? `<span class="tag">${p.category}</span>` : ""}
      <div class="price-row">
        <span class="price">${fmtPHP(p.price)}</span>
        <span class="stock-badge ${p.status || "out-of-stock"}">${STOCK_LABEL[p.status] || "● Out of stock"}</span>
      </div>
      <div class="qty-row" style="display:flex; gap:8px; align-items:center; margin-top:6px;">
        <input type="number" min="1" value="1" id="qty-${p.id}" style="width:60px; padding:8px; border:1px solid var(--line); border-radius:6px;">
        <button class="btn btn-primary add-btn" data-add="${p.id}" ${p.status === "out-of-stock" ? "disabled" : ""}>Add to order</button>
      </div>
    </div>
  `).join("");

  grid.querySelectorAll("[data-view-product]").forEach(name => {
    name.addEventListener("click", () => openProductModal(name.dataset.viewProduct));
  });

  grid.querySelectorAll("[data-add]").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.add;
      const qtyInput = document.getElementById("qty-" + id);
      const qty = Math.max(1, parseInt(qtyInput.value) || 1);
      Cart.add(id, qty);
      renderCartCount();
      btn.textContent = "Added ✓";
      setTimeout(() => { btn.textContent = "Add to order"; }, 1200);
    });
  });
}

// Product quick view
function openProductModal(id){
  const p = PRODUCTS.find(p => p.id === id);
  if(!p) return;

  document.getElementById("pm-id").textContent = p.id;
  document.getElementById("pm-name").textContent = p.name || "Untitled product";
  document.getElementById("pm-category").textContent = p.category || "Uncategorized";
  document.getElementById("pm-category").style.display = p.category ? "" : "none";
  document.getElementById("pm-description").textContent = p.description || "No description available yet.";
  document.getElementById("pm-price").textContent = fmtPHP(p.price);
  document.getElementById("pm-unit").textContent = p.unit || "";
  document.getElementById("pm-qty").value = 1;

  const stockEl = document.getElementById("pm-stock");
  stockEl.className = "stock-badge " + (p.status || "out-of-stock");
  stockEl.textContent = (STOCK_LABEL[p.status] || "● Out of stock").replace("● ", "");

  const specsList = document.getElementById("pm-specs-list");
  if(p.specs && p.specs.length){
    specsList.innerHTML = p.specs.map(s => `
      <div class="pm-specs-row"><span>${s.label}</span><span>${s.value}</span></div>
    `).join("");
  } else {
    specsList.innerHTML = `<div class="pm-specs-empty">Full specifications for this product haven't been added to the catalog yet — check back soon, or contact us for a spec sheet.</div>`;
  }

  const addBtn = document.getElementById("pm-add");
  addBtn.disabled = p.status === "out-of-stock";
  addBtn.textContent = p.status === "out-of-stock" ? "Out of stock" : "Add to order";
  addBtn.onclick = () => {
    const qty = Math.max(1, parseInt(document.getElementById("pm-qty").value) || 1);
    Cart.add(id, qty);
    renderCartCount();
    addBtn.textContent = "Added ✓";
    setTimeout(() => { addBtn.textContent = "Add to order"; }, 1200);
  };

  document.getElementById("productModalBackdrop").classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeProductModal(){
  document.getElementById("productModalBackdrop").classList.remove("open");
  document.body.style.overflow = "";
}

document.getElementById("productModalClose")?.addEventListener("click", closeProductModal);
document.getElementById("productModalBackdrop")?.addEventListener("click", (e) => {
  if(e.target.id === "productModalBackdrop") closeProductModal();
});
document.addEventListener("keydown", (e) => {
  if(e.key === "Escape") closeProductModal();
});

// Cart drawer
function renderCartCount(){
  document.querySelectorAll(".cart-count").forEach(el => el.textContent = Cart.count());
}

function renderCartDrawer(){
  const wrap = document.getElementById("cartItems");
  const footTotal = document.getElementById("cartTotal");
  if(!wrap) return;
  const lines = Cart.lines();
  if(lines.length === 0){
    wrap.innerHTML = `<p class="empty-state">Your order slip is empty.<br>Add products from the catalog to get started.</p>`;
  } else {
    wrap.innerHTML = lines.map(l => `
      <div class="cart-line">
        <div>
          <div class="name">${l.name}</div>
          <div class="meta">${l.qty} × ${l.unit} — SRP ${fmtPHP(l.price)}</div>
        </div>
        <div style="text-align:right;">
          <div class="meta">${fmtPHP(l.lineTotal)}</div>
          <button class="rm" data-remove="${l.id}">Remove</button>
        </div>
      </div>
    `).join("");
  }
  if(footTotal) footTotal.textContent = fmtPHP(Cart.total());
  renderCartCount();

  wrap.querySelectorAll("[data-remove]").forEach(btn => {
    btn.addEventListener("click", () => {
      Cart.remove(btn.dataset.remove);
      renderCartDrawer();
    });
  });

  const checkoutBtn = document.getElementById("checkoutBtn");
  if(checkoutBtn) checkoutBtn.disabled = lines.length === 0;
}

function openCart(){
  document.getElementById("cartDrawer")?.classList.add("open");
  document.getElementById("overlay")?.classList.add("open");
  renderCartDrawer();
}
function closeCart(){
  document.getElementById("cartDrawer")?.classList.remove("open");
  document.getElementById("overlay")?.classList.remove("open");
}

document.addEventListener("DOMContentLoaded", async () => {
  await Api.detect();
  showDemoBanner();
  await loadProducts();
  renderFilters();
  renderGrid();
  renderCartCount();

  // Rotating hero background carousel
  const slides = document.querySelectorAll("#heroCarousel .hero-slide");
  if(slides.length > 1){
    let current = 0;
    setInterval(() => {
      slides[current].classList.remove("active");
      current = (current + 1) % slides.length;
      slides[current].classList.add("active");
    }, 4500);
  }

  document.getElementById("searchInput")?.addEventListener("input", (e) => {
    query = e.target.value.trim().toLowerCase();
    renderGrid();
  });

  document.getElementById("cartToggle")?.addEventListener("click", () => {
    closeNav();
    openCart();
  });
  document.getElementById("cartClose")?.addEventListener("click", closeCart);
  document.getElementById("overlay")?.addEventListener("click", closeCart);

  // Mobile nav toggle
  const nav = document.getElementById("siteNav");
  const navToggle = document.getElementById("navToggle");
  function closeNav(){
    nav?.classList.remove("open");
    navToggle?.setAttribute("aria-expanded", "false");
  }
  navToggle?.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });
  nav?.querySelectorAll("a").forEach(a => a.addEventListener("click", closeNav));

  document.getElementById("checkoutForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const client = document.getElementById("cf-name").value.trim();
    const email = document.getElementById("cf-email").value.trim();
    const facility = document.getElementById("cf-facility").value.trim();
    if(!client || !email || !facility || Cart.lines().length === 0) return;

    const checkoutBtn = document.getElementById("checkoutBtn");
    if(checkoutBtn){ checkoutBtn.disabled = true; checkoutBtn.textContent = "Submitting…"; }

    const result = await Orders.create({ client, email, facility });

    if(!result.ok){
      if(checkoutBtn){ checkoutBtn.disabled = false; checkoutBtn.textContent = "Submit order"; }
      const conf = document.getElementById("orderConfirm");
      if(conf) conf.innerHTML = `<p style="color:var(--danger); font-size:13.5px; text-align:center;">${result.error}</p>`;
      return;
    }
    const order = result.order;

    const conf = document.getElementById("orderConfirm");
    if(conf){
      conf.innerHTML = `
        <div class="slip" style="max-width:460px; margin:0 auto;">
          <div class="perf"></div>
          <div class="slip-head">
            <span class="id">${order.id}</span>
            <span class="status">Submitted</span>
          </div>
          <div class="slip-body">
            ${order.lines.map(l => `
              <div class="slip-row">
                <span class="name">${l.name}</span>
                <span class="meta">${l.qty} × ${l.unit}</span>
              </div>
            `).join("")}
          </div>
          <div class="slip-foot">
            <span>Billed to ${order.facility}</span>
            <span class="total">${fmtPHP(order.total)}</span>
          </div>
        </div>
        <p style="text-align:center; color:var(--ink-soft); font-size:13.5px; margin-top:18px;">
          Order received. Our team will confirm availability and delivery timing to <b>${order.email}</b> shortly.
        </p>
      `;
    }
    document.getElementById("checkoutForm").style.display = "none";
    renderCartCount();
  });
});
