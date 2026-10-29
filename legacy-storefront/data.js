// Product catalog + cart — PRODUCTS is populated from the backend at runtime.

let PRODUCTS = [];

function getCategories(){
  const seen = new Map();
  seen.set("all", "All products");
  for(const p of PRODUCTS){
    if(p.category && !seen.has(p.category)){
      seen.set(p.category, p.category.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase()));
    }
  }
  return Array.from(seen, ([id, label]) => ({ id, label }));
}

function fmtPHP(n){
  return "₱" + Number(n || 0).toLocaleString("en-PH", { minimumFractionDigits:2, maximumFractionDigits:2 });
}

// Cart
const Cart = {
  KEY: "iraseth_cart",
  get(){
    try{ return JSON.parse(localStorage.getItem(this.KEY)) || []; }
    catch(e){ return []; }
  },
  save(items){ localStorage.setItem(this.KEY, JSON.stringify(items)); },
  add(productId, qty){
    const items = this.get();
    const existing = items.find(i => i.id === productId);
    if(existing){ existing.qty += qty; } else { items.push({ id: productId, qty }); }
    this.save(items);
  },
  remove(productId){
    this.save(this.get().filter(i => i.id !== productId));
  },
  clear(){ this.save([]); },
  count(){ return this.get().reduce((n,i) => n + i.qty, 0); },
  total(){
    return this.get().reduce((sum,i) => {
      const p = PRODUCTS.find(p => p.id === i.id);
      return sum + (p ? (p.price || 0) * i.qty : 0);
    }, 0);
  },
  lines(){
    return this.get().map(i => {
      const p = PRODUCTS.find(p => p.id === i.id);
      return p ? { ...p, qty:i.qty, lineTotal: (p.price || 0) * i.qty } : null;
    }).filter(Boolean);
  }
};

// Orders
const Orders = {
  async create({ client, email, facility }){
    const lines = Cart.lines();
    const res = await Api.createOrder({
      client, email, facility,
      lines: lines.map(l => ({ id: l.id, qty: l.qty })),
    });
    if(res.ok){
      Cart.clear();
      return { ok:true, order: res.data };
    }
    return { ok:false, error: res.error || "Could not reach the ordering server. Please try again." };
  },
};
