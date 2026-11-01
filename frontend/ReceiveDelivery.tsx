import {useState, type FormEvent} from 'react';
import {api, requestKey, type Product} from './api';
import './receive-delivery.css';

type Line = {product_id:string; lot:string; expires_on:string; qty:string; condition:'available'|'quarantine'};
const empty = ():Line => ({product_id:'',lot:'',expires_on:'',qty:'',condition:'available'});
export function ReceiveDelivery({products,onDone,onCancel}:{products:Product[];onDone:()=>Promise<void>;onCancel:()=>void}) {
  const [reference,setReference]=useState('');
  const [lines,setLines]=useState<Line[]>([empty()]);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [result,setResult]=useState<{reference:string;lines_received:number;units_received:number}|null>(null);
  const [submissionKey,setSubmissionKey]=useState(requestKey);
  const update=(i:number,field:keyof Line,value:string)=>setLines(previous=>previous.map((line,n)=>n===i?{...line,[field]:value}:line));
  const canSubmit=reference.trim() && lines.length>0 && lines.every(l=>l.product_id&&l.lot.trim()&&l.expires_on&&Number.isSafeInteger(Number(l.qty))&&Number(l.qty)>0);
  async function submit(event:FormEvent) {
    event.preventDefault();if(!canSubmit||busy)return;
    setBusy(true);setError('');setResult(null);
    try {
      const response=await api<{reference:string;lines_received:number;units_received:number}>('/api/v2/inventory/deliveries/receive',{
        method:'POST',key:submissionKey,
        data:{reference:reference.trim(),lines:lines.map(l=>({...l,lot:l.lot.trim(),qty:Number(l.qty)}))}
      });
      setResult(response);setLines([empty()]);setReference('');setSubmissionKey(requestKey());
      await onDone();
    } catch(e) {setError(e instanceof Error?e.message:'Unable to receive delivery.');}
    finally {setBusy(false);}
  }
  return <section className="delivery-page">
    <div className="delivery-header"><div><h2>Receive Delivery</h2><p>Receive multiple products and lots together. Every line is committed in one inventory transaction.</p></div><button className="btn outline" type="button" onClick={onCancel}>Back to batches</button></div>
    {result&&<div className="delivery-success" role="status">Received {result.lines_received} batch lines ({result.units_received} units) for {result.reference}. Inventory has been refreshed.</div>}
    {error&&<div className="delivery-error" role="alert">{error}</div>}
    <form onSubmit={submit}>
      <label className="field"><span>Delivery / invoice reference</span><input required maxLength={150} value={reference} onChange={e=>setReference(e.target.value)} placeholder="e.g. DR-2026-1001"/></label>
      <div className="delivery-lines">
        {lines.map((line,index)=><div key={index} className="delivery-line">
          <div className="delivery-line-title"><strong>Batch line {index+1}</strong><button type="button" className="btn outline" disabled={lines.length===1||busy} onClick={()=>setLines(ls=>ls.filter((_,i)=>i!==index))}>Remove</button></div>
          <div className="delivery-fields">
            <label className="field"><span>Product</span><select required value={line.product_id} onChange={e=>update(index,'product_id',e.target.value)}><option value="">Select product</option>{products.map(p=><option key={p.id} value={p.id}>{p.name} ({p.id})</option>)}</select></label>
            <label className="field"><span>Lot number</span><input required maxLength={100} value={line.lot} onChange={e=>update(index,'lot',e.target.value)} placeholder="Lot number"/></label>
            <label className="field"><span>Expiration date</span><input type="date" required value={line.expires_on} onChange={e=>update(index,'expires_on',e.target.value)}/></label>
            <label className="field"><span>Quantity (catalog units)</span><input type="number" required min="1" step="1" value={line.qty} onChange={e=>update(index,'qty',e.target.value)}/></label>
            <label className="field"><span>Condition</span><select value={line.condition} onChange={e=>update(index,'condition',e.target.value)}><option value="available">Available</option><option value="quarantine">Quarantine</option></select></label>
          </div>
        </div>)}
      </div>
      <div className="delivery-actions"><button className="btn outline" type="button" disabled={busy||lines.length>=50} onClick={()=>setLines(ls=>[...ls,empty()])}>+ Add batch line</button><button className="btn primary" disabled={busy||!canSubmit} type="submit">{busy?'Receiving…':`Receive ${lines.length} batch line${lines.length===1?'':'s'}`}</button></div>
      <p className="delivery-note">Please review product, unit, lot, expiry and quantity carefully. Any invalid line rejects the entire delivery. Duplicate submission protection is enabled.</p>
    </form>
  </section>;
}
