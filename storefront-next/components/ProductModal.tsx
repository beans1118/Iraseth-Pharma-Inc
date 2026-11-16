'use client';
import {useEffect, useRef} from 'react';
import {useRouter} from 'next/navigation';
import type {PublicProduct} from '@/lib/catalog';
import ProductDetail from './ProductDetail';
export default function ProductModal({product}: {product:PublicProduct}) {
  const ref=useRef<HTMLDialogElement>(null), router=useRouter();
  useEffect(()=>{
    const previous=document.activeElement instanceof HTMLElement?document.activeElement:null;
    const dialog=ref.current!; dialog.showModal();
    const overflow=document.body.style.overflow; document.body.style.overflow='hidden';
    return ()=>{dialog.close(); document.body.style.overflow=overflow; previous?.focus();};
  },[]);
  return <dialog ref={ref} className="product-dialog" aria-modal="true" aria-label={product.name+' details'} onCancel={e=>{e.preventDefault();router.back();}}
    onKeyDown={e=>{
      if(e.key!=='Tab')return;
      const controls=Array.from(e.currentTarget.querySelectorAll<HTMLElement>('a[href],button,input,select,textarea,[tabindex]')).filter(node=>node.tabIndex>=0&&!node.matches(':disabled')&&node.getClientRects().length>0);
      const first=controls[0],last=controls.at(-1);
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}
      else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
    }}
    onClick={e=>{if(e.target===e.currentTarget) {const rect=e.currentTarget.getBoundingClientRect(); if(e.clientX<rect.left||e.clientX>rect.right||e.clientY<rect.top||e.clientY>rect.bottom)router.back();}}}>
    <div className="product-dialog-bar"><span>PRODUCT DETAILS</span><button autoFocus type="button" aria-label="Close product details" onClick={()=>router.back()}>✕</button></div>
    <ProductDetail product={product} modal onAdded={()=>router.back()}/>
  </dialog>;
}
