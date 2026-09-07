/* =========================================================
   IRASETH PHARMA — Public site logic
   Catalog rendering, cart drawer, and checkout submission.
   ========================================================= */

let activeCat = new URLSearchParams(location.search).get("cat") || "all";
let query = "";

async function loadProducts(){
  const live = await Api.getProducts();
  if(live && live.length){
    PRODUCTS = live;
  }
  // else: keep DEMO_PRODUCTS (already assigned as PRODUCTS in data.js)
}

function renderFilters(){
  const el = document.getElementById("filterList");
  if(!el) return;
  el.innerHTML = CATEGORIES.map(c => `
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

function renderGrid(){
  const grid = document.getElementById("productGrid");
  if(!grid) return;
  const items = PRODUCTS.filter(p => {
    const matchCat = activeCat === "all" || p.cat === activeCat;
    const matchQuery = !query || p.name.toLowerCase().includes(query) || p.id.toLowerCase().includes(query);
    return matchCat && matchQuery;
  });

  if(items.length === 0){
    grid.innerHTML = `<p class="empty-note">No products match your search.</p>`;
    return;
  }

  grid.innerHTML = items.map(p => `
    <div class="product-card">
      <div class="product-img">${p.id}</div>
      <div class="product-body">
        <span class="product-tag">${p.tag}</span>
        <h4>${p.name}</h4>
        <span class="sku">${p.unit}</span>
        <div class="product-foot">
          <span class="product-price"><span class="srp-label">SRP</span> ${fmtPHP(p.price)}</span>
          <span class="${p.stock === 'in' ? 'stock-ok' : 'stock-low'}">${p.stock === 'in' ? '● In stock' : '● Low stock'}</span>
        </div>
        <div class="qty-add">
          <input type="number" min="1" value="1" id="qty-${p.id}">
          <button class="add-btn" data-add="${p.id}">Add to order</button>
        </div>
      </div>
    </div>
  `).join("");

  grid.querySelectorAll("[data-add]").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.add;
      const qtyInput = document.getElementById("qty-" + id);
      const qty = Math.max(1, parseInt(qtyInput.value) || 1);
      Cart.add(id, qty);
      renderCartCount();
      btn.textContent = "Added ✓";
      btn.classList.add("added");
      setTimeout(() => { btn.textContent = "Add to order"; btn.classList.remove("added"); }, 1200);
    });
  });
}

/* ---------- Cart drawer ---------- */
function renderCartCount(){
  document.querySelectorAll(".cart-count").forEach(el => el.textContent = Cart.count());
}

function renderCartDrawer(){
  const wrap = document.getElementById("cartItems");
  const footTotal = document.getElementById("cartTotal");
  if(!wrap) return;
  const lines = Cart.lines();
  if(lines.length === 0){
    wrap.innerHTML = `<p class="empty-note">Your order slip is empty.<br>Add products from the catalog to get started.</p>`;
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

    const order = await Orders.create({ client, email, facility });

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
