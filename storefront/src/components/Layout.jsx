import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";
import CartDrawer from "./CartDrawer";
import ProductModal from "./ProductModal";

export default function Layout(){
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return (
    <>
      <Header />
      <main className="page"><div key={pathname} className="page-fade"><Outlet /></div></main>
      <Footer />
      <CartDrawer />
      <ProductModal />
    </>
  );
}
