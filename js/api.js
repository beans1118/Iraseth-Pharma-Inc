/* =========================================================
   IRASETH PHARMA — API client
   Tries the real backend first. If it can't be reached (no server
   running), Api.mock flips on and every method below is served by
   MockApi (js/mock-backend.js) instead — same shape, same UI, just
   backed by this browser's localStorage. See mock-backend.js for
   details. Nothing needs to be configured for this to happen.
   ========================================================= */
const Api = {
  TOKEN_KEY: "iraseth_admin_token",
  mock: false,
  _mockReady: false,

  getToken(){ return sessionStorage.getItem(this.TOKEN_KEY); },
  setToken(token){ sessionStorage.setItem(this.TOKEN_KEY, token); },
  clearToken(){ sessionStorage.removeItem(this.TOKEN_KEY); },

  async _request(path, options = {}){
    try{
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3500);
      const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
      });
      clearTimeout(timeout);
      const data = await res.json().catch(() => null);
      if(!res.ok){
        return { ok:false, status:res.status, error: (data && data.error) || "Request failed.", data:null };
      }
      return { ok:true, status:res.status, data, error:null };
    }catch(err){
      return { ok:false, status:0, error:"unreachable", data:null };
    }
  },

  _authHeaders(){
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },

  /** Call once on page load. Detects whether the real backend is up;
   *  if not, switches to Demo Mode (MockApi) for the rest of the session. */
  async detect(){
    const r = await this._request("/health");
    this.mock = !r.ok;
    if(this.mock && typeof MockApi !== "undefined" && !this._mockReady){
      MockApi.init();
      this._mockReady = true;
    }
    return !this.mock; // true = real backend is live
  },

  async health(){
    const r = await this._request("/health");
    return r.ok;
  },

  // ---- Auth ----
  async login(email, password){
    if(this.mock) return MockApi.login(email, password);
    return this._request("/auth/login", { method:"POST", body: JSON.stringify({ email, password }) });
  },
  async logout(){
    if(this.mock) return MockApi.logout();
    return this._request("/auth/logout", { method:"POST", headers:this._authHeaders() });
  },
  async me(){
    if(this.mock) return MockApi.me();
    return this._request("/auth/me", { headers:this._authHeaders() });
  },

  // ---- Products ----
  async getProducts(){
    if(this.mock) return MockApi.getProducts();
    const r = await this._request("/products");
    return r.ok ? r.data : null;
  },
  async createProduct(payload){
    if(this.mock) return MockApi.createProduct(payload);
    return this._request("/products", { method:"POST", headers:this._authHeaders(), body:JSON.stringify(payload) });
  },
  async updateProduct(id, payload){
    if(this.mock) return MockApi.updateProduct(id, payload);
    return this._request(`/products/${encodeURIComponent(id)}`, { method:"PUT", headers:this._authHeaders(), body:JSON.stringify(payload) });
  },
  async deleteProduct(id){
    if(this.mock) return MockApi.deleteProduct(id);
    return this._request(`/products/${encodeURIComponent(id)}`, { method:"DELETE", headers:this._authHeaders() });
  },

  // ---- Orders ----
  async createOrder(payload){
    if(this.mock) return MockApi.createOrder(payload);
    return this._request("/orders", { method:"POST", body:JSON.stringify(payload) });
  },
  async getOrders(){
    if(this.mock) return MockApi.getOrders();
    return this._request("/orders", { headers:this._authHeaders() });
  },
  async getClientsSummary(){
    if(this.mock) return MockApi.getClientsSummary();
    return this._request("/orders/clients-summary", { headers:this._authHeaders() });
  },
  async updateOrder(id, payload){
    if(this.mock) return MockApi.updateOrder(id, payload);
    return this._request(`/orders/${encodeURIComponent(id)}`, { method:"PATCH", headers:this._authHeaders(), body:JSON.stringify(payload) });
  },

  // ---- Inventory (real-time stock) ----
  async getStock(){
    if(this.mock) return MockApi.getStock();
    return this._request("/inventory", { headers:this._authHeaders() });
  },
  async releaseStock(id, qty, note){
    if(this.mock) return MockApi.releaseStock(id, qty, note);
    return this._request(`/inventory/${encodeURIComponent(id)}/release`, { method:"POST", headers:this._authHeaders(), body:JSON.stringify({ qty, note }) });
  },
  async supplyStock(id, qty, note){
    if(this.mock) return MockApi.supplyStock(id, qty, note);
    return this._request(`/inventory/${encodeURIComponent(id)}/supply`, { method:"POST", headers:this._authHeaders(), body:JSON.stringify({ qty, note }) });
  },

  // ---- Logs (superadmin + admin) ----
  async getSessionLogs(params = {}){
    if(this.mock) return MockApi.getSessionLogs(params);
    const qs = new URLSearchParams(params).toString();
    return this._request(`/logs/sessions${qs ? "?" + qs : ""}`, { headers:this._authHeaders() });
  },
  async getInventoryLogs(params = {}){
    if(this.mock) return MockApi.getInventoryLogs(params);
    const qs = new URLSearchParams(params).toString();
    return this._request(`/logs/inventory${qs ? "?" + qs : ""}`, { headers:this._authHeaders() });
  },

  // ---- Users & roles (superadmin only) ----
  async getUsers(){
    if(this.mock) return MockApi.getUsers();
    return this._request("/users", { headers:this._authHeaders() });
  },
  async createUser(payload){
    if(this.mock) return MockApi.createUser(payload);
    return this._request("/users", { method:"POST", headers:this._authHeaders(), body:JSON.stringify(payload) });
  },
  async updateUser(email, payload){
    if(this.mock) return MockApi.updateUser(email, payload);
    return this._request(`/users/${encodeURIComponent(email)}`, { method:"PATCH", headers:this._authHeaders(), body:JSON.stringify(payload) });
  },
  async deleteUser(email){
    if(this.mock) return MockApi.deleteUser(email);
    return this._request(`/users/${encodeURIComponent(email)}`, { method:"DELETE", headers:this._authHeaders() });
  },

  // ---- Backup (superadmin only) ----
  async runBackup(){
    if(this.mock) return MockApi.runBackup();
    return this._request("/backup/run", { method:"POST", headers:this._authHeaders() });
  },
  async listBackups(){
    if(this.mock) return MockApi.listBackups();
    return this._request("/backup", { headers:this._authHeaders() });
  },
};
