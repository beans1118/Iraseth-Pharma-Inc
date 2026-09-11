// Local demo backend — mirrors the real Api.* methods but reads/writes localStorage.

const MockDB = {
  KEYS: {
    products: "iraseth_mock_products",
    orders: "iraseth_mock_orders",
    users: "iraseth_mock_users",
    sessions: "iraseth_mock_sessions",
    invLogs: "iraseth_mock_inventory_logs",
    backups: "iraseth_mock_backups",
    tokens: "iraseth_mock_tokens",
    seeded: "iraseth_mock_seeded_v2",
  },

  get(key, fallback){
    try{ const raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : fallback; }
    catch(e){ return fallback; }
  },
  set(key, value){ localStorage.setItem(key, JSON.stringify(value)); },

  products(){ return this.get(this.KEYS.products, []); },
  saveProducts(v){ this.set(this.KEYS.products, v); },
  orders(){ return this.get(this.KEYS.orders, []); },
  saveOrders(v){ this.set(this.KEYS.orders, v); },
  users(){ return this.get(this.KEYS.users, []); },
  saveUsers(v){ this.set(this.KEYS.users, v); },
  sessions(){ return this.get(this.KEYS.sessions, []); },
  saveSessions(v){ this.set(this.KEYS.sessions, v); },
  invLogs(){ return this.get(this.KEYS.invLogs, []); },
  saveInvLogs(v){ this.set(this.KEYS.invLogs, v); },
  backups(){ return this.get(this.KEYS.backups, []); },
  saveBackups(v){ this.set(this.KEYS.backups, v); },
  tokens(){ return this.get(this.KEYS.tokens, {}); },
  saveTokens(v){ this.set(this.KEYS.tokens, v); },
};

function mockId(prefix){ return prefix + "-" + Math.random().toString(36).slice(2, 9); }
function mockNow(){ return new Date().toISOString(); }

function seedMockData(){
  if(localStorage.getItem(MockDB.KEYS.seeded)) return;

  const products =
[
  {
    "id": "IRP-1001",
    "name": "Disposable Syringe 1 mL 26G",
    "description": "ALPHASHOT \u2014 Syringes, sold per unit.",
    "category": "syringes-needles",
    "unit": "per unit",
    "quantity": 60,
    "price": 1220,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1002",
    "name": "Disposable Syringe 3 mL 26G",
    "description": "ALPHASHOT \u2014 Syringes, sold per unit.",
    "category": "syringes-needles",
    "unit": "per unit",
    "quantity": 200,
    "price": 608,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1003",
    "name": "Disposable Syringe 5 mL 22G",
    "description": "ALPHASHOT \u2014 Syringes, sold per unit.",
    "category": "syringes-needles",
    "unit": "per unit",
    "quantity": 200,
    "price": 640,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1004",
    "name": "Disposable Syringe 10 mL 21G",
    "description": "ALPHASHOT \u2014 Syringes, sold per unit.",
    "category": "syringes-needles",
    "unit": "per unit",
    "quantity": 200,
    "price": 850,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1005",
    "name": "Adult Diaper S",
    "description": "ALPHACARE \u2014 Patient Care, sold per unit.",
    "category": "patient-care",
    "unit": "per unit",
    "quantity": 200,
    "price": 250,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1006",
    "name": "Adult Diaper M",
    "description": "ALPHACARE \u2014 Patient Care, sold per unit.",
    "category": "patient-care",
    "unit": "per unit",
    "quantity": 200,
    "price": 260,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1007",
    "name": "Adult Diaper L",
    "description": "ALPHACARE \u2014 Patient Care, sold per unit.",
    "category": "patient-care",
    "unit": "per unit",
    "quantity": 60,
    "price": 280,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1008",
    "name": "Adult Diaper XL",
    "description": "ALPHACARE \u2014 Patient Care, sold per unit.",
    "category": "patient-care",
    "unit": "per unit",
    "quantity": 200,
    "price": 330,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1009",
    "name": "Underpads",
    "description": "ALPHACARE \u2014 Patient Care, sold per unit.",
    "category": "patient-care",
    "unit": "per unit",
    "quantity": 200,
    "price": 280,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1010",
    "name": "Needle Retractable Safety Syringe 1mL with needle 27G x 3/8\"",
    "description": "IRASAFETY \u2014 Safety Syringes, sold per unit.",
    "category": "syringes-needles",
    "unit": "per unit",
    "quantity": 200,
    "price": 2800,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1011",
    "name": "Needle Retractable Safety Syringe 5mL with needle",
    "description": "IRASAFETY \u2014 Safety Syringes, sold per unit.",
    "category": "syringes-needles",
    "unit": "per unit",
    "quantity": 200,
    "price": 1400,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1012",
    "name": "Needle Retractable Safety Syringe 10mL with needle",
    "description": "IRASAFETY \u2014 Safety Syringes, sold per unit.",
    "category": "syringes-needles",
    "unit": "per unit",
    "quantity": 200,
    "price": 1465,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1013",
    "name": "Needle Retractable Safety Syringe 3mL with needle 27G x 3/8\"",
    "description": "IRASAFETY \u2014 Safety Syringes, sold per unit.",
    "category": "syringes-needles",
    "unit": "per unit",
    "quantity": 60,
    "price": 1410,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1014",
    "name": "IV Administration Set with Burette (Soluset) 150 mL",
    "description": "POLYVOL \u2014 IV Administration, sold per unit.",
    "category": "iv-therapy",
    "unit": "per unit",
    "quantity": 200,
    "price": 850,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1015",
    "name": "IV Administration Set with Burette (Soluset) 110 mL",
    "description": "POLYVOL \u2014 IV Administration, sold per unit.",
    "category": "iv-therapy",
    "unit": "per unit",
    "quantity": 200,
    "price": 670,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1016",
    "name": "IV Infusion Set (Macroset)",
    "description": "AUTOFUSION \u2014 IV Infusion, sold per box.",
    "category": "iv-therapy",
    "unit": "per box",
    "quantity": 200,
    "price": 1740,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1017",
    "name": "IV Infusion Set (Macroset)",
    "description": "AUTOFUSION \u2014 IV Infusion, sold per piece.",
    "category": "iv-therapy",
    "unit": "per piece",
    "quantity": 200,
    "price": 58,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1018",
    "name": "Blood Administration Set",
    "description": "HAEMOFUSOR \u2014 Blood Administration, sold per box.",
    "category": "iv-therapy",
    "unit": "per box",
    "quantity": 200,
    "price": 2450,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1019",
    "name": "Blood Administration Set",
    "description": "HAEMOFUSOR \u2014 Blood Administration, sold per piece.",
    "category": "iv-therapy",
    "unit": "per piece",
    "quantity": 60,
    "price": 98,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1020",
    "name": "IV Infusion Set (Microset)",
    "description": "MICROFUSION \u2014 IV Infusion, sold per box.",
    "category": "iv-therapy",
    "unit": "per box",
    "quantity": 200,
    "price": 700,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1021",
    "name": "IV Infusion Set (Microset)",
    "description": "MICROFUSION \u2014 IV Infusion, sold per piece.",
    "category": "iv-therapy",
    "unit": "per piece",
    "quantity": 200,
    "price": 28,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1022",
    "name": "IV Administration Set with Burette (Soluset) 150mL",
    "description": "POLYVOL \u2014 IV Administration, sold per unit.",
    "category": "iv-therapy",
    "unit": "per unit",
    "quantity": 200,
    "price": 85,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1023",
    "name": "IV Administration Set with Burette (Soluset) 110mL",
    "description": "POLYVOL \u2014 IV Administration, sold per unit.",
    "category": "iv-therapy",
    "unit": "per unit",
    "quantity": 200,
    "price": 68,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1024",
    "name": "IV Cannula with Safety Features G16",
    "description": "POLYSAFETY \u2014 Safety IV Cannula, sold per box.",
    "category": "iv-therapy",
    "unit": "per box",
    "quantity": 200,
    "price": 2662,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1025",
    "name": "IV Cannula with Safety Features G16",
    "description": "POLYSAFETY \u2014 Safety IV Cannula, sold per piece.",
    "category": "iv-therapy",
    "unit": "per piece",
    "quantity": 60,
    "price": 54,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1026",
    "name": "IV Cannula with Safety Features G18",
    "description": "POLYSAFETY \u2014 Safety IV Cannula, sold per box.",
    "category": "iv-therapy",
    "unit": "per box",
    "quantity": 200,
    "price": 2662,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1027",
    "name": "IV Cannula with Safety Features G18",
    "description": "POLYSAFETY \u2014 Safety IV Cannula, sold per piece.",
    "category": "iv-therapy",
    "unit": "per piece",
    "quantity": 200,
    "price": 54,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1028",
    "name": "IV Cannula with Safety Features G20",
    "description": "POLYSAFETY \u2014 Safety IV Cannula, sold per box.",
    "category": "iv-therapy",
    "unit": "per box",
    "quantity": 200,
    "price": 2662,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1029",
    "name": "IV Cannula with Safety Features G20",
    "description": "POLYSAFETY \u2014 Safety IV Cannula, sold per piece.",
    "category": "iv-therapy",
    "unit": "per piece",
    "quantity": 200,
    "price": 54,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1030",
    "name": "IV Cannula with Safety Features G22",
    "description": "POLYSAFETY \u2014 Safety IV Cannula, sold per box.",
    "category": "iv-therapy",
    "unit": "per box",
    "quantity": 200,
    "price": 2662,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1031",
    "name": "IV Cannula with Safety Features G22",
    "description": "POLYSAFETY \u2014 Safety IV Cannula, sold per piece.",
    "category": "iv-therapy",
    "unit": "per piece",
    "quantity": 60,
    "price": 54,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1032",
    "name": "IV Cannula with Safety Features G24",
    "description": "POLYSAFETY \u2014 Safety IV Cannula, sold per box.",
    "category": "iv-therapy",
    "unit": "per box",
    "quantity": 200,
    "price": 2783,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1033",
    "name": "IV Cannula with Safety Features G24",
    "description": "POLYSAFETY \u2014 Safety IV Cannula, sold per piece.",
    "category": "iv-therapy",
    "unit": "per piece",
    "quantity": 200,
    "price": 56,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1034",
    "name": "IV Cannula with Safety Features G26",
    "description": "POLYSAFETY \u2014 Safety IV Cannula, sold per box.",
    "category": "iv-therapy",
    "unit": "per box",
    "quantity": 200,
    "price": 3025,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1035",
    "name": "IV Cannula with Safety Features G26",
    "description": "POLYSAFETY \u2014 Safety IV Cannula, sold per piece.",
    "category": "iv-therapy",
    "unit": "per piece",
    "quantity": 200,
    "price": 61,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1036",
    "name": "IV Cannula G16",
    "description": "POLYFLON \u2014 IV Cannula, sold per unit.",
    "category": "iv-therapy",
    "unit": "per unit",
    "quantity": 200,
    "price": 1330,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1037",
    "name": "IV Cannula G18",
    "description": "POLYFLON \u2014 IV Cannula, sold per unit.",
    "category": "iv-therapy",
    "unit": "per unit",
    "quantity": 60,
    "price": 1180,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1038",
    "name": "IV Cannula G20",
    "description": "POLYFLON \u2014 IV Cannula, sold per unit.",
    "category": "iv-therapy",
    "unit": "per unit",
    "quantity": 200,
    "price": 1180,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1039",
    "name": "IV Cannula G22",
    "description": "POLYFLON \u2014 IV Cannula, sold per unit.",
    "category": "iv-therapy",
    "unit": "per unit",
    "quantity": 200,
    "price": 1180,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1040",
    "name": "IV Cannula G24",
    "description": "POLYFLON \u2014 IV Cannula, sold per unit.",
    "category": "iv-therapy",
    "unit": "per unit",
    "quantity": 200,
    "price": 1420,
    "baseline_qty": 200
  },
  {
    "id": "IRP-1041",
    "name": "IV Cannula G26",
    "description": "POLYFLON \u2014 IV Cannula, sold per unit.",
    "category": "iv-therapy",
    "unit": "per unit",
    "quantity": 200,
    "price": 1635,
    "baseline_qty": 200
  }
];
  MockDB.saveProducts(products);

  MockDB.saveUsers([
    { email:"superadmin@irasethpharma.com", password:"demo-superadmin", name:"Super Admin", role:"superadmin" },
    { email:"admin@irasethpharma.com", password:"demo-admin", name:"Admin", role:"admin" },
    { email:"subadmin@irasethpharma.com", password:"demo-subadmin", name:"Sub Admin", role:"subadmin" },
  ]);

  const OPENING_STOCK_DATE = "2026-09-01T08:00:00.000Z";
  const openingLogs = products
    .map(p => ({
      product_id: p.id,
      product_name: p.name,
      action: "opening",
      qty: 200,
      before: 0,
      after: 200,
      note: "Opening stock",
      actor_email: "system@irasethpharma.com",
      actor_name: "System (seed)",
      role: "superadmin",
      at: OPENING_STOCK_DATE,
    }));

  const DEMO_RELEASE_DATE = "2026-09-05T14:30:00.000Z";
  const demoReleaseLogs = products
    .filter(p => p.quantity === 60)
    .map(p => ({
      product_id: p.id,
      product_name: p.name,
      action: "release",
      qty: 140,
      before: 200,
      after: 60,
      note: "PO: PO-2026-0118 — Ordered by: Metro Manila Diagnostic Center",
      actor_email: "subadmin@irasethpharma.com",
      actor_name: "Sub Admin",
      role: "subadmin",
      at: DEMO_RELEASE_DATE,
    }));

  MockDB.saveOrders([]);
  MockDB.saveSessions([]);
  MockDB.saveInvLogs(openingLogs.concat(demoReleaseLogs));
  MockDB.saveBackups([]);
  MockDB.saveTokens({});

  localStorage.setItem(MockDB.KEYS.seeded, "1");
}

function mockStatus(p){
  const qty = p.quantity || 0;
  if(qty <= 0) return "out-of-stock";
  const baseline = p.baseline_qty || 0;
  if(baseline > 0 && qty * 10 <= baseline * 3) return "low-stock";
  return "in-stock";
}
function serializeProduct(p){ return { ...p, status: mockStatus(p) }; }

function currentMonthKey(){
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function ensureMonthlyOpenings(){
  const monthKey = currentMonthKey();
  const invLogs = MockDB.invLogs();
  if(invLogs.some(l => l.action === "monthly_opening" && l.month === monthKey)) return; // already snapshotted this month

  const products = MockDB.products();
  const now = mockNow();
  const newLogs = products.map(p => ({
    product_id: p.id, product_name: p.name, action:"monthly_opening",
    qty: p.quantity, before: p.quantity, after: p.quantity,
    note: `Beginning stock for ${monthKey}`, month: monthKey,
    actor_email:"system@irasethpharma.com", actor_name:"System (monthly snapshot)", role:"superadmin",
    at: now,
  }));
  MockDB.saveInvLogs(invLogs.concat(newLogs));
}

function currentMockUser(){
  const token = Api.getToken();
  if(!token) return null;
  const tokens = MockDB.tokens();
  return tokens[token] || null;
}

const MockApi = {
  init(){ seedMockData(); },

  // ---- Auth ----
  login(email, password){
    email = (email || "").trim().toLowerCase();
    const user = MockDB.users().find(u => u.email === email);
    if(!user || user.password !== password){
      return { ok:false, status:401, error:"Incorrect email or password.", data:null };
    }
    const token = mockId("tok");
    const jti = mockId("jti");
    const tokens = MockDB.tokens();
    tokens[token] = { email:user.email, name:user.name, role:user.role, jti };
    MockDB.saveTokens(tokens);

    const sessions = MockDB.sessions();
    sessions.unshift({
      jti, user_email:user.email, user_name:user.name, role:user.role,
      login_at: mockNow(), logout_at:null, duration_seconds:null,
    });
    MockDB.saveSessions(sessions);

    return { ok:true, status:200, error:null, data:{ token, user:{ email:user.email, name:user.name, role:user.role } } };
  },

  logout(){
    const u = currentMockUser();
    if(u){
      const sessions = MockDB.sessions();
      const row = sessions.find(s => s.jti === u.jti && !s.logout_at);
      if(row){
        row.logout_at = mockNow();
        row.duration_seconds = Math.max(1, Math.round((new Date(row.logout_at) - new Date(row.login_at)) / 1000));
        MockDB.saveSessions(sessions);
      }
    }
    return { ok:true, status:200, error:null, data:{ ok:true } };
  },

  me(){
    const u = currentMockUser();
    if(!u) return { ok:false, status:401, error:"Not signed in.", data:null };
    return { ok:true, status:200, error:null, data:{ email:u.email, name:u.name, role:u.role } };
  },

  // ---- Products ----
  getProducts(){ return MockDB.products().map(serializeProduct); },

  createProduct(payload){
    const u = currentMockUser();
    if(!u || u.role !== "superadmin") return { ok:false, status:403, error:"Only Superadmin can add products.", data:null };
    const products = MockDB.products();
    if(products.find(p => p.id === payload.id)) return { ok:false, status:409, error:`Product ${payload.id} already exists.`, data:null };
    const doc = { id:payload.id, name:payload.name, description:payload.description, category:payload.category, unit:payload.unit, quantity:Number(payload.quantity)||0, price:Number(payload.price)||0 };
    doc.baseline_qty = doc.quantity; // the starting stock is also the first "full" baseline for the 30% low-stock check
    products.push(doc);
    MockDB.saveProducts(products);

    if(doc.quantity > 0){
      const invLogs = MockDB.invLogs();
      invLogs.push({
        product_id:doc.id, product_name:doc.name, action:"opening", qty:doc.quantity,
        before:0, after:doc.quantity, note:"Opening stock",
        actor_email:u.email, actor_name:u.name, role:u.role, at:mockNow(),
      });
      MockDB.saveInvLogs(invLogs);
    }

    return { ok:true, status:201, error:null, data:serializeProduct(doc) };
  },

  updateProduct(id, payload){
    const u = currentMockUser();
    if(!u || u.role !== "superadmin") return { ok:false, status:403, error:"Only Superadmin can edit products.", data:null };
    const products = MockDB.products();
    const p = products.find(p => p.id === id);
    if(!p) return { ok:false, status:404, error:"Product not found.", data:null };
    Object.assign(p, payload, { quantity: p.quantity }); // never edit quantity here
    MockDB.saveProducts(products);
    return { ok:true, status:200, error:null, data:serializeProduct(p) };
  },

  deleteProduct(id){
    const u = currentMockUser();
    if(!u || u.role !== "superadmin") return { ok:false, status:403, error:"Only Superadmin can delete products.", data:null };
    const products = MockDB.products().filter(p => p.id !== id);
    MockDB.saveProducts(products);
    return { ok:true, status:200, error:null, data:{ deleted:id } };
  },

  // ---- Orders ----
  createOrder(payload){
    const products = MockDB.products();
    const lines = [];
    let total = 0;
    for(const raw of payload.lines){
      const product = products.find(p => p.id === raw.id);
      if(!product) return { ok:false, status:400, error:`Unknown product id: ${raw.id}`, data:null };
      const qty = Math.max(1, parseInt(raw.qty) || 1);
      const lineTotal = Math.round(product.price * qty * 100) / 100;
      total += lineTotal;
      lines.push({ id:product.id, name:product.name, unit:product.unit, price:product.price, qty, lineTotal });
    }
    const orders = MockDB.orders();
    const order = {
      id: `PO-${new Date().getFullYear()}${String(orders.length + 1).padStart(4, "0")}`,
      client: payload.client, email: payload.email, facility: payload.facility,
      lines, total: Math.round(total * 100) / 100, status:"Pending", notes:[], date: mockNow(),
    };
    orders.unshift(order);
    MockDB.saveOrders(orders);
    return { ok:true, status:201, error:null, data:order };
  },

  getOrders(){ return { ok:true, status:200, error:null, data:MockDB.orders() }; },

  getClientsSummary(){
    const orders = MockDB.orders();
    const byFacility = {};
    for(const o of orders){
      if(!byFacility[o.facility]) byFacility[o.facility] = { facility:o.facility, client:o.client, orders:0, spend:0, last:o.date };
      byFacility[o.facility].orders += 1;
      byFacility[o.facility].spend += o.total;
      if(o.date > byFacility[o.facility].last) byFacility[o.facility].last = o.date;
    }
    const rows = Object.values(byFacility).sort((a,b) => b.spend - a.spend);
    return { ok:true, status:200, error:null, data:rows };
  },

  updateOrder(id, payload){
    const u = currentMockUser();
    if(!u || (u.role !== "superadmin" && u.role !== "subadmin")) return { ok:false, status:403, error:"You do not have permission to do that.", data:null };
    const orders = MockDB.orders();
    const order = orders.find(o => o.id === id);
    if(!order) return { ok:false, status:404, error:"Order not found.", data:null };

    const becomingFulfilled = payload.status === "Fulfilled" && order.status !== "Fulfilled";
    if(payload.status) order.status = payload.status;
    if(payload.note) order.notes.push({ text:payload.note, author:u.email, at:mockNow() });

    if(becomingFulfilled){
      const products = MockDB.products();
      const invLogs = MockDB.invLogs();
      for(const line of order.lines){
        const product = products.find(p => p.id === line.id);
        if(!product) continue;
        const before = product.quantity;
        product.quantity = Math.max(0, before - line.qty);
        invLogs.unshift({
          product_id:product.id, product_name:product.name, action:"release", qty:line.qty,
          before, after:product.quantity, note:`Order ${order.id} fulfilled`,
          actor_email:u.email, actor_name:u.name, role:u.role, at:mockNow(),
        });
      }
      MockDB.saveProducts(products);
      MockDB.saveInvLogs(invLogs);
    }

    MockDB.saveOrders(orders);
    return { ok:true, status:200, error:null, data:order };
  },

  // ---- Inventory ----
  getStock(){ ensureMonthlyOpenings(); return { ok:true, status:200, error:null, data:MockDB.products().map(serializeProduct) }; },

  _stockAction(id, qty, note, action){
    const u = currentMockUser();
    if(!u || (u.role !== "superadmin" && u.role !== "subadmin")) return { ok:false, status:403, error:"You do not have permission to do that.", data:null };
    const products = MockDB.products();
    const product = products.find(p => p.id === id);
    if(!product) return { ok:false, status:404, error:"Product not found.", data:null };

    const delta = action === "release" ? -qty : qty;
    const before = product.quantity;
    const after = before + delta;
    if(after < 0) return { ok:false, status:400, error:`Cannot release ${qty} — only ${before} in stock.`, data:null };
    product.quantity = after;
    if(action === "supply") product.baseline_qty = after;
    MockDB.saveProducts(products);

    const invLogs = MockDB.invLogs();
    const log = { product_id:id, product_name:product.name, action, qty, before, after, note:note||"", actor_email:u.email, actor_name:u.name, role:u.role, at:mockNow() };
    invLogs.unshift(log);
    MockDB.saveInvLogs(invLogs);

    return { ok:true, status:200, error:null, data:{ product:serializeProduct(product), log } };
  },
  releaseStock(id, qty, note){ return this._stockAction(id, qty, note, "release"); },
  supplyStock(id, qty, note){ return this._stockAction(id, qty, note, "supply"); },

  // ---- Logs ----
  getSessionLogs(params = {}){
    let rows = MockDB.sessions();
    if(params.role && params.role !== "all") rows = rows.filter(s => s.role === params.role);
    if(params.user) rows = rows.filter(s => s.user_email.toLowerCase().includes(params.user.toLowerCase()));
    return { ok:true, status:200, error:null, data:rows };
  },
  getInventoryLogs(params = {}){
    let rows = MockDB.invLogs();
    if(params.action && params.action !== "all") rows = rows.filter(l => l.action === params.action);
    rows = rows.slice().sort((a,b) => new Date(b.at) - new Date(a.at));
    return { ok:true, status:200, error:null, data:rows };
  },

  // ---- Users ----
  getUsers(){
    return { ok:true, status:200, error:null, data:MockDB.users().map(u => ({ email:u.email, name:u.name, role:u.role })) };
  },
  createUser(payload){
    const users = MockDB.users();
    if(users.find(u => u.email === payload.email)) return { ok:false, status:409, error:"A user with that email already exists.", data:null };
    users.push({ email:payload.email, password:payload.password, name:payload.name, role:payload.role });
    MockDB.saveUsers(users);
    return { ok:true, status:201, error:null, data:{ email:payload.email, name:payload.name, role:payload.role } };
  },
  updateUser(email, payload){
    const users = MockDB.users();
    const user = users.find(u => u.email === email);
    if(!user) return { ok:false, status:404, error:"User not found.", data:null };
    if(payload.role) user.role = payload.role;
    if(payload.name) user.name = payload.name;
    if(payload.password) user.password = payload.password;
    MockDB.saveUsers(users);
    return { ok:true, status:200, error:null, data:{ email:user.email, name:user.name, role:user.role } };
  },
  deleteUser(email){
    const users = MockDB.users().filter(u => u.email !== email);
    MockDB.saveUsers(users);
    return { ok:true, status:200, error:null, data:{ deleted:email } };
  },

  // ---- Backup ----
  runBackup(){
    const snapshot = {
      created_at: mockNow(),
      products: MockDB.products(),
      orders: MockDB.orders(),
      users: MockDB.users().map(u => ({ email:u.email, name:u.name, role:u.role })),
      sessions: MockDB.sessions(),
      inventory_logs: MockDB.invLogs(),
    };
    const filename = `backup-${mockNow().replace(/[:.]/g, "-")}.json`;
    const record = { filename, created_at:snapshot.created_at, counts:{ products:snapshot.products.length, orders:snapshot.orders.length, users:snapshot.users.length, sessions:snapshot.sessions.length, inventory_logs:snapshot.inventory_logs.length } };

    const backups = MockDB.backups();
    backups.unshift(record);
    MockDB.saveBackups(backups);

    try{
      const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type:"application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }catch(e){ /* download not critical to the demo */ }

    return { ok:true, status:201, error:null, data:record };
  },
  listBackups(){ return { ok:true, status:200, error:null, data:MockDB.backups() }; },
};
