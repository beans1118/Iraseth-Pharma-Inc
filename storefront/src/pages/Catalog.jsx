import { useEffect, useMemo, useState } from "react";
import { useApp } from "../context/AppContext";
import { fmtPHP, getCategories } from "../data";
import Pagination from "../components/Pagination";
import PageHero from "../components/PageHero";

const PAGE_SIZE = 9;
const CAT_ICON = { "syringes-needles": "💉", "patient-care": "🩹", "iv-therapy": "💧" };
const STOCK_LABEL = { "in-stock": "In stock", "low-stock": "Low stock", "out-of-stock": "Out of stock" };

function ProductCard({ p }){
  const { setActiveProduct, addToCart } = useApp();
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);

  function add(){
    addToCart(p.id, Math.max(1, parseInt(qty) || 1));
    setAdded(true);
    setTimeout(() => setAdded(false), 1200);
  }

  return (
    <div className="product-card" onClick={() => setActiveProduct(p)}>
      <div className="card-top">
        <span className="cat-tile">{CAT_ICON[p.category] || "🧪"}</span>
        <span className="brand">{p.id}</span>
      </div>
      <h4>{p.name || "Untitled product"}</h4>
      {p.description && <p className="desc">{p.description}</p>}
      {p.category && <span className="tag">{p.category}</span>}
      <div className="price-row">
        <span className="price">{fmtPHP(p.price)}</span>
        <span className={`stock-badge ${p.status || "out-of-stock"}`}>● {STOCK_LABEL[p.status] || "Out of stock"}</span>
      </div>
      <div className="qty-row" onClick={e => e.stopPropagation()}>
        <input type="number" min="1" value={qty} onChange={e => setQty(e.target.value)} />
        <button className="btn btn-primary add-btn" disabled={p.status === "out-of-stock"} onClick={add}>{added ? "Added ✓" : "Add to order"}</button>
      </div>
    </div>
  );
}

export default function Catalog(){
  const { products, loaded } = useApp();
  const [cat, setCat] = useState("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const categories = useMemo(() => getCategories(products), [products]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return products.filter(p =>
      (cat === "all" || p.category === cat) &&
      (!q || (p.name || "").toLowerCase().includes(q) || p.id.toLowerCase().includes(q))
    );
  }, [products, cat, query]);

  useEffect(() => { setPage(1); }, [cat, query]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const visible = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  return (
    <>
      <PageHero eyebrow="Catalog" title="Order medical & diagnostic supplies" subtitle="Prices shown are SRP (Suggested Retail Price), inclusive of 12% VAT." />
      <section className="catalog-section">
        <div className="wrap products-layout">
          <aside className="filter-box">
            <h5>Search</h5>
            <input type="text" className="search-input" placeholder="Search products or SKU..." value={query} onChange={e => setQuery(e.target.value)} />
            <h5>Category</h5>
            <div className="filter-list">
              {categories.map(c => (
                <button key={c.id} className={c.id === cat ? "active" : ""} onClick={() => setCat(c.id)}>{c.label}</button>
              ))}
            </div>
          </aside>
          <div>
            <div className="catalog-meta">
              {filtered.length} product{filtered.length === 1 ? "" : "s"}
              {filtered.length > 0 && <> · showing {(safePage - 1) * PAGE_SIZE + 1}–{Math.min(safePage * PAGE_SIZE, filtered.length)}</>}
            </div>
            {!loaded ? <p className="empty-state">Loading catalog…</p>
              : visible.length === 0 ? <p className="empty-state">No products match your search yet.</p>
              : <div className="product-grid">{visible.map(p => <ProductCard key={p.id} p={p} />)}</div>}
            <Pagination page={safePage} totalPages={totalPages} onChange={(p) => { setPage(p); window.scrollTo({ top: 0, behavior: "smooth" }); }} />
          </div>
        </div>
      </section>
    </>
  );
}
