import {useId, useRef, useState, type FormEvent} from 'react';
import {endpoints, type Product} from './api';
import './product-editor.css';

type Props = {product:Product|null;categories:string[];units:string[];onSaved:()=>Promise<void>;onCancel:()=>void};
export default function ProductEditor({product,categories,units,onSaved,onCancel}: Props) {
  const [name,setName]=useState(product?.name||''), [id,setId]=useState(product?.id||''), [category,setCategory]=useState(product?.category||'');
  const [unit,setUnit]=useState(product?.unit||''), [manufacturer,setManufacturer]=useState(product?.manufacturer||''), [description,setDescription]=useState(product?.description||'');
  const [brand,setBrand]=useState(product?.brand||'');
  const [model,setModel]=useState(product?.model||'');
  const provisional=product?.identity_status==='provisional';
  const [sku,setSku]=useState(product?.sku||''),[confirmIdentity,setConfirmIdentity]=useState(false),[identityNote,setIdentityNote]=useState('');
  const [features,setFeatures]=useState<string[]>(product?.key_features||[]), [specs,setSpecs]=useState<Array<{label:string;value:string}>>(product?.specifications||[]);
  const [images,setImages]=useState<string[]>(product?.images?.length?product.images:product?.image?[product.image]:[]);
  const [busy,setBusy]=useState(false), [uploading,setUploading]=useState(false), [error,setError]=useState('');
  const pending=useRef(false), uploadPending=useRef(false), prefix=useId();
  const disabled=busy||uploading;
  async function files(list:FileList|null, replace?:number) {
    if(!list?.length||uploadPending.current)return;
    const chosen=Array.from(list);
    if(replace===undefined&&chosen.length+images.length>8){setError('Use up to 8 images.');return;}
    if(chosen.some(file=>file.size>200000||!['image/png','image/jpeg','image/webp'].includes(file.type))){setError('Use PNG, JPEG or WebP files up to 200 KB each.');return;}
    uploadPending.current=true;setUploading(true);setError('');
    try {
      const urls=await Promise.all(chosen.map(file=>new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result));reader.onerror=()=>reject(new Error('Unable to read image.'));reader.readAsDataURL(file);})));
      const next=replace===undefined?[...images,...urls]:images.map((image,i)=>i===replace?urls[0]:image);
      if(new Set(next).size!==next.length)throw new Error('Remove duplicate images before saving.');
      setImages(next);
    } catch(e){setError(e instanceof Error?e.message:'Unable to load images.');}
    finally{uploadPending.current=false;setUploading(false);}
  }
  function move(from:number,to:number){setImages(old=>{const next=[...old];next.splice(to,0,next.splice(from,1)[0]);return next;});}
  async function save(e:FormEvent){
    e.preventDefault();if(pending.current||uploadPending.current)return;
    pending.current=true;setBusy(true);setError('');
    const data={id:id.trim(),name:name.trim(),description,category:category.trim(),unit:unit.trim(),brand:brand.trim(),manufacturer:manufacturer.trim(),model:model.trim(),images,image:images[0]||'',key_features:features,specifications:specs};
    try {if(product)await endpoints.updateProduct(product.id,{...data,...(provisional&&confirmIdentity?{sku,confirm_identity:true,identity_review_note:identityNote}:{})});else await endpoints.createProduct({...data,quantity:0,price:0});await onSaved();}
    catch(e){setError(e instanceof Error?e.message:'Unable to save product.');}
    finally{pending.current=false;setBusy(false);}
  }
  return <form className="product-create product-editor" onSubmit={save} aria-busy={disabled}>
    {error&&<p className="notice form-error" role="alert">{error}</p>}
    <fieldset disabled={disabled}><section className="product-create-card"><div className="product-create-head"><h2>Product details</h2><p>Fields marked * are required.</p></div>
      <div className="product-create-grid">
        <label className="field">Product name *<input required maxLength={200} value={name} onChange={e=>setName(e.target.value)}/></label>
        <label className="field">{product?.identity_status?'Internal product ID (not a SKU)':'Product ID / SKU *'}<input required disabled={!!product} maxLength={80} value={id} onChange={e=>setId(e.target.value)}/></label>
        <label className="field">Category *<input required list={prefix+'categories'} maxLength={160} value={category} onChange={e=>setCategory(e.target.value)}/><datalist id={prefix+'categories'}>{categories.map(c=><option key={c} value={c}/>)}</datalist></label>
        <label className="field">Unit *<input required list={prefix+'units'} maxLength={80} value={unit} onChange={e=>setUnit(e.target.value)}/><datalist id={prefix+'units'}>{units.map(u=><option key={u} value={u}/>)}</datalist></label>
        <label className="field">Brand (optional)<input maxLength={200} value={brand} onChange={e=>setBrand(e.target.value)}/></label>
        <label className="field">Manufacturer (optional)<input maxLength={200} value={manufacturer} onChange={e=>setManufacturer(e.target.value)}/></label>
        <label className="field">Documented model (optional)<input maxLength={200} value={model} onChange={e=>setModel(e.target.value)}/><span>Leave empty when no model is documented. Verify changes against supplier records.</span></label>
        {product?.identity_status&&<label className="field">Genuine SKU (required before receiving)<input maxLength={80} value={sku} disabled={!provisional} required={confirmIdentity} onChange={e=>setSku(e.target.value)}/></label>}
      </div>
      {provisional&&<><p className="notice" role="status">Provisional internal identity. The displayed pending unit is not a selling unit. Stock receiving, orders and invoices are blocked until the genuine SKU and selling unit are confirmed. The internal ID and product URL will stay unchanged.</p>
        <label><input type="checkbox" checked={confirmIdentity} onChange={e=>setConfirmIdentity(e.target.checked)}/> I confirm this genuine SKU and selling unit from staff/supplier records.</label>
        {confirmIdentity&&<label className="field">SKU/unit confirmation evidence<textarea required minLength={5} maxLength={2000} value={identityNote} onChange={e=>setIdentityNote(e.target.value)}/></label>}
        <p>Leave confirmation unchecked to edit descriptions, features, specifications or images only.</p></>}
      </section>
      <section className="product-create-card"><div className="product-create-head"><h2>Product description</h2></div><label className="field">Description (optional)<textarea rows={5} maxLength={12000} value={description} onChange={e=>setDescription(e.target.value)}/></label></section>
      <section className="product-create-card"><div className="product-create-head"><h2>Key features</h2><p>Only enter documented, approved product claims.</p></div>
        {features.map((feature,i)=><div className="metadata-row" key={i}><label className="field">Feature {i+1}<textarea aria-label={'Feature '+(i+1)} required maxLength={1000} value={feature} rows={2} onChange={e=>setFeatures(old=>old.map((f,j)=>j===i?e.target.value:f))}/></label><button type="button" className="btn outline" onClick={()=>setFeatures(old=>old.filter((_,j)=>j!==i))}>Remove feature {i+1}</button></div>)}
        <button type="button" className="btn outline" disabled={features.length>=40} onClick={()=>setFeatures(old=>[...old,''])}>Add feature</button></section>
      <section className="product-create-card"><div className="product-create-head"><h2>Specifications</h2><p>Optional documented label/value fields.</p></div>
        {specs.map((spec,i)=><div className="metadata-row specification-row" key={i}><label className="field">Specification {i+1} label<input required maxLength={160} value={spec.label} onChange={e=>setSpecs(old=>old.map((s,j)=>j===i?{...s,label:e.target.value}:s))}/></label>
          <label className="field">Specification {i+1} value<textarea aria-label={'Specification '+(i+1)+' value'} required maxLength={2000} rows={2} value={spec.value} onChange={e=>setSpecs(old=>old.map((s,j)=>j===i?{...s,value:e.target.value}:s))}/></label>
          <button type="button" className="btn outline" onClick={()=>setSpecs(old=>old.filter((_,j)=>j!==i))}>Remove specification {i+1}</button></div>)}
        <button type="button" className="btn outline" disabled={specs.length>=60} onClick={()=>setSpecs(old=>[...old,{label:'',value:''}])}>Add specification</button></section>
      <section className="product-create-card"><div className="product-create-head"><h2>Product image gallery</h2><p>Up to 8 static PNG, JPEG or WebP images. Maximum 200 KB and 16 megapixels per image. The first image is primary.</p></div>
        <label className="product-image-drop">Add gallery images<input type="file" multiple accept="image/png,image/jpeg,image/webp" disabled={images.length>=8} onChange={e=>{void files(e.target.files);e.target.value='';}}/></label>
        <ol className="editor-gallery">{images.map((image,i)=><li key={image}><img src={image} alt={'Gallery preview '+(i+1)}/><strong>{i===0?'Primary image':'Image '+(i+1)}</strong>
          <div className="editor-image-actions"><button type="button" className="btn outline" disabled={i===0} onClick={()=>move(i,0)}>Make primary</button>
          <button type="button" className="btn outline" aria-label={'Move image '+(i+1)+' earlier'} disabled={i===0} onClick={()=>move(i,i-1)}>Move earlier</button>
          <button type="button" className="btn outline" aria-label={'Move image '+(i+1)+' later'} disabled={i===images.length-1} onClick={()=>move(i,i+1)}>Move later</button>
          <label className="field">Replace image {i+1}<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>{void files(e.target.files,i);e.target.value='';}}/></label>
          <button type="button" className="btn outline" onClick={()=>setImages(old=>old.filter((_,j)=>j!==i))}>Remove image {i+1}</button></div></li>)}</ol>
      </section></fieldset>
      <div className="product-create-foot"><p>{product?'Metadata changes preserve stock, batches, reservations and invoice prices.':'Products start with zero stock. Receive physical inventory under Batch Inventory. Selling prices are entered when creating invoices.'} Public prices and visibility are controlled in Storefront Settings.</p>
        <div className="product-create-buttons"><button type="button" className="btn outline" disabled={disabled} onClick={onCancel}>Cancel</button><button type="submit" className="btn primary" disabled={disabled}>{busy?'Saving…':uploading?'Reading images…':product?'Save changes':'Save Product'}</button></div></div>
  </form>;
}
