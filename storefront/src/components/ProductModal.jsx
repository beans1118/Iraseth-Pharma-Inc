import { useEffect, useState } from "react";
import { useApp } from "../context/AppContext";
import { fmtPHP } from "../data";

const STOCK_LABEL = { "in-stock": "In stock", "low-stock": "Low stock", "out-of-stock": "Out of stock" };

export default function ProductModal(){
  const { activeProduct: p, setActiveProduct, addToCart } = useApp();
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);

  useEffect(() => { setQty(1); setAdded(false); }, [p?.id]);

  useEffect(() => {
    if(!p) return;
    const onKey = (e) => { if(e.key === "Escape") setActiveProduct(null); };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [p, setActiveProduct]);

  const outOfStock = p?.status === "out-of-stock";
  function handleAdd(){
    addToCart(p.id, Math.max(1, parseInt(qty) || 1));
    setAdded(true);
    setTimeout(() => setAdded(false), 1200);
  }

  return (
    <div className={`product-modal-backdrop ${p ? "open" : ""}`} onClick={(e) => { if(e.target === e.currentTarget) setActiveProduct(null); }}>
      <div className="product-modal">
        <button className="product-modal-close" aria-label="Close" onClick={() => setActiveProduct(null)}>×</button>
        {p && (
          <div className="product-modal-body">
            <span className="brand">{p.id}</span>
            <h3>{p.name || "Untitled product"}</h3>
            {p.category && <span className="tag">{p.category}</span>}
            <p style={{ marginTop: 14 }}>{p.description || "No description available yet."}</p>
            <div className="pm-specs">
              <h5>Specifications</h5>
              {p.specs && p.specs.length
                ? p.specs.map((s, i) => <div className="pm-specs-row" key={i}><span>{s.label}</span><span>{s.value}</span></div>)
                : <div className="pm-specs-empty">Full specifications for this product haven't been added to the catalog yet — check back soon, or contact us for a spec sheet.</div>}
            </div>
            <div className="pm-footer">
              <div><span className="price">{fmtPHP(p.price)}</span><span className="unit">{p.unit}</span></div>
              <span className={`stock-badge ${p.status || "out-of-stock"}`}>{STOCK_LABEL[p.status] || "Out of stock"}</span>
            </div>
            <div className="pm-actions">
              <input type="number" min="1" value={qty} onChange={e => setQty(e.target.value)} />
              <button className="btn btn-primary" disabled={outOfStock} onClick={handleAdd}>
                {outOfStock ? "Out of stock" : added ? "Added ✓" : "Add to order"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
