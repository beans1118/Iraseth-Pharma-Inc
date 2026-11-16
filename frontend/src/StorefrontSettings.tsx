import {useEffect, useState, type FormEvent} from 'react';
import {endpoints, type Product} from './api';

function StorefrontRow({product,onSaved}:{product:Product;onSaved:()=>Promise<void>}){
  const [visible,setVisible] = useState(product.storefront_visible !== false);
  const [price,setPrice] = useState(product.storefront_price == null?'':String(product.storefront_price));
  const [busy,setBusy] = useState(false);
  const [message,setMessage] = useState('');
  useEffect(()=>{
    setVisible(product.storefront_visible!==false);
    setPrice(product.storefront_price==null?'':String(product.storefront_price));
  },[product.storefront_visible,product.storefront_price]);

  async function submit(e:FormEvent){
    e.preventDefault();setBusy(true);setMessage('');
    try{
      if(price.trim() && (!/^\d+(?:\.\d{1,2})?$/.test(price.trim())||Number(price)>999999999)){
        setMessage('Enter a valid PHP price with at most two decimal places.');return;
      }
      await endpoints.updateStorefrontSettings(product.id,{
        visible,
        publicPrice:price.trim()?Number(price):null,
      });
      await onSaved();
      setMessage('Saved and published to the live catalog.');
    }catch(e){setMessage(e instanceof Error?e.message:'Could not save storefront settings.');}
    finally{setBusy(false);}
  }
  return <form onSubmit={submit} className="storefront-settings-row">
    <strong>{product.name}<small style={{display:'block',fontWeight:400}}>{product.id}</small></strong>
    <label className="field"><span>Public price (PHP)</span><input aria-label={`Public price for ${product.name}`} type="number" min="0" max="999999999" step="0.01" placeholder="Price upon request" value={price} onChange={e=>setPrice(e.target.value)}/></label>
    <label className="field"><span>Website visibility</span><select aria-label={`Visibility for ${product.name}`} value={visible?'yes':'no'} onChange={e=>setVisible(e.target.value==='yes')}><option value="yes">Published</option><option value="no">Hidden</option></select></label>
    <button className="btn outline" type="submit" disabled={busy}>{busy?'Saving…':'Save'}</button>
    {message&&<small role="status" style={{gridColumn:'1 / -1'}}>{message}</small>}
  </form>
}

export default function StorefrontSettings({products,onSaved}:{products:Product[];onSaved:()=>Promise<void>}){
  return <section className="card" style={{padding:'1.25rem',marginTop:'1.25rem'}}>
    <h2 style={{margin:'0 0 .5rem'}}>Storefront prices & visibility</h2>
    <p className="muted">Products publish automatically when created. Hide a product or set its public catalog price here. This does not change invoice pricing or physical stock.</p>
    {products.length===0?<p className="muted">No products have been created yet.</p>:products.map(product=><StorefrontRow key={product.id} product={product} onSaved={onSaved}/>)}
    <style>{`.storefront-settings-row{display:grid;grid-template-columns:minmax(130px,2fr) minmax(140px,1fr) minmax(135px,1fr) auto;align-items:end;gap:12px;padding:14px 0;border-bottom:1px solid #dae2ee}.storefront-settings-row .field{min-width:0}.storefront-settings-row input,.storefront-settings-row select{width:100%}@media(max-width:760px){.storefront-settings-row{grid-template-columns:1fr 1fr}.storefront-settings-row strong{grid-column:1/-1}}@media(max-width:460px){.storefront-settings-row{grid-template-columns:1fr}.storefront-settings-row strong{grid-column:1}}`}</style>
  </section>
}
