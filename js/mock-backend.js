/* =========================================================
   IRASETH PHARMA — Demo Mode (no backend required)
   Mirrors every Api.* method with the same {ok, status, data, error}
   shape, but reads/writes localStorage instead of calling a server.
   Api.js switches to this automatically when it can't reach the real
   backend at API_BASE — nothing to configure.

   This is clearly a DEMO: data lives only in this browser tab's
   storage, resets if you clear it, and isn't shared between devices.
   Swap in the real Flask + MongoDB backend (see backend/README.md)
   for actual production use — every screen in index.html/admin.html
   works identically against either one.
   ========================================================= */

const MockDB = {
  KEYS: {
    products: "iraseth_mock_products",
    orders: "iraseth_mock_orders",
    users: "iraseth_mock_users",
    sessions: "iraseth_mock_sessions",
    invLogs: "iraseth_mock_inventory_logs",
    backups: "iraseth_mock_backups",
    tokens: "iraseth_mock_tokens",
    seeded: "iraseth_mock_seeded_v1",
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

  // A modest, clearly-labelled sample catalog so Demo Mode actually
  // demonstrates release/supply/low-stock behaviour. The real backend's
  // seed (backend/products_seed.json) intentionally starts empty instead —
  // this sample data is for previewing the UI only.
  const sampleNames = [
    ["Disposable Syringe 3 mL 26G", "syringes-needles", "per unit", 8.50],
    ["Disposable Syringe 5 mL 23G", "syringes-needles", "per unit", 9.20],
    ["IV Cannula G22 with Safety Features", "iv-therapy", "per box", 320.00],
    ["IV Cannula G24 with Safety Features", "iv-therapy", "per box", 310.00],
    ["Surgical Face Mask (50s)", "ppe", "per box", 145.00],
    ["Nitrile Examination Gloves M (100s)", "ppe", "per box", 385.00],
    ["Nitrile Examination Gloves L (100s)", "ppe", "per box", 385.00],
    ["Alcohol Prep Pads (200s)", "consumables", "per box", 95.00],
    ["Adult Diaper M (10s)", "consumables", "per pack", 210.00],
    ["Adult Diaper L (10s)", "consumables", "per pack", 220.00],
    ["Blood Glucose Test Strips (50s)", "diagnostics", "per box", 890.00],
    ["Rapid Antigen Test Kit (25s)", "diagnostics", "per box", 1450.00],
    ["Digital Thermometer", "diagnostics", "per unit", 180.00],
    ["Pulse Oximeter", "diagnostics", "per unit", 650.00],
    ["Sphygmomanometer (Aneroid)", "diagnostics", "per unit", 980.00],
    ["Cotton Balls (500g)", "consumables", "per pack", 120.00],
    ["Gauze Pads 4x4 (100s)", "consumables", "per pack", 175.00],
    ["Elastic Bandage 4 inch", "consumables", "per unit", 45.00],
    ["Surgical Gown, Disposable", "ppe", "per unit", 65.00],
    ["Face Shield, Reusable", "ppe", "per unit", 55.00],
    ["Urine Specimen Cups (100s)", "diagnostics", "per pack", 210.00],
    ["Blood Collection Tubes EDTA (100s)", "diagnostics", "per box", 560.00],
    ["Micropore Tape 1 inch", "consumables", "per unit", 28.00],
    ["Suction Catheter 12Fr", "iv-therapy", "per unit", 18.00],
    ["Nasal Cannula, Adult", "iv-therapy", "per unit", 22.00],
    ["Foley Catheter 16Fr", "iv-therapy", "per unit", 95.00],
    ["IV Infusion Set", "iv-therapy", "per unit", 32.00],
    ["Disposable Bed Pad (10s)", "consumables", "per pack", 340.00],
    ["Hand Sanitizer 500mL", "ppe", "per unit", 110.00],
    ["Surgical Scrub Solution 500mL", "ppe", "per unit", 165.00],
  ];

  const products = sampleNames.map((row, i) => {
    const qty = [0, 3, 12, 40, 80][i % 5]; // mix of out/low/in-stock for a realistic demo
    return {
      id: `IRP-${1001 + i}`,
      name: row[0],
      description: `Sample demo listing for ${row[0]}.`,
      category: row[1],
      unit: row[2],
      quantity: qty,
      reorder_level: 5,
      price: row[3],
    };
  });
  MockDB.saveProducts(products);

  MockDB.saveUsers([
    { email:"superadmin@irasethpharma.com", password:"demo-superadmin", name:"Super Admin", role:"superadmin" },
    { email:"admin@irasethpharma.com", password:"demo-admin", name:"Admin", role:"admin" },
    { email:"subadmin@irasethpharma.com", password:"demo-subadmin", name:"Sub Admin", role:"subadmin" },
  ]);

  MockDB.saveOrders([]);
  MockDB.saveSessions([]);
  MockDB.saveInvLogs([]);
  MockDB.saveBackups([]);
  MockDB.saveTokens({});

  localStorage.setItem(MockDB.KEYS.seeded, "1");
}

function mockStatus(p){
  const qty = p.quantity || 0;
  if(qty <= 0) return "out-of-stock";
  if(qty <= (p.reorder_level || 0)) return "low-stock";
  return "in-stock";
}
function serializeProduct(p){ return { ...p, status: mockStatus(p) }; }

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
    const doc = { id:payload.id, name:payload.name, description:payload.description, category:payload.category, unit:payload.unit, quantity:Number(payload.quantity)||0, reorder_level:Number(payload.reorder_level)||5, price:Number(payload.price)||0 };
    products.push(doc);
    MockDB.saveProducts(products);
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
  getStock(){ return { ok:true, status:200, error:null, data:MockDB.products().map(serializeProduct) }; },

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

    // Demo mode has no server disk to write to — trigger a real browser
    // download instead, so "backup" still produces an actual file.
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
