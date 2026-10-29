import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const SLIDES = [
  "https://images.unsplash.com/photo-1532938911079-1b06ac7ceec7?fm=jpg&q=80&w=1600&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1504813184591-01572f98c85f?fm=jpg&q=80&w=1600&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1516841273335-e39b37888115?fm=jpg&q=80&w=1600&auto=format&fit=crop",
];

const STEPS = [
  { num: "01", title: "Build your order", body: "Search or filter our catalog of diagnostic devices, PPE, and lab consumables, and add items straight to your order slip." },
  { num: "02", title: "Submit the requisition", body: "Confirm your facility details and submit. You'll get a reference number for tracking, same as a paper PO — just faster." },
  { num: "03", title: "We confirm & deliver", body: "Our team verifies stock and pricing, confirms by email, and coordinates delivery to your facility nationwide." },
];

export default function Home(){
  const [slide, setSlide] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSlide(s => (s + 1) % SLIDES.length), 6000);
    return () => clearInterval(t);
  }, []);

  return (
    <>
      <section className="hero">
        <div className="hero-bg-carousel">
          {SLIDES.map((src, i) => <div key={i} className={`hero-slide ${i === slide ? "active" : ""}`} style={{ backgroundImage: `url('${src}')` }} />)}
        </div>
        <div className="hero-overlay" />
        <div className="wrap hero-grid">
          <div>
            <div className="eyebrow eyebrow-light">Since 2013 · ISO-aligned distributor</div>
            <h1>Reorder your <em>medical supply</em>, instantly.</h1>
            <p className="lede">Iraseth Pharma supplies hospitals, clinics, and laboratories across the Philippines with diagnostic devices, PPE, and lab consumables — now orderable online in minutes, not days.</p>
            <div className="cta-row">
              <Link to="/catalog" className="btn btn-primary">Browse the catalog</Link>
              <Link to="/about" className="btn btn-ghost-light">About us</Link>
            </div>
            <div className="trust-row">
              <div><b>2013</b> Founded</div>
              <div><b>16+</b> Principal suppliers</div>
              <div><b>Nationwide</b> Delivery, PH</div>
              <div><b>Hospitals &amp; labs</b> Core clients</div>
            </div>
          </div>
          <div className="slip">
            <div className="perf" />
            <div className="slip-head"><span className="id">PO-20260034</span><span className="status">Ready to submit</span></div>
            <div className="slip-body">
              <div className="slip-row"><span className="name">Disposable Syringe 3 mL 26G</span><span className="meta">50 × per unit</span></div>
              <div className="slip-row"><span className="name">IV Cannula with Safety Features G22</span><span className="meta">10 × per box</span></div>
              <div className="slip-row"><span className="name">Adult Diaper M</span><span className="meta">30 × per unit</span></div>
            </div>
            <div className="slip-foot"><span>Est. delivery: 2-4 business days</span><span className="total">₱44,000.00</span></div>
          </div>
        </div>
      </section>

      <div className="strip">
        <div className="wrap">
          <div className="stat"><b>4</b><span>Product categories</span></div>
          <div className="stat"><b>16+</b><span>Principal suppliers</span></div>
          <div className="stat"><b>2–4 days</b><span>Typical delivery</span></div>
          <div className="stat"><b>24/7</b><span>Online ordering</span></div>
        </div>
      </div>

      <section>
        <div className="wrap">
          <div className="section-head center">
            <div className="eyebrow">How it works</div>
            <h2>From catalog to delivery, in three steps</h2>
            <p>No more back-and-forth over email or phone for repeat orders. Build your requisition online, and our team takes it from there.</p>
          </div>
          <div className="steps">
            {STEPS.map(s => (
              <div className="step" key={s.num}>
                <div className="num">{s.num}</div>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
