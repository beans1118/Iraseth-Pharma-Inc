/* =========================================================
   IRASETH PHARMA — API client
   Every method returns { ok, status, data, error }. There is no
   offline/demo fallback — if the backend is unreachable, ok is
   false and status is 0, and callers should show that clearly
   instead of silently substituting fake data.
   ========================================================= */
const Api = {
  TOKEN_KEY: "iraseth_admin_token",

  getToken(){ return sessionStorage.getItem(this.TOKEN_KEY); },
  setToken(token){ sessionStorage.setItem(this.TOKEN_KEY, token); },
  clearToken(){ sessionStorage.removeItem(this.TOKEN_KEY); },

  async _request(path, options = {}){
    try{
      const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
      });
      const data = await res.json().catch(() => null);
      if(!res.ok){
        return { ok:false, status:res.status, error: (data && data.error) || "Request failed.", data:null };
      }
      return { ok:true, status:res.status, data, error:null };
    }catch(err){
      console.warn("API unreachable:", path, err.message);
      return { ok:false, status:0, error:"unreachable", data:null };
    }
  },

  _authHeaders(){
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },

  async health(){
    const r = await this._request("/health");
    return r.ok;
  },

  // ---- Auth ----
  async login(email, password){
    return this._request("/auth/login", { method:"POST", body: JSON.stringify({ email, password }) });
  },
  async logout(){
    return this._request("/auth/logout", { method:"POST", headers:this._authHeaders() });
  },
  async me(){
    return this._request("/auth/me", { headers:this._authHeaders() });
  },

  // ---- Products ----
  async getProducts(){
    const r = await this._request("/products");
    return r.ok ? r.data : null;
  },
  async createProduct(payload){
    return this._request("/products", { method:"POST", headers:this._authHeaders(), body:JSON.stringify(payload) });
  },
  async updateProduct(id, payload){
    return this._request(`/products/${encodeURIComponent(id)}`, { method:"PUT", headers:this._authHeaders(), body:JSON.stringify(payload) });
  },
  async deleteProduct(id){
    return this._request(`/products/${encodeURIComponent(id)}`, { method:"DELETE", headers:this._authHeaders() });
  },

  // ---- Orders ----
  async createOrder(payload){
    return this._request("/orders", { method:"POST", body:JSON.stringify(payload) });
  },
  async getOrders(){
    const r = await this._request("/orders", { headers:this._authHeaders() });
    return r;
  },
  async getClientsSummary(){
    const r = await this._request("/orders/clients-summary", { headers:this._authHeaders() });
    return r;
  },
  async updateOrder(id, payload){
    return this._request(`/orders/${encodeURIComponent(id)}`, { method:"PATCH", headers:this._authHeaders(), body:JSON.stringify(payload) });
  },

  // ---- Inventory (real-time stock) ----
  async getStock(){
    return this._request("/inventory", { headers:this._authHeaders() });
  },
  async releaseStock(id, qty, note){
    return this._request(`/inventory/${encodeURIComponent(id)}/release`, { method:"POST", headers:this._authHeaders(), body:JSON.stringify({ qty, note }) });
  },
  async supplyStock(id, qty, note){
    return this._request(`/inventory/${encodeURIComponent(id)}/supply`, { method:"POST", headers:this._authHeaders(), body:JSON.stringify({ qty, note }) });
  },

  // ---- Logs (superadmin + admin) ----
  async getSessionLogs(params = {}){
    const qs = new URLSearchParams(params).toString();
    return this._request(`/logs/sessions${qs ? "?" + qs : ""}`, { headers:this._authHeaders() });
  },
  async getInventoryLogs(params = {}){
    const qs = new URLSearchParams(params).toString();
    return this._request(`/logs/inventory${qs ? "?" + qs : ""}`, { headers:this._authHeaders() });
  },

  // ---- Users & roles (superadmin only) ----
  async getUsers(){
    return this._request("/users", { headers:this._authHeaders() });
  },
  async createUser(payload){
    return this._request("/users", { method:"POST", headers:this._authHeaders(), body:JSON.stringify(payload) });
  },
  async updateUser(email, payload){
    return this._request(`/users/${encodeURIComponent(email)}`, { method:"PATCH", headers:this._authHeaders(), body:JSON.stringify(payload) });
  },
  async deleteUser(email){
    return this._request(`/users/${encodeURIComponent(email)}`, { method:"DELETE", headers:this._authHeaders() });
  },

  // ---- Backup (superadmin only) ----
  async runBackup(){
    return this._request("/backup/run", { method:"POST", headers:this._authHeaders() });
  },
  async listBackups(){
    return this._request("/backup", { headers:this._authHeaders() });
  },
};
