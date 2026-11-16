import Link from 'next/link';
import { company } from '@/lib/content';

export default function SiteFooter() {
  return <footer className="footer">
    <div className="container footer-grid">
      <div className="footer-main">
        <h2 className="footer-wordmark">Iraseth Pharma</h2>
        <p>Integrated medical and diagnostics solutions supporting healthcare teams across the Philippines.</p>
      </div>
      <div><h3>Explore</h3><Link href="/about">About us</Link><Link href="/mission-vision">Mission &amp; Vision</Link><Link href="/leadership">Leadership</Link><Link href="/products">Products</Link></div>
      <div><h3>Contact</h3><p>{company.address}</p><a href="tel:+63289426365">{company.phone}</a><a href="tel:+639171586736">{company.mobile}</a><Link href="/contact">Contact us →</Link></div>
    </div>
    <div className="container footer-bottom"><span>© {new Date().getFullYear()} Iraseth Pharma Incorporated</span><span>Healthcare solutions with purpose.</span></div>
  </footer>;
}
