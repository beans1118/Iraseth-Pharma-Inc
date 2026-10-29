import { useState } from "react";
import { useApp } from "../context/AppContext";
import { fmtPHP, Orders } from "../data";

export default function CartDrawer(){
  const { cartOpen, setCartOpen, cartLines, cartTotal, removeFromCart, products, refreshCart } = useApp();
  const [form, setForm] = useState({ name: "", facility: "", email: "" });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const canSubmit = cartLines.length > 0 && form.name && form.facility && form.email && !submitting;
  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  async function handleSubmit(e){
    e.preventDefault();
    if(!canSubmit) return;
    setSubmitting(true);
    setResult(null);
    const res = await Orders.create({ client: form.name, email: form.email, facility: form.facility }, products);
    setSubmitting(false);
    refreshCart();
    if(res.ok){
      setResult({ ok: true, order: res.order });
      setForm({ name: "", facility: "", email: "" });
    } else {
      setResult({ ok: false, error: res.error });
    }
  }

  return (
    <>
      <div className={`overlay ${cartOpen ? "open" : ""}`} onClick={() => setCartOpen(false)} />
      <aside className={`cart-drawer ${cartOpen ? "open" : ""}`}>
        <div className="cart-drawer-head">
          <strong>Your order slip</strong>
          <button aria-label="Close cart" onClick={() => setCartOpen(false)}>×</button>
        </div>
        <div className="cart-items">
          {cartLines.length === 0 ? (
            <p className="empty-state">Your order slip is empty.<br />Add products from the catalog to get started.</p>
          ) : cartLines.map(line => (
            <div className="cart-line" key={line.id}>
              <div>
                <div className="name">{line.name}</div>
                <div className="meta">{line.qty} × {line.unit} · {fmtPHP(line.lineTotal)}</div>
              </div>
              <button className="rm" onClick={() => removeFromCart(line.id)}>Remove</button>
            </div>
          ))}
        </div>
        <div className="cart-drawer-foot">
          <div className="cart-total"><span>Total</span><span>{fmtPHP(cartTotal)}</span></div>
          {result?.ok && <div className="notice notice-ok">Order <b>{result.order.id}</b> submitted! We'll confirm by email shortly.</div>}
          {result && !result.ok && <div className="notice notice-err">{result.error}</div>}
          <form onSubmit={handleSubmit}>
            <p className="form-hint">No account needed — just fill in your details to order</p>
            <div className="field"><label htmlFor="cf-name">Contact name</label>
              <input id="cf-name" required placeholder="e.g. Dr. J. Reyes" value={form.name} onChange={set("name")} /></div>
            <div className="field"><label htmlFor="cf-facility">Facility / hospital</label>
              <input id="cf-facility" required placeholder="e.g. Marikina General Hospital" value={form.facility} onChange={set("facility")} /></div>
            <div className="field"><label htmlFor="cf-email">Email</label>
              <input id="cf-email" type="email" required placeholder="you@facility.ph" value={form.email} onChange={set("email")} /></div>
            <button type="submit" className="btn btn-primary btn-block" disabled={!canSubmit}>{submitting ? "Submitting…" : "Submit order"}</button>
          </form>
        </div>
      </aside>
    </>
  );
}
