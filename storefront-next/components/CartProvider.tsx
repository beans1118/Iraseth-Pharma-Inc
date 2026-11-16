'use client';
import {createContext,useContext,useEffect,useMemo,useState} from 'react';
import type {ReactNode} from 'react';
import type {PublicProduct} from '@/lib/catalog';
type Item={product:PublicProduct;quantity:number};
type CartContextType={items:Item[];drawerOpen:boolean;open:()=>void;close:()=>void;add:(p:PublicProduct)=>void;remove:(id:string)=>void;changeQty:(id:string,qty:number)=>void;clear:()=>void};
const C=createContext<CartContextType|null>(null);
const STORE='iraseth_quotation_draft_v1';
export function CartProvider({children}:{children:ReactNode}){const [items,setItems]=useState<Item[]>([]);const [drawerOpen,setDrawerOpen]=useState(false);const [ready,setReady]=useState(false);
  useEffect(()=>{try{const saved=localStorage.getItem(STORE);if(saved){const parsed=JSON.parse(saved);if(Array.isArray(parsed))setItems(parsed.filter((i):i is Item=>i&&typeof i==='object'&&i.product&&typeof i.product.id==='string'&&i.product.inStock===true&&Number.isInteger(i.quantity)&&i.quantity>0));}}catch{}setReady(true)},[]);
  useEffect(()=>{if(ready)localStorage.setItem(STORE,JSON.stringify(items))},[items,ready]);
  const value=useMemo<CartContextType>(()=>({items,drawerOpen,open:()=>setDrawerOpen(true),close:()=>setDrawerOpen(false),add:p=>{if(!p.inStock)return;setItems(old=>{const prev=old.find(x=>x.product.id===p.id);return prev?old.map(x=>x.product.id===p.id?{...x,quantity:x.quantity+1}:x):[...old,{product:p,quantity:1}]});setDrawerOpen(true)},remove:id=>setItems(old=>old.filter(x=>x.product.id!==id)),changeQty:(id,quantity)=>setItems(old=>old.map(x=>x.product.id===id?{...x,quantity:Math.max(1,Math.floor(quantity)||1)}:x)),clear:()=>setItems([])}),[items,drawerOpen]);
  return <C.Provider value={value}>{children}</C.Provider>}
export function useCart(){const v=useContext(C);if(!v)throw Error('CartProvider is missing');return v}
