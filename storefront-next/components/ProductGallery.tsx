'use client';
import {useRef, useState} from 'react';
export default function ProductGallery({images, name}: {images: string[]; name: string}) {
  const [index, setIndex] = useState(0);
  const start = useRef<{x:number; y:number}|null>(null);
  function move(delta: number) {setIndex(i => (i + delta + images.length) % images.length);}
  return <div className="product-gallery" role="region" aria-roledescription="carousel" aria-label={name + ' images'}
    onKeyDown={e => {if (images.length > 1 && ['ArrowLeft','ArrowRight'].includes(e.key)) {e.preventDefault(); move(e.key === 'ArrowLeft' ? -1 : 1);}}}>
    <div className="gallery-viewport" tabIndex={0} aria-label="Product images. Use left and right arrow keys to browse."
      onTouchStart={e => {start.current = {x:e.touches[0].clientX, y:e.touches[0].clientY};}}
      onTouchEnd={e => {if (!start.current || !images.length) return; const dx=e.changedTouches[0].clientX-start.current.x, dy=e.changedTouches[0].clientY-start.current.y; if (Math.abs(dx)>45 && Math.abs(dx)>Math.abs(dy)) move(dx<0?1:-1); start.current=null;}}>
      {images.length ? <div className="gallery-track" style={{transform:`translateX(-${index * 100}%)`}}>{images.map((image,i) =>
        <div className="gallery-slide" key={image} aria-hidden={i!==index}><img src={image} alt={name + (i===0?' — primary image':` — image ${i+1}`)} draggable={false}/></div>)}</div> : <div className="gallery-placeholder">IRASETH PHARMA<span>Product image not yet available</span></div>}
      {images.length>1 && <><button type="button" className="gallery-arrow previous" aria-label="Previous product image" onClick={()=>move(-1)}>‹</button>
        <button type="button" className="gallery-arrow next" aria-label="Next product image" onClick={()=>move(1)}>›</button></>}
    </div>
    {images.length>0 && <><p className="gallery-indicator" aria-live="polite" aria-atomic="true">Image {index+1} of {images.length}{index===0?' · Primary image':''}</p>
      {images.length>1 && <div className="detail-thumbs" aria-label="Choose a product image">{images.map((image,i)=><button type="button" className={index===i?'selected':''} key={image}
        aria-label={'View '+(i===0?'primary image':'image '+(i+1))} aria-pressed={index===i} onClick={()=>setIndex(i)}><img src={image} alt=""/></button>)}</div>}</>}
  </div>;
}
