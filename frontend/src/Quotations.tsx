import {useEffect,useState} from 'react';
import {endpoints,type QuotationInquiry,type Role} from './api';
import InquiryDecision from './InquiryDecision';

type Props={role:Role;onChanged:()=>Promise<void>;onViewOrder:(id:string)=>void};
export default function Quotations({role,onChanged,onViewOrder}:Props){
 const [items,setItems]=useState<QuotationInquiry[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[saving,setSaving]=useState('');
 const [decision,setDecision]=useState<{inquiry:QuotationInquiry;action:'accept'|'decline'}|null>(null);
 async function load(){setLoading(true);try{setItems(await endpoints.quotations());setError('')}catch(e){setError(e instanceof Error?e.message:'Unable to load inquiries.')}finally{setLoading(false)}}
 useEffect(()=>{void load()},[]);
 async function change(q:QuotationInquiry,action:'review'|'accept'|'decline'){
  if(saving)return;
  setSaving(q.id);setError('');
  try{
   if(action==='accept')await endpoints.acceptInquiry(q.id);
   else if(action==='decline')await endpoints.declineInquiry(q.id);
   else await endpoints.quotationStatus(q.id,'In Review');
   if(action!=='review')setDecision(null);
   await load();await onChanged();
  }catch(e){if(action!=='review')throw e;setError(e instanceof Error?e.message:'Unable to update inquiry.')}finally{setSaving('')}
 }
 return <section className="panel"><div className="panel-head"><div><h2>Order Inquiries</h2><p>Accept an inquiry to create one pending order. Stock is reserved only when the order is approved in Orders.</p><p>Order prices use the current internal catalog; public inquiry prices remain recorded below.</p></div><button className="btn outline" disabled={!!saving} onClick={()=>void load()}>Refresh</button></div>
 {error&&<p role="alert" className="form-error">{error}</p>}
 {loading?<p>Loading inquiries...</p>:items.length===0?<p>No order inquiries received yet.</p>:<div style={{display:'grid',gap:16,padding:16}}>{items.map(q=>{
 const terminal=q.status==='Accepted'||q.status==='Declined';
 return <article className="panel" style={{padding:20}} key={q.id}>
 <div style={{display:'flex',flexWrap:'wrap',gap:12,justifyContent:'space-between'}}><div><strong>{q.id}</strong><p>{new Date(q.created_at).toLocaleString()}</p></div><strong>{q.status}</strong></div>
 <p><strong>{q.fullName}</strong> &mdash; {q.company}</p><p>Email: <a href={'mailto:'+q.email}>{q.email}</a> &middot; Phone: {q.phone}</p>{q.notes&&<p>Notes: {q.notes}</p>}
 <ul>{q.items.map(l=><li key={l.id}>{l.name} &times; {l.quantity} &mdash; {l.public_price_at_inquiry===null?'Price Upon Request':new Intl.NumberFormat('en-PH',{style:'currency',currency:'PHP'}).format(l.public_price_at_inquiry)+' each at time of inquiry'}</li>)}</ul>
 <div className="row-actions">
 {role!=='admin'&&!terminal&&<>
 {q.status!=='In Review'&&<button className="btn outline" disabled={!!saving} onClick={()=>void change(q,'review')}>Mark In Review</button>}
 <button className="btn primary" disabled={!!saving} onClick={()=>setDecision({inquiry:q,action:'accept'})}>Accept Inquiry</button>
 <button className="btn outline" disabled={!!saving} onClick={()=>setDecision({inquiry:q,action:'decline'})}>Decline</button>
 </>}
 {q.order_id&&<button className="btn outline" disabled={!!saving} onClick={()=>onViewOrder(q.order_id!)}>View Order {q.order_id}</button>}
 </div>
 </article>})}</div>}{decision&&<InquiryDecision inquiry={decision.inquiry} action={decision.action} onCancel={()=>setDecision(null)} onConfirm={()=>change(decision.inquiry,decision.action)}/>}</section>
}
