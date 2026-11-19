import {useEffect, useMemo, useRef, useState} from 'react';
import {ImageOff, Search, X} from 'lucide-react';
import type {Batch, Product, Stock} from './api';
import './product-catalog.css';
import StorefrontSettings from './StorefrontSettings';

type Props = {products:Product[];stocks:Stock[];stockSummaryReady:boolean;batches:Batch[];canWrite:boolean;canPublish:boolean;onSaved:()=>Promise<void>;search:string;onSearch:(value:string)=>void;onEdit:(product:Product)=>void};
const number=(value:number|undefined)=>value===undefined?'Not loaded':new Intl.NumberFormat('en-PH').format(value);
const gallery=(product:Product)=>product.images?.length?product.images:product.image?[product.image]:[];

function ProductDetails({product,stock,batches,canWrite,canPublish,onSaved,onClose,onEdit}:{product:Product;stock?:Stock;batches:Batch[];canWrite:boolean;canPublish:boolean;onSaved:()=>Promise<void>;onClose:()=>void;onEdit:()=>void}) {
  const dialog=useRef<HTMLDialogElement>(null),[image,setImage]=useState(0),images=gallery(product);
  useEffect(()=>{const previous=document.activeElement as HTMLElement|null;const node=dialog.current!;node.showModal();return()=>{node.close();previous?.focus();};},[]);
  const pending=product.identity_status==='provisional';
  return <dialog ref={dialog} className="staff-product-dialog" aria-label={product.name+' product details'} onCancel={event=>{event.preventDefault();onClose();}}>
    <header className="staff-product-dialog-head"><div><p>PRODUCT DETAILS</p><h2>{product.name}</h2></div><button type="button" autoFocus className="icon-btn" aria-label="Close product details" onClick={onClose}><X size={20}/></button></header>
    <div className="staff-product-dialog-body">
      {pending&&<p className="notice" role="status">Genuine SKU and selling unit require confirmation. Receiving, releasing, reservations and fulfillment are blocked until authorized staff confirm them in Edit Product. Metadata and image editing remain available.</p>}
      <div className="staff-product-detail-grid"><section aria-label="Product images"><div className="staff-product-photo">{images.length?<img src={images[image]||images[0]} alt={product.name+' image '+(image+1)}/>:<span><ImageOff size={30}/>Image pending</span>}</div>{images.length>1&&<div className="staff-product-thumbnails">{images.map((src,i)=><button key={src} type="button" aria-label={'View product image '+(i+1)} aria-pressed={i===image} onClick={()=>setImage(i)}><img src={src} alt=""/></button>)}</div>}</section>
        <section><h3>Identity and metadata</h3><dl className="staff-product-fields"><div><dt>Internal product ID</dt><dd className="staff-product-id">{product.id}</dd></div><div><dt>Genuine SKU</dt><dd>{product.sku||(product.identity_status?'Not confirmed':product.id)}</dd></div><div><dt>Selling unit</dt><dd>{product.unit}</dd></div><div><dt>Identity state</dt><dd>{pending?'Provisional — confirmation required':product.identity_status==='confirmed'?'Staff confirmed':'Existing product identity'}</dd></div><div><dt>Category</dt><dd>{product.category}</dd></div><div><dt>Brand</dt><dd>{product.brand||'Not documented'}</dd></div><div><dt>Manufacturer</dt><dd>{product.manufacturer||'Not documented'}</dd></div><div><dt>Model</dt><dd>{product.model||'Not documented'}</dd></div></dl></section></div>
      <section><h3>Inventory summary</h3><dl className="staff-product-stock"><div><dt>Batch on hand</dt><dd>{number(stock?.on_hand)}</dd></div><div><dt>Reserved</dt><dd>{number(stock?.reserved)}</dd></div><div><dt>Available to release</dt><dd>{number(stock?.available)}</dd></div></dl><p className="staff-product-note">On hand includes physical stock in all batches. Available is eligible, unreserved stock reported by the inventory API. Identity restrictions still apply.</p>
        {batches.length?<div className="table-wrap"><table><thead><tr><th>Lot</th><th>Expiry</th><th>Condition</th><th>On hand</th><th>Reserved</th></tr></thead><tbody>{batches.map(batch=><tr key={batch.id}><td>{batch.lot}</td><td>{batch.expires_on}</td><td>{batch.unverified?'Unverified':batch.condition}</td><td>{number(batch.on_hand)}</td><td>{number(batch.reserved)}</td></tr>)}</tbody></table></div>:<p className="staff-product-note">No inventory batches loaded for this product.</p>}</section>
      <section><h3>Description</h3><p className="staff-product-description">{product.description||'No description provided.'}</p></section>
      {!!product.key_features?.length&&<section><h3>Key features</h3><ul>{product.key_features.map((feature,i)=><li key={i}>{feature}</li>)}</ul></section>}
      {!!product.specifications?.length&&<section><h3>Specifications</h3><dl className="staff-product-fields">{product.specifications.map((spec,i)=><div key={i}><dt>{spec.label}</dt><dd>{spec.value}</dd></div>)}</dl></section>}
      {canPublish&&<StorefrontSettings products={[product]} onSaved={onSaved}/>}
    </div><footer className="staff-product-dialog-foot"><button className="btn outline" type="button" onClick={onClose}>Close</button>{canWrite&&<button className="btn primary" type="button" onClick={onEdit}>Edit Product</button>}</footer>
  </dialog>;
}

export default function ProductCatalog({products,stocks,stockSummaryReady,batches,canWrite,canPublish,onSaved,search,onSearch,onEdit}:Props) {
  const [page,setPage]=useState(1),[size,setSize]=useState(25),[selected,setSelected]=useState<string|null>(null);
  const stockById=useMemo(()=>new Map(stocks.map(stock=>[stock.product_id,stock])),[stocks]);
  // The existing summary API returns only products with batches, capped at 500.
  // An absent row means zero only when that complete response loaded successfully.
  const stockFor=(id:string)=>stockSummaryReady?(stockById.get(id)??(stocks.length<500?{product_id:id,on_hand:0,reserved:0,available:0}:undefined)):undefined;
  const filtered=useMemo(()=>{const term=search.trim().toLocaleLowerCase();return products.filter(product=>[product.name,product.category,product.brand,product.manufacturer,product.id,product.sku].some(value=>value?.toLocaleLowerCase().includes(term)));},[products,search]);
  useEffect(()=>setPage(1),[search,size]);
  const pages=Math.max(1,Math.ceil(filtered.length/size)),current=Math.min(page,pages),start=(current-1)*size,rows=filtered.slice(start,start+size),detail=products.find(product=>product.id===selected);
  return <section className="panel staff-product-catalog" aria-label="Product catalog">
    <header className="staff-catalog-head"><div><h2>Product catalog</h2><p>{products.length} products in your catalog</p></div><label className="staff-catalog-search"><Search size={17}/><span className="sr-only">Search employee products</span><input value={search} onChange={event=>onSearch(event.target.value)} placeholder="Search name, category or SKU..."/></label></header>
    <div className="staff-catalog-table-wrap"><table className="staff-catalog-table"><thead><tr><th>Product</th><th>Category</th><th>Stock availability</th><th>Actions</th></tr></thead><tbody>
      {rows.map(product=>{const stock=stockFor(product.id),image=gallery(product)[0];return <tr key={product.id} data-product-id={product.id}><td><div className="staff-product-label"><div className="staff-product-thumb">{image?<img src={image} alt="" loading="lazy"/>:<ImageOff size={19} aria-hidden="true"/>}</div><strong>{product.name}</strong></div></td><td className="staff-product-category">{product.category}</td><td><span className={'staff-product-availability '+(stock&&stock.available>0?'available':'unavailable')}>{stock?stock.available>0?number(stock.available)+' available':'No available stock':'Stock data unavailable'}</span><small className="staff-product-on-hand">Batch on hand: {number(stock?.on_hand)}</small></td><td><div className="staff-product-actions"><button className="btn outline" type="button" aria-label={'View '+product.name} onClick={()=>setSelected(product.id)}>View</button>{canWrite&&<button className="btn outline" type="button" aria-label={'Edit metadata for '+product.name} onClick={()=>onEdit(product)}>Edit</button>}</div></td></tr>;})}
      {!rows.length&&<tr><td colSpan={4} className="staff-product-empty">No matching products. Try another name, category or SKU.</td></tr>}
    </tbody></table></div>
    <footer className="staff-catalog-footer"><p role="status">{filtered.length?start+1:0}–{Math.min(start+size,filtered.length)} of {filtered.length} products</p><label>Rows per page<select value={size} onChange={event=>setSize(Number(event.target.value))}><option value={25}>25</option><option value={50}>50</option></select></label><nav aria-label="Employee product pages"><button className="btn outline" type="button" disabled={current===1} onClick={()=>setPage(current-1)}>Previous</button><span>Page {current} of {pages}</span><button className="btn outline" type="button" disabled={current===pages} onClick={()=>setPage(current+1)}>Next</button></nav></footer>
    {detail&&<ProductDetails product={detail} stock={stockFor(detail.id)} batches={batches.filter(batch=>batch.product_id===detail.id)} canWrite={canWrite} canPublish={canPublish} onSaved={onSaved} onClose={()=>setSelected(null)} onEdit={()=>{setSelected(null);onEdit(detail);}}/>}
  </section>;
}
