import {notFound} from 'next/navigation';
import {getPublicProduct} from '@/lib/catalog';
import ProductModal from '@/components/ProductModal';
export const dynamic = 'force-dynamic';
export default async function ProductOverlay({params}: {params:Promise<{slug:string}>}) {
  const {slug}=await params;
  const result=await getPublicProduct(slug);
  if (!result.connected) throw new Error('Product catalog is temporarily unavailable.');
  const product=result.product;
  if(!product)notFound();
  return <ProductModal product={product}/>;
}
