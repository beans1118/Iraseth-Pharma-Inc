export default function Pagination({ page, totalPages, onChange }){
  if(totalPages <= 1) return null;
  const items = [];
  for(let i = 1; i <= totalPages; i++){
    if(i === 1 || i === totalPages || Math.abs(i - page) <= 1) items.push(i);
    else if(items[items.length - 1] !== "…") items.push("…");
  }
  return (
    <nav className="pagination" aria-label="Pagination">
      <button className="page-btn" disabled={page === 1} onClick={() => onChange(page - 1)}>‹ Prev</button>
      {items.map((p, i) => p === "…"
        ? <span key={`gap-${i}`} className="page-gap">…</span>
        : <button key={p} className={`page-btn ${p === page ? "active" : ""}`} onClick={() => onChange(p)}>{p}</button>)}
      <button className="page-btn" disabled={page === totalPages} onClick={() => onChange(page + 1)}>Next ›</button>
    </nav>
  );
}
