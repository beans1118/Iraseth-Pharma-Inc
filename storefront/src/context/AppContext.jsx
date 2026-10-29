import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Api } from "../api";
import { Cart } from "../data";

const AppContext = createContext(null);

export function AppProvider({ children }){
  const [products, setProducts] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [, setCartVersion] = useState(0);
  const [cartOpen, setCartOpen] = useState(false);
  const [activeProduct, setActiveProduct] = useState(null);

  useEffect(() => {
    (async () => {
      await Api.detect();
      const live = await Api.getProducts();
      if(live) setProducts(live);
      setLoaded(true);
    })();
  }, []);

  const refreshCart = useCallback(() => setCartVersion(v => v + 1), []);
  const addToCart = useCallback((id, qty) => { Cart.add(id, qty); refreshCart(); }, [refreshCart]);
  const removeFromCart = useCallback((id) => { Cart.remove(id); refreshCart(); }, [refreshCart]);

  const value = {
    products, loaded,
    cartOpen, setCartOpen,
    cartCount: Cart.count(),
    cartLines: Cart.lines(products),
    cartTotal: Cart.total(products),
    addToCart, removeFromCart, refreshCart,
    activeProduct, setActiveProduct,
  };
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(){
  const ctx = useContext(AppContext);
  if(!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
