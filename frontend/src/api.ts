export type Role = 'superadmin' | 'admin' | 'subadmin';
export type User = { email: string; name: string; role: Role };
export type Product = {id: string; name: string; category: string; description: string; unit: string; quantity: number; price: number; manufacturer?: string; image?: string; status?: string};
export type Batch = {id: string; product_id: string; lot: string; expires_on: string; on_hand: number; reserved: number; condition: string; unverified?: boolean};
export type Order = {id: string; client: string; email: string; facility: string; status: string; total: number; date: string; lines: Array<{id: string; name: string; qty: number; unit: string; price: number}>};
export type InvoiceLine = {id:string;name:string;unit:string;qty:number;price:string;subtotal:string};
export type Invoice = {id:string;order_id:string|null;client:string;email:string;facility:string;lines:InvoiceLine[];total:string;currency:string;status:'Draft'|'Issued'|'Voided';created_at:string;actor_email:string};
export type InvoiceTransaction = {id:string;invoice_id:string;event:string;actor_email:string;at:string};
export type AnalyticsOverview = {period_days:number;as_of_utc:string;products:number;batch_count:number;on_hand:number;reserved:number;available_eligible:number;expiring_batches_90d:number;orders_by_status:Record<string,number>;invoices_by_status:Record<string,number>;movement_trends:Array<{day:string;action:string;events:number;units:number}>;scope_note:string};
export type AlertProduct = {product_id:string;product_name:string;category:string;unit:string;available:number;threshold:number;custom_threshold?:boolean};
export type AlertBatch = {batch_id:string;product_id:string;lot:string;expires_on:string;on_hand:number;reserved:number;condition:string};
export type InventoryAlerts = {as_of_utc:string;expiry_window_days:number;global_preview_threshold:number;note:string;all_products:AlertProduct[];low_stock:AlertProduct[];stockouts:AlertProduct[];expiring_batches:AlertBatch[];expired_batches:AlertBatch[];restricted_batches:AlertBatch[]};
export type Adjustment = {id: string; batch_id: string; delta: number; reason: string; status?: string};
export type Stock = {product_id: string; on_hand: number; reserved: number; available: number};
export type Movement = {id?: string; product_id?: string; type?: string; action?: string; qty?: number; at?: string; actor_email?: string; lot?: string; batch_id?: string; reference?: string};

const TOKEN_KEY = 'iraseth.accessToken';
export const token = () => sessionStorage.getItem(TOKEN_KEY);
export const saveToken = (value: string) => sessionStorage.setItem(TOKEN_KEY, value);
export const clearToken = () => sessionStorage.removeItem(TOKEN_KEY);

export class ApiError extends Error {constructor(message: string, public status: number) {super(message); this.name = 'ApiError';}}

export async function api<T>(path: string, options: {method?: string; data?: unknown; key?: string; authenticated?: boolean} = {}): Promise<T> {
  const headers: Record<string, string> = {Accept: 'application/json'};
  if (options.data !== undefined) headers['Content-Type'] = 'application/json';
  if (options.authenticated !== false && token()) headers.Authorization = `Bearer ${token()}`;
  if (options.key) headers['Idempotency-Key'] = options.key;
  let response: Response;
  try {response = await fetch(path, {method: options.method || 'GET', headers, body: options.data === undefined ? undefined : JSON.stringify(options.data), cache: 'no-store'});}
  catch {throw new ApiError('Cannot connect to Flask. Check the backend server and Vite proxy.', 0);}
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError((body && typeof body.error === 'string' && body.error) || `Request failed (${response.status}).`, response.status);
  return body as T;
}

export const requestKey = () => (globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`);
export const endpoints = {
  login: (email: string, password: string) => api<{token: string; user: User}>('/api/auth/login', {method: 'POST', data: {email, password}, authenticated: false}),
  me: () => api<User>('/api/auth/me'),
  logout: () => api('/api/auth/logout', {method: 'POST'}),
  products: () => api<Product[]>('/api/products'),
  createProduct: (data: Omit<Product, 'status'>) => api<Product>('/api/products', {method: 'POST', data}),
  batches: () => api<{items: Batch[]; total: number}>('/api/v2/inventory/batches?limit=100'),
  summary: () => api<Stock[]>('/api/v2/inventory/summary'),
  movements: () => api<Movement[]>('/api/v2/inventory/movements?limit=100'),
  receive: (data: unknown) => api('/api/v2/inventory/batches/receive', {method: 'POST', data, key: requestKey()}),
  release: (data: unknown) => api('/api/v2/inventory/release', {method: 'POST', data, key: requestKey()}),
  orders: () => api<Order[]>('/api/orders'),
  createOrder: (data: unknown) => api<Order>('/api/orders', {method: 'POST', data, authenticated: false}),
  orderAction: (id: string, action: 'approve'|'fulfill'|'cancel') => api(`/api/v2/orders/${encodeURIComponent(id)}/${action}`, {method: 'POST', key: requestKey()}),
  requestAdjustment: (data: unknown) => api<Adjustment>('/api/v2/inventory/adjustments', {method: 'POST', data}),
  decideAdjustment: (id: string, approve: boolean) => api(`/api/v2/inventory/adjustments/${encodeURIComponent(id)}/decision`, {method: 'POST', data: {approve}, key: requestKey()}),
  users: () => api<User[]>('/api/users'),
  createUser: (data: unknown) => api<User>('/api/users', {method: 'POST', data}),
  inventoryAlerts: (days:30|60|90, threshold:number) => api<InventoryAlerts>(`/api/v2/alerts/inventory?days=${days}&threshold=${threshold}`),
  setInventoryThreshold: (id:string,threshold:number|null) => api<{product_id:string;threshold:number|null}>(`/api/v2/alerts/products/${encodeURIComponent(id)}/threshold`,{method:'PATCH',data:{threshold}}),
  analyticsOverview: (days:7|30|90) => api<AnalyticsOverview>(`/api/v2/analytics/overview?days=${days}`),
  invoices: () => api<Invoice[]>('/api/v2/invoices'),
  invoiceTransactions: () => api<InvoiceTransaction[]>('/api/v2/invoices/transactions'),
  createInvoice: (data:unknown, key:string) => api<Invoice>('/api/v2/invoices',{method:'POST',data,key}),
  invoiceAction: (id:string, action:'issue'|'void') => api<Invoice>(`/api/v2/invoices/${encodeURIComponent(id)}/${action}`,{method:'POST'}),
  health: () => api<{status: string}>('/api/ready', {authenticated: false}),
};
