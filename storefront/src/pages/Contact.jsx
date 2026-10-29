import { Link } from "react-router-dom";
import PageHero from "../components/PageHero";

const MAPS = "https://www.google.com/maps/search/?api=1&query=77+EGT+Bldg.+JM+Basa+St.+Calumpang+Marikina+City+Philippines";

export default function Contact(){
  return (
    <>
      <PageHero eyebrow="Contact" title="Get in touch" subtitle="Questions about a product, a spec sheet, or a standing order? We're happy to help." />
      <section>
        <div className="wrap">
          <div className="steps">
            <div className="step value-card">
              <div className="value-icon">📞</div>
              <h3>Call us</h3>
              <p>(02) 8942-6365</p>
              <p>+63 917 158 6736</p>
            </div>
            <a className="step value-card map-link" href={MAPS} target="_blank" rel="noopener noreferrer">
              <div className="value-icon">📍</div>
              <h3>Visit us</h3>
              <p>77 EGT Bldg., JM Basa St., Calumpang, Marikina City, Philippines</p>
              <span className="map-link-cta">Open in Google Maps →</span>
            </a>
            <div className="step value-card">
              <div className="value-icon">🛒</div>
              <h3>Order online</h3>
              <p>Build your requisition in minutes, 24/7.</p>
              <Link to="/catalog" className="map-link-cta">Browse the catalog →</Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
