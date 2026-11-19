'use client';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {useRef, useState, type FormEvent} from 'react';
import {useCart} from './CartProvider';
import {formatPrice} from '@/lib/catalog';
import CartProductImage from './CartProductImage';
import {submissionKey} from '@/lib/inquiry-submission';

export default function CartPageClient(){
  const cart=useCart(); const router=useRouter();
  const [form,setForm]=useState({fullName:'',email:'',phone:'',company:'',notes:'',website:''});
  const [pending,setPending]=useState(false),[error,setError]=useState('');
  const sending=useRef(false);
  const input=(name:keyof typeof form,value:string)=>{setForm(old=>({...old,[name]:value}))};
  async function submit(e:FormEvent<HTMLFormElement>){
    e.preventDefault();if(sending.current||!cart.items.length)return;
    sending.current=true;
    setPending(true);setError('');
    try {
      const payload=JSON.stringify({...form,fullName:form.fullName.trim(),email:form.email.trim(),phone:form.phone.trim(),company:form.company.trim(),notes:form.notes.trim(),items:cart.items.map(x=>({id:x.product.id,quantity:x.quantity})).sort((a,b)=>a.id.localeCompare(b.id))});
      const key=await submissionKey(payload);
      const res=await fetch('/api/quotations',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':key},body:payload});
      const body=await res.json();
      if(!res.ok)throw new Error(body?.error||`Quotation request failed (${res.status}).`);
      if(typeof body.reference!=='string'||!/^RFQ-[A-F0-9]{12}$/.test(body.reference))throw new Error('The server returned an invalid reference. Please contact us before resubmitting.');
      cart.clear();router.push(`/quotation/success?reference=${encodeURIComponent(body.reference)}`);
    }catch(e){setError(e instanceof Error?e.message:'Unable to submit quotation.');}finally{sending.current=false;setPending(false)}
  }
  return <section className="section"><div className="container"><p className="eyebrow">YOUR SELECTION</p><h1>My Order</h1><p className="lead">Review the products you'd like a quotation for. Submitting this inquiry does not reserve stock or confirm a purchase.</p>
    {cart.items.length===0?<div className="empty-panel"><h3>Your order list is empty</h3><p>Browse available medical products and add them to your inquiry.</p><Link className="button button-primary" href="/products">Browse Products ↗</Link></div>:
      <div className="cart-page-grid"><div className="cart-lines">{cart.items.map(({product:product,quantity})=><div className="cart-line" key={product.id}><div style={{display:"flex",alignItems:"center",gap:14,minWidth:0,flex:1}}><CartProductImage src={product.imageUrl} name={product.name}/><div><h3>{product.name}</h3><p>{formatPrice(product.publicPrice)}</p></div></div><div className="qty-controls"><button type="button" onClick={()=>{cart.changeQty(product.id,quantity-1)}} aria-label={'Decrease '+product.name}>−</button><span>{quantity}</span><button type="button" onClick={()=>{cart.changeQty(product.id,quantity+1)}} aria-label={'Increase '+product.name}>+</button><button type="button" onClick={()=>{cart.remove(product.id)}} aria-label={'Remove '+product.name}>✕</button></div></div>)}</div>
      <form className="quote-panel quote-form" onSubmit={submit}><h2>Request a quotation</h2><p>Our team will review your inquiry and follow up with you. If submission is interrupted, retry with the same details in this tab to recover your reference.</p>
        <label>Full Name *<input required maxLength={160} autoComplete="name" value={form.fullName} onChange={e=>input('fullName',e.target.value)}/></label>
        <label>Email Address *<input required type="email" maxLength={254} autoComplete="email" value={form.email} onChange={e=>input('email',e.target.value)}/></label>
        <label>Phone Number *<input required type="tel" maxLength={40} autoComplete="tel" value={form.phone} onChange={e=>input('phone',e.target.value)}/></label>
        <label>Company / Organization *<input required maxLength={180} value={form.company} onChange={e=>input('company',e.target.value)}/></label>
        <label>Additional Message / Notes<textarea maxLength={2000} rows={4} value={form.notes} onChange={e=>input('notes',e.target.value)}/></label>
        <div className="quote-honeypot" aria-hidden="true"><label>Website<input tabIndex={-1} autoComplete="off" value={form.website} onChange={e=>input('website',e.target.value)}/></label></div>
        <p className="form-note">Availability and public prices are checked again when you submit. A quotation is not an invoice or stock reservation.</p>
        {error&&<p role="alert" className="form-error">{error}</p>}
        <button className="button button-primary" disabled={pending} type="submit">{pending?'Submitting…':'Submit Quotation Request'}</button>
      </form></div>}
  </div></section>;
}
