import {notFound} from 'next/navigation';
import Link from 'next/link';
import ProductDetail from '@/components/ProductDetail';
import {getPublicProduct} from '@/lib/catalog';
// Public prices and availability are read fresh for each request.
export const dynamic = 'force-dynamic';
export default async function ProductPage({params}:{params:Promise<{slug:string}>}){const {slug}=await params;const result=await getPublicProduct(slug);if(!result.connected)return <section className="section"><div className="container centered"><p className="eyebrow">PRODUCT DETAILS</p><h1>The live catalog isn't connected yet.</h1><p>Product details will become available when the approved Flask public API is online.</p><Link href="/products" className="button button-primary">Back to Catalog ↗</Link></div></section>;const product=result.product;if(!product)notFound();return <ProductDetail product={product}/>}
