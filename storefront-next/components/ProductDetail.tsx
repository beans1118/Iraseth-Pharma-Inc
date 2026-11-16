'use client';
import Link from 'next/link';
import {useCart} from './CartProvider';
import ProductGallery from './ProductGallery';
import {formatPrice,type PublicProduct} from '@/lib/catalog';
export default function ProductDetail({product, modal=false, onAdded}: {product:PublicProduct; modal?:boolean; onAdded?:()=>void}) {
 const images = product.imageUrls?.length ? product.imageUrls : product.imageUrl ? [product.imageUrl] : [];
 const cart = useCart();
 return <section className="section product-detail-section"><div className="container">
 {!modal && <div className="breadcrumb"><Link href="/products">Products</Link> / {product.category}</div>}
 <div className="detail-grid"><ProductGallery images={images} name={product.name}/><div className="detail-copy">
 <p className="eyebrow">{product.category}</p><h1>{product.name}</h1>{product.brand && <p className="detail-brand">{product.brand}</p>}
 {product.manufacturer && <p className="detail-brand">Manufacturer: {product.manufacturer}</p>}
 {product.model && <p className="detail-brand">Model: {product.model}</p>}
 <span className={product.inStock?'stock-label':'stock-label out'}>{product.inStock?'In Stock':'Out of Stock'}</span>
 <div className="detail-price">{formatPrice(product.publicPrice)}</div>
 <p className="product-description">{product.description||'Contact our team for additional product information.'}</p>
 {!!product.keyFeatures?.length && <div className="product-features"><h2>Key features</h2><ul>{product.keyFeatures.map((feature,i)=><li key={i}>{feature}</li>)}</ul></div>}
 {!!product.specifications?.length && <div className="product-specifications"><h2>Specifications</h2><dl>{product.specifications.map((spec,i)=><div key={i}><dt>{spec.label}</dt><dd>{spec.value}</dd></div>)}</dl></div>}
 <button className="button button-primary" onClick={()=>{cart.add(product);onAdded?.();}} disabled={!product.inStock}>Add to My Order</button>
 {!product.inStock && <p className="form-note">This product is currently unavailable to add to My Order.</p>}
 <p className="detail-note">Public prices are approved catalog reference prices. Final quotations are subject to confirmation.</p>
 {modal && <a className="text-link" href={'/products/'+encodeURIComponent(product.slug)}>Open standalone product page</a>}
 </div></div></div></section>;
}
