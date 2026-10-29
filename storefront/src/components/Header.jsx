import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useApp } from "../context/AppContext";
import logo from "../assets/logo-mark.png";

const NAV_LINKS = [
  { to: "/", label: "Home" },
  { to: "/catalog", label: "Catalog" },
  { to: "/about", label: "About" },
  { to: "/mission", label: "Mission & Vision" },
  { to: "/leadership", label: "Leadership" },
  { to: "/locations", label: "Locations" },
  { to: "/contact", label: "Contact" },
];

export default function Header(){
  const { cartCount, setCartOpen } = useApp();
  const [menuOpen, setMenuOpen] = useState(false);
  const close = () => setMenuOpen(false);

  return (
    <header className="site-header">
      <div className="wrap">
        <NavLink to="/" className="logo" onClick={close}>
          <img src={logo} alt="Iraseth Pharma Incorporated" className="logo-img" />
        </NavLink>
        <nav id="siteNav" className={menuOpen ? "open" : ""}>
          {NAV_LINKS.map(l => (
            <NavLink key={l.to} to={l.to} end={l.to === "/"} onClick={close}>{l.label}</NavLink>
          ))}
          <a href="admin.html" className="nav-login" aria-label="Log in" title="Log in">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <circle cx="12" cy="8" r="3.6" /><path d="M4.5 20c1.3-3.6 4.2-5.5 7.5-5.5s6.2 1.9 7.5 5.5" />
            </svg>
          </a>
          <button className="nav-cta" style={{ border: "none" }} onClick={() => { close(); setCartOpen(true); }}>
            Order slip <span className="cart-count">{cartCount}</span>
          </button>
        </nav>
        <button className="nav-toggle" aria-label="Open menu" onClick={() => setMenuOpen(o => !o)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>
    </header>
  );
}
