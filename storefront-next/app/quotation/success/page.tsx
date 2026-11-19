import Link from 'next/link';
export const metadata={title:'Quotation Request Received'};
export default async function Success({searchParams}:{searchParams:Promise<{reference?:string}>}){
  const {reference}=await searchParams;
  const valid=typeof reference==='string'&&/^RFQ-[A-F0-9]{12}$/.test(reference);
  return <section className="section"><div className="container centered"><p className="eyebrow">QUOTATION REQUEST</p><h1>{valid?'Thank you for your inquiry!':'Quotation confirmation'}</h1>{valid?<><p>Your quotation request has been submitted for staff review.</p><div className="empty-panel"><h2>Reference: {reference}</h2><p>Keep this reference for future correspondence. This is not a confirmed order or stock reservation.</p></div></>:<p>No valid quotation reference was supplied. Please submit a request from My Order.</p>}{valid&&<Link href={'/track-order?reference='+encodeURIComponent(reference!)} className="button button-soft">Track My Order</Link>}<Link href="/products" className="button button-primary">Browse Products ↗</Link></div></section>;
}
