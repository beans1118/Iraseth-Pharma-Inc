'use client';
import {useState} from 'react';

/** Reuses the exact image URL/data URI attached to the selected catalog product. */
export default function CartProductImage({src,name}:{src?:string;name:string}) {
  const [failed,setFailed]=useState(false);
  return <div style={{width:76,height:76,flex:"0 0 76px",display:"grid",placeItems:"center",overflow:"hidden",background:"white",border:"1px solid #DEE8F4",borderRadius:12}}>
    {src && !failed ?
      // The catalog may return uploaded data: URLs as well as http(s) URLs.
      // eslint-disable-next-line @next/next/no-img-element
      <img src={src} alt={name} loading="lazy" onError={()=>setFailed(true)}/> :
      <span style={{fontSize:12,color:"#566985",textAlign:"center",padding:8}} aria-label="Product image unavailable">No image</span>}
  </div>;
}
