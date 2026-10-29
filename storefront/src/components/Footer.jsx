import { Link } from "react-router-dom";
import logo from "../assets/logo-mark.png";
import isoLogo from "../assets/iso_logo.png";

const MAPS = "https://www.google.com/maps/search/?api=1&query=77+EGT+Bldg.+JM+Basa+St.+Calumpang+Marikina+City+Philippines";

export default function Footer(){
  return (
    <footer>
      <div className="wrap">
        <div>
          <div className="footer-logo"><img src={logo} alt="Iraseth Pharma Incorporated" /></div>
          <p style={{ fontSize: 13, maxWidth: 280 }}>Philippine-based importer, indentor, and distributor of medical and diagnostic devices, laboratory supplies, and consumables.</p>
          <img src={isoLogo} alt="ISO 9001 Certified — TÜV NORD CERT GmbH" className="footer-iso" />
        </div>
        <div>
          <h5>Company</h5>
          <ul>
            <li><Link to="/">Home</Link></li>
            <li><Link to="/catalog">Catalog</Link></li>
            <li><Link to="/about">About</Link></li>
            <li><Link to="/mission">Mission &amp; Vision</Link></li>
            <li><Link to="/leadership">Leadership</Link></li>
            <li><a href="admin.html">Login</a></li>
          </ul>
        </div>
        <div>
          <h5>Marikina City (Main)</h5>
          <ul>
            <li><a href={MAPS} target="_blank" rel="noopener noreferrer">77 EGT Bldg., JM Basa St.,<br />Calumpang, Marikina City</a></li>
            <li>(02) 8942-6365 · +63 917 158 6736</li>
          </ul>
        </div>
      </div>
      <div className="bottom"><span>© 2026 Iraseth Pharma Inc. All rights reserved.</span></div>
    </footer>
  );
}
