import { Link } from "react-router-dom";
import PageHero from "../components/PageHero";

const MAPS = "https://www.google.com/maps/search/?api=1&query=77+EGT+Bldg.+JM+Basa+St.+Calumpang+Marikina+City+Philippines";

export default function Locations(){
  return (
    <>
      <PageHero eyebrow="Where we operate" title="Our location" subtitle="Visit our main office in Marikina City." />
      <section>
        <div className="wrap">
          <a href={MAPS} target="_blank" rel="noopener noreferrer" className="step map-link map-card">
            <h3>Marikina City — Main Office</h3>
            <p>77 EGT Bldg., JM Basa St., Calumpang, Marikina City, Philippines</p>
            <p className="phone">(02) 8942-6365 · +63 917 158 6736</p>
            <span className="map-link-cta">View on Google Maps →</span>
          </a>
          <div className="cta-band">
            <div>
              <h3>Ready to place a standing order?</h3>
              <p>Add items to your order slip and submit — our team confirms availability and delivery timing.</p>
            </div>
            <Link to="/catalog" className="btn btn-white">Go to catalog →</Link>
          </div>
        </div>
      </section>
    </>
  );
}
