import {unstable_rethrow} from 'next/navigation';

export type PublicProduct = {
  id: string;
  slug: string;
  name: string;
  category: string;
  brand?: string;
  manufacturer?: string;
  model?: string;
  description?: string;
  imageUrl?: string;
  imageUrls?: string[];
  keyFeatures?: string[];
  specifications?: Array<{label: string; value: string}>;
  publicPrice: number | null;
  inStock: boolean;
  publishedAt?: string;
};
export type CatalogResult = { products: PublicProduct[]; connected: boolean; message?: string };
export async function getPublicProduct(slug: string): Promise<{product: PublicProduct|null; connected: boolean}> {
  const base = process.env.CATALOG_API_BASE_URL || process.env.NEXT_PUBLIC_CATALOG_API_BASE;
  if (!base) return {product:null, connected:false};
  try {
    const response = await fetch(`${base.replace(/\/$/, '')}/api/public/products/${encodeURIComponent(slug)}`, {cache:'no-store'});
    if (response.status === 404) return {product:null, connected:true};
    if (!response.ok) throw new Error(`Catalog API returned ${response.status}`);
    const product: PublicProduct = await response.json();
    if (typeof product.id !== 'string' || product.slug !== slug || typeof product.name !== 'string' || typeof product.inStock !== 'boolean') throw new Error('Invalid product response');
    return {product, connected:true};
  } catch(error) {
    unstable_rethrow(error);
    console.error('[public catalog] Unable to load product:', error);
    return {product:null, connected:false};
  }
}
/**
 * Phase 1: explicitly safe adapter. No employee JWT or /api/products call.
 * Phase 2 provides the public Flask endpoint with a stable contract.
 * If unavailable, show a visible error, never use mock products or inventory.
 */
export async function getPublicProducts(): Promise<CatalogResult> {
  const base = process.env.CATALOG_API_BASE_URL || process.env.NEXT_PUBLIC_CATALOG_API_BASE;
  if (!base) return {products: [],connected:false,message:'The live product catalog has not yet been connected.'};
  try {
    const products: PublicProduct[] = [];
    const seen = new Set<string>();
    for (let page = 1; page <= 10000; page++) {
    const response = await fetch(`${base.replace(/\/$/, '')}/api/public/products?page=${page}&limit=100`, {cache:'no-store'});
    if (!response.ok) throw new Error(`Catalog API returned ${response.status}`);
    const body: unknown = await response.json();
    if (!body || typeof body !== 'object') throw new Error('Invalid catalog response');
    const record = body as Record<string, unknown>;
    const raw = Array.isArray(record.products) ? record.products : Array.isArray(body) ? body : null;
    if (!raw) throw new Error('Unrecognized catalog response');
    const rows = raw.filter((p): p is PublicProduct => {
      if (!p || typeof p !== 'object') return false;
      const v = p as Partial<PublicProduct>;
      return typeof v.id === 'string' && typeof v.slug === 'string' && typeof v.name === 'string' && typeof v.category === 'string' && typeof v.inStock === 'boolean' && (v.publicPrice === null || (typeof v.publicPrice === 'number' && Number.isFinite(v.publicPrice) && v.publicPrice >= 0));
    });
    if (rows.length !== raw.length) throw new Error('Invalid catalog product');
    for (const product of rows) if (!seen.has(product.id)) {products.push(product); seen.add(product.id);}
    if (record.hasMore !== true) return {products,connected:true};
    if (!rows.length) throw new Error('Catalog pagination made no progress');
    }
    throw new Error('Catalog pagination limit exceeded');
  } catch (error) {
    // Let Next.js handle rendering control flow before reporting API failures.
    unstable_rethrow(error);
    // Server-side diagnostics: never expose upstream error details to visitors.
    console.error('[public catalog] Unable to load products:', error);
    return {products: [], connected:false, message:'The product catalog is temporarily unavailable. Please contact our team for product inquiries.'};
  }
}
export function formatPrice(value: number | null) {
  return value === null ? 'Price Upon Request' : new Intl.NumberFormat('en-PH',{style:'currency',currency:'PHP'}).format(value);
}
