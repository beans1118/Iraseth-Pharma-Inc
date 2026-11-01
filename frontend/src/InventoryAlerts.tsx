import {useEffect,useState} from 'react';
import {endpoints,type InventoryAlerts} from './api';
import './inventory-alerts.css';

export function InventoryAlertsPage({onViewBatches,onViewProducts}:{onViewBatches:()=>void;onViewProducts:()=>void}){
 const [days,setDays]=useState<30|60|90>(30);
 const [threshold,setThreshold]=useState(10);
 const [data,setData]=useState<InventoryAlerts|null>(null);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const [loading,setLoading]=useState(false);
 const [saving,setSaving]=useState('');
 const [drafts,setDrafts]=useState<Record<string,string>>({});
 const [refresh,setRefresh]=useState(0);
 useEffect(()=>{
  let mounted=true;setLoading(true);setError('');
  endpoints.inventoryAlerts(days,threshold).then(result=>{
   if(!mounted)return;
   setData(result);
   const next:Record<string,string>={};
   for(const p of result.all_products||[])next[p.product_id]=p.custom_threshold?String(p.threshold):'';
   setDrafts(next);
  }).catch(err=>{if(mounted){setData(null);setError(err instanceof Error?err.message:'Unable to load alerts')}})
  .finally(()=>{if(mounted)setLoading(false)});
  return()=>{mounted=false};
 },[days,threshold,refresh]);
 async function saveThreshold(productId:string){
  const raw=(drafts[productId]??'').trim();
  if(raw!=='' && (!/^\d+$/.test(raw)||Number(raw)>100000)){setError('Enter a whole number from 0 to 100000, or leave blank to use the fallback.');return}
  setSaving(productId);setError('');setNotice('');
  try{
   await endpoints.setInventoryThreshold(productId,raw===''?null:Number(raw));
   setNotice('Alert threshold saved. Inventory quantities were not changed.');
   setRefresh(x=>x+1);
  }catch(err){setError(err instanceof Error?err.message:'Unable to save threshold. Superadmin access is required.')}
  finally{setSaving('')}
 }
 return <section className="inventory-alerts">
  <div className="alerts-controls">
   <label>Expiry window <select value={days} onChange={e=>setDays(Number(e.target.value) as 30|60|90)}><option value={30}>30 days</option><option value={60}>60 days</option><option value={90}>90 days</option></select></label>
   <label>Default low-stock threshold <input type="number" min="0" max="100000" value={threshold} onChange={e=>setThreshold(Math.max(0,Math.min(100000,Number(e.target.value)||0)))}/></label>
   <button type="button" className="btn outline" onClick={()=>setRefresh(x=>x+1)}>Refresh alerts</button>
  </div>
  <p className="alerts-note">Set a low-stock level for each product below.</p>
  {loading&&<p role="status">Loading inventory alerts…</p>}
  {error&&<p className="alerts-error" role="alert">{error}</p>}
  {notice&&<p className="alerts-success" role="status">{notice}</p>}
  {data&&<>
   <div className="alerts-metrics">{[['Stockouts',data.stockouts.length],['Low-stock products',data.low_stock.length],[`Expiring in ${days} days`,data.expiring_batches.length],['Expired batches',data.expired_batches.length],['Restricted batches',data.restricted_batches.length]].map(([label,count])=><article key={label}><span>{label}</span><strong>{count}</strong></article>)}</div>
   <div className="alerts-panel"><div className="alerts-panel-title"><h3>Stockouts and low stock</h3><button className="btn outline" onClick={onViewProducts}>View products</button></div><div className="alerts-table"><table><thead><tr><th>Product</th><th>Category</th><th>Available</th><th>Low-stock level</th><th>Status</th></tr></thead><tbody>{[...data.stockouts,...data.low_stock].map(p=><tr key={p.product_id}><td>{p.product_name}<small>{p.product_id}</small></td><td>{p.category||'—'}</td><td>{p.available} {p.unit}</td><td>{p.threshold} {p.unit}{p.custom_threshold?' (saved)':' (fallback)'}</td><td>{p.available===0?'Stockout':'Low stock'}</td></tr>)}</tbody></table>{!data.stockouts.length&&!data.low_stock.length&&<p>No products below their thresholds.</p>}</div></div>
   <div className="alerts-panel"><div className="alerts-panel-title"><h3>Product low-stock settings</h3></div><p className="alerts-note">Leave a threshold blank to use the default.</p><div className="alerts-table"><table><thead><tr><th>Product</th><th>Available</th><th>Low-stock level</th><th>Action</th></tr></thead><tbody>{(data.all_products||[]).map(p=><tr key={p.product_id}><td>{p.product_name}<small>{p.product_id}</small></td><td>{p.available} {p.unit}</td><td><input className="alerts-threshold-input" aria-label={`Low stock threshold for ${p.product_name}`} type="number" min="0" max="100000" placeholder={`Default: ${threshold}`} value={drafts[p.product_id]??''} onChange={e=>setDrafts(prev=>({...prev,[p.product_id]:e.target.value}))}/></td><td><button type="button" className="btn outline" disabled={Boolean(saving)} onClick={()=>saveThreshold(p.product_id)}>{saving===p.product_id?'Saving…':'Save'}</button></td></tr>)}</tbody></table>{!data.all_products?.length&&<p>No products found.</p>}</div></div>
   <div className="alerts-panel"><div className="alerts-panel-title"><h3>Expiry and stock restrictions</h3><button className="btn outline" onClick={onViewBatches}>View batch inventory</button></div><div className="alerts-table"><table><thead><tr><th>Product ID</th><th>Lot</th><th>Expiry</th><th>On hand</th><th>Condition</th><th>Flag</th></tr></thead><tbody>{[...data.expired_batches.map(b=>({...b,flag:'Expired'})),...data.expiring_batches.map(b=>({...b,flag:'Expiring'})),...data.restricted_batches.map(b=>({...b,flag:'Restricted'}))].map((b,i)=><tr key={`${b.batch_id}-${i}`}><td>{b.product_id}</td><td>{b.lot}</td><td>{b.expires_on}</td><td>{b.on_hand}</td><td>{b.condition}</td><td>{b.flag}</td></tr>)}</tbody></table>{!data.expiring_batches.length&&!data.expired_batches.length&&!data.restricted_batches.length&&<p>No flagged batches in this window.</p>}</div></div>
   <p className="alerts-note">{data.note} Refreshed: {new Date(data.as_of_utc).toLocaleString('en-PH')}.</p>
  </>}
 </section>
}
