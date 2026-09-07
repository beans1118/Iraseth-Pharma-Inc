/* =========================================================
   IRASETH PHARMA — Product catalog
   DEMO_PRODUCTS is the offline fallback used automatically when
   the backend (see /backend) isn't reachable. PRODUCTS is the
   live variable everything else in the app reads from — main.js
   overwrites it with data from the API when available.
   ========================================================= */
const DEMO_PRODUCTS = [
  { id:"IRP-1001", name:"Disposable Syringe 1 mL 26G", cat:"syringes-needles", tag:"Syringes", brand:"ALPHASHOT", price:1220.0, unit:"per unit", stock:"in" },
  { id:"IRP-1002", name:"Disposable Syringe 3 mL 26G", cat:"syringes-needles", tag:"Syringes", brand:"ALPHASHOT", price:608.0, unit:"per unit", stock:"in" },
  { id:"IRP-1003", name:"Disposable Syringe 5 mL 22G", cat:"syringes-needles", tag:"Syringes", brand:"ALPHASHOT", price:640.0, unit:"per unit", stock:"in" },
  { id:"IRP-1004", name:"Disposable Syringe 10 mL 21G", cat:"syringes-needles", tag:"Syringes", brand:"ALPHASHOT", price:850.0, unit:"per unit", stock:"in" },
  { id:"IRP-1005", name:"Adult Diaper S", cat:"patient-care", tag:"Patient Care", brand:"ALPHACARE", price:250.0, unit:"per unit", stock:"in" },
  { id:"IRP-1006", name:"Adult Diaper M", cat:"patient-care", tag:"Patient Care", brand:"ALPHACARE", price:260.0, unit:"per unit", stock:"in" },
  { id:"IRP-1007", name:"Adult Diaper L", cat:"patient-care", tag:"Patient Care", brand:"ALPHACARE", price:280.0, unit:"per unit", stock:"in" },
  { id:"IRP-1008", name:"Adult Diaper XL", cat:"patient-care", tag:"Patient Care", brand:"ALPHACARE", price:330.0, unit:"per unit", stock:"in" },
  { id:"IRP-1009", name:"Underpads", cat:"patient-care", tag:"Patient Care", brand:"ALPHACARE", price:280.0, unit:"per unit", stock:"in" },
  { id:"IRP-1010", name:"Needle Retractable Safety Syringe 1mL with needle 27G x 3/8\"", cat:"syringes-needles", tag:"Safety Syringes", brand:"IRASAFETY", price:2800.0, unit:"per unit", stock:"in" },
  { id:"IRP-1011", name:"Needle Retractable Safety Syringe 5mL with needle", cat:"syringes-needles", tag:"Safety Syringes", brand:"IRASAFETY", price:1400.0, unit:"per unit", stock:"in" },
  { id:"IRP-1012", name:"Needle Retractable Safety Syringe 10mL with needle", cat:"syringes-needles", tag:"Safety Syringes", brand:"IRASAFETY", price:1465.0, unit:"per unit", stock:"in" },
  { id:"IRP-1013", name:"Needle Retractable Safety Syringe 3mL with needle 27G x 3/8\"", cat:"syringes-needles", tag:"Safety Syringes", brand:"IRASAFETY", price:1410.0, unit:"per unit", stock:"in" },
  { id:"IRP-1014", name:"IV Administration Set with Burette (Soluset) 150 mL", cat:"iv-therapy", tag:"IV Administration", brand:"POLYVOL", price:850.0, unit:"per unit", stock:"in" },
  { id:"IRP-1015", name:"IV Administration Set with Burette (Soluset) 110 mL", cat:"iv-therapy", tag:"IV Administration", brand:"POLYVOL", price:670.0, unit:"per unit", stock:"in" },
  { id:"IRP-1016", name:"IV Infusion Set (Macroset)", cat:"iv-therapy", tag:"IV Infusion", brand:"AUTOFUSION", price:1740.0, unit:"per box", stock:"in" },
  { id:"IRP-1017", name:"IV Infusion Set (Macroset)", cat:"iv-therapy", tag:"IV Infusion", brand:"AUTOFUSION", price:58.0, unit:"per piece", stock:"in" },
  { id:"IRP-1018", name:"Blood Administration Set", cat:"iv-therapy", tag:"Blood Administration", brand:"HAEMOFUSOR", price:2450.0, unit:"per box", stock:"in" },
  { id:"IRP-1019", name:"Blood Administration Set", cat:"iv-therapy", tag:"Blood Administration", brand:"HAEMOFUSOR", price:98.0, unit:"per piece", stock:"in" },
  { id:"IRP-1020", name:"IV Infusion Set (Microset)", cat:"iv-therapy", tag:"IV Infusion", brand:"MICROFUSION", price:700.0, unit:"per box", stock:"in" },
  { id:"IRP-1021", name:"IV Infusion Set (Microset)", cat:"iv-therapy", tag:"IV Infusion", brand:"MICROFUSION", price:28.0, unit:"per piece", stock:"in" },
  { id:"IRP-1022", name:"IV Administration Set with Burette (Soluset) 150mL", cat:"iv-therapy", tag:"IV Administration", brand:"POLYVOL", price:85.0, unit:"per unit", stock:"in" },
  { id:"IRP-1023", name:"IV Administration Set with Burette (Soluset) 110mL", cat:"iv-therapy", tag:"IV Administration", brand:"POLYVOL", price:68.0, unit:"per unit", stock:"in" },
  { id:"IRP-1024", name:"IV Cannula with Safety Features G16", cat:"iv-therapy", tag:"Safety IV Cannula", brand:"POLYSAFETY", price:2662.0, unit:"per box", stock:"in" },
  { id:"IRP-1025", name:"IV Cannula with Safety Features G16", cat:"iv-therapy", tag:"Safety IV Cannula", brand:"POLYSAFETY", price:54.0, unit:"per piece", stock:"in" },
  { id:"IRP-1026", name:"IV Cannula with Safety Features G18", cat:"iv-therapy", tag:"Safety IV Cannula", brand:"POLYSAFETY", price:2662.0, unit:"per box", stock:"in" },
  { id:"IRP-1027", name:"IV Cannula with Safety Features G18", cat:"iv-therapy", tag:"Safety IV Cannula", brand:"POLYSAFETY", price:54.0, unit:"per piece", stock:"in" },
  { id:"IRP-1028", name:"IV Cannula with Safety Features G20", cat:"iv-therapy", tag:"Safety IV Cannula", brand:"POLYSAFETY", price:2662.0, unit:"per box", stock:"in" },
  { id:"IRP-1029", name:"IV Cannula with Safety Features G20", cat:"iv-therapy", tag:"Safety IV Cannula", brand:"POLYSAFETY", price:54.0, unit:"per piece", stock:"in" },
  { id:"IRP-1030", name:"IV Cannula with Safety Features G22", cat:"iv-therapy", tag:"Safety IV Cannula", brand:"POLYSAFETY", price:2662.0, unit:"per box", stock:"in" },
  { id:"IRP-1031", name:"IV Cannula with Safety Features G22", cat:"iv-therapy", tag:"Safety IV Cannula", brand:"POLYSAFETY", price:54.0, unit:"per piece", stock:"in" },
  { id:"IRP-1032", name:"IV Cannula with Safety Features G24", cat:"iv-therapy", tag:"Safety IV Cannula", brand:"POLYSAFETY", price:2783.0, unit:"per box", stock:"in" },
  { id:"IRP-1033", name:"IV Cannula with Safety Features G24", cat:"iv-therapy", tag:"Safety IV Cannula", brand:"POLYSAFETY", price:56.0, unit:"per piece", stock:"in" },
  { id:"IRP-1034", name:"IV Cannula with Safety Features G26", cat:"iv-therapy", tag:"Safety IV Cannula", brand:"POLYSAFETY", price:3025.0, unit:"per box", stock:"in" },
  { id:"IRP-1035", name:"IV Cannula with Safety Features G26", cat:"iv-therapy", tag:"Safety IV Cannula", brand:"POLYSAFETY", price:61.0, unit:"per piece", stock:"in" },
  { id:"IRP-1036", name:"IV Cannula G16", cat:"iv-therapy", tag:"IV Cannula", brand:"POLYFLON", price:1330.0, unit:"per unit", stock:"in" },
  { id:"IRP-1037", name:"IV Cannula G18", cat:"iv-therapy", tag:"IV Cannula", brand:"POLYFLON", price:1180.0, unit:"per unit", stock:"in" },
  { id:"IRP-1038", name:"IV Cannula G20", cat:"iv-therapy", tag:"IV Cannula", brand:"POLYFLON", price:1180.0, unit:"per unit", stock:"in" },
  { id:"IRP-1039", name:"IV Cannula G22", cat:"iv-therapy", tag:"IV Cannula", brand:"POLYFLON", price:1180.0, unit:"per unit", stock:"in" },
  { id:"IRP-1040", name:"IV Cannula G24", cat:"iv-therapy", tag:"IV Cannula", brand:"POLYFLON", price:1420.0, unit:"per unit", stock:"in" },
  { id:"IRP-1041", name:"IV Cannula G26", cat:"iv-therapy", tag:"IV Cannula", brand:"POLYFLON", price:1635.0, unit:"per unit", stock:"in" },
];

// The live catalog the rest of the app reads from. Starts as the offline
// demo data; main.js swaps this out for real data from the API on load.
let PRODUCTS = DEMO_PRODUCTS;

const CATEGORIES = [
  { id:"all", label:"All products" },
  { id:"syringes-needles", label:"Syringes & Needles" },
  { id:"iv-therapy", label:"IV Therapy" },
  { id:"patient-care", label:"Patient Care" },
];

function fmtPHP(n){
  return "₱" + n.toLocaleString("en-PH", { minimumFractionDigits:2, maximumFractionDigits:2 });
}

/* ---------- Cart (localStorage-backed, client-side demo) ---------- */
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
      return sum + (p ? p.price * i.qty : 0);
    }, 0);
  },
  lines(){
    return this.get().map(i => {
      const p = PRODUCTS.find(p => p.id === i.id);
      return p ? { ...p, qty:i.qty, lineTotal: p.price * i.qty } : null;
    }).filter(Boolean);
  }
};

/* ---------- Orders (submitted carts become "orders" for admin) ---------- */
const Orders = {
  KEY: "iraseth_orders",
  all(){
    try{ return JSON.parse(localStorage.getItem(this.KEY)) || []; }
    catch(e){ return []; }
  },
  save(orders){ localStorage.setItem(this.KEY, JSON.stringify(orders)); },
  async create({ client, email, facility }){
    const lines = Cart.lines();

    // Try the real backend first — it re-prices from the DB and persists
    // to Mongo. Falls back to the local demo behavior if unreachable.
    const res = await Api.createOrder({
      client, email, facility,
      lines: lines.map(l => ({ id: l.id, qty: l.qty })),
    });
    if(res.ok){
      Cart.clear();
      return res.data;
    }

    const orders = this.all();
    const order = {
      id: "PO-" + String(20260000 + orders.length + 1),
      client, email, facility,
      lines,
      total: Cart.total(),
      status: "Pending",
      date: new Date().toISOString(),
    };
    orders.unshift(order);
    this.save(orders);
    Cart.clear();
    return order;
  },
  updateStatus(id, status){
    const orders = this.all().map(o => o.id === id ? { ...o, status } : o);
    this.save(orders);
  },
  seedIfEmpty(){
    if(this.all().length) return;
    const seed = [
      { id:"PO-20260031", client:"Dr. Reyes / St. Luke's Procurement", email:"procurement@stlukes-sample.ph", facility:"St. Luke's Medical Center", lines:[{...PRODUCTS[6], qty:20, lineTotal: PRODUCTS[6].price*20},{...PRODUCTS[10], qty:100, lineTotal: PRODUCTS[10].price*100}], total: PRODUCTS[6].price*20 + PRODUCTS[10].price*100, status:"Fulfilled", date: new Date(Date.now()-86400000*2).toISOString() },
      { id:"PO-20260032", client:"J. Santos", email:"j.santos@carmenlab-sample.ph", facility:"Carmen Diagnostic Laboratory", lines:[{...PRODUCTS[11], qty:5, lineTotal: PRODUCTS[11].price*5}], total: PRODUCTS[11].price*5, status:"Processing", date: new Date(Date.now()-86400000).toISOString() },
      { id:"PO-20260033", client:"M. Dela Cruz", email:"m.delacruz@marikinagen-sample.ph", facility:"Marikina General Hospital", lines:[{...PRODUCTS[0], qty:10, lineTotal: PRODUCTS[0].price*10},{...PRODUCTS[7], qty:15, lineTotal: PRODUCTS[7].price*15}], total: PRODUCTS[0].price*10 + PRODUCTS[7].price*15, status:"Pending", date: new Date().toISOString() },
    ];
    this.save(seed);
  }
};
