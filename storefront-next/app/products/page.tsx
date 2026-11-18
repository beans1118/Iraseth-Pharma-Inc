import PageIntro from '@/components/PageIntro';
import CatalogClient from '@/components/CatalogClient';
import {getPublicProducts} from '@/lib/catalog';
export const metadata={title:'Medical Products'};
// Public prices and availability are read fresh for each request.
export const dynamic = 'force-dynamic';
export default async function Products(){const result=await getPublicProducts();return <><PageIntro eyebrow="PRODUCT CATALOG" title="Explore products for modern healthcare." lead="Browse medical, diagnostic and laboratory supplies for your organization."/><CatalogClient initial={result}/></>}
