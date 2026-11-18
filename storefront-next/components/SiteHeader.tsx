'use client';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

const staffLoginUrl = process.env.NEXT_PUBLIC_STAFF_LOGIN_URL || 'http://localhost:5173';

const nav = [
  { label: 'Home', href: '/' },
  { label: 'About', href: '/about' },
  { label: 'Mission & Vision', href: '/mission-vision' },
  { label: 'Leadership', href: '/leadership' },
  { label: 'Products', href: '/products' },
  { label: 'Track My Order', href: '/track-order' },
  { label: 'Contact', href: '/contact' },
];

export default function SiteHeader() {
  const [menu, setMenu] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const pathname = usePathname();
  const closeRef = useRef<HTMLButtonElement>(null);
  const openRef = useRef<HTMLButtonElement>(null);

  useEffect(() => { setMounted(true); }, []);
  useEffect(() => { setMenu(false); }, [pathname]);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  useEffect(() => {
    if (!menu) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setMenu(false); openRef.current?.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = original;
      document.removeEventListener('keydown', onKey);
    };
  }, [menu]);

  const current = (href: string) => href === '/' ? pathname === '/' : pathname.startsWith(href);
  return <>
    <header className={'site-header ' + (scrolled ? 'is-scrolled' : '')}>
      <div className="container header-row">
        <Link href="/" className="brand" aria-label="Iraseth Pharma home">
          <Image src="/brand/logo-mark.png" alt="Iraseth Pharma" width={186} height={60} priority className="brand-image" />
        </Link>
        <nav className="desktop-nav" aria-label="Main navigation">
          {nav.map(item => <Link key={item.href} href={item.href} aria-current={current(item.href) ? 'page' : undefined}>{item.label}</Link>)}
          <a href={staffLoginUrl}>Log In</a>
        </nav>
        <div className="header-actions">
          <Link href="/cart" className="my-order-link" aria-current={pathname === '/cart' ? 'page' : undefined}>My Order</Link>
          <button ref={openRef} type="button" className="menu-button" aria-label={menu ? 'Close navigation menu' : 'Open navigation menu'} aria-expanded={menu} aria-controls="mobile-navigation" onClick={() => setMenu(!menu)}>
            <span aria-hidden="true">{menu ? '✕' : '☰'}</span>
          </button>
        </div>
      </div>
    </header>
    {mounted && menu && createPortal(
      <div className="mobile-backdrop">
        <button type="button" className="mobile-backdrop-dismiss" aria-label="Close navigation menu" onClick={() => setMenu(false)} />
        <nav id="mobile-navigation" className="mobile-menu" aria-label="Mobile navigation">
          <div className="mobile-top"><b>Explore Iraseth</b><button ref={closeRef} type="button" aria-label="Close menu" onClick={() => { setMenu(false); openRef.current?.focus(); }}>✕</button></div>
          {[...nav, {label: 'My Order', href: '/cart'}].map(item =>
            <Link key={item.href} href={item.href} className={current(item.href) ? 'mobile-active' : ''} aria-current={current(item.href) ? 'page' : undefined} onClick={() => setMenu(false)}>{item.label}<span aria-hidden="true">↗</span></Link>
          )}
          <a href={staffLoginUrl} onClick={() => setMenu(false)}>Log In<span aria-hidden="true">↗</span></a>
        </nav>
      </div>, document.body
    )}
  </>;
}
