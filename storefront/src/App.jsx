import { HashRouter, Route, Routes, Navigate } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Catalog from "./pages/Catalog";
import About from "./pages/About";
import Mission from "./pages/Mission";
import Leadership from "./pages/Leadership";
import Locations from "./pages/Locations";
import Contact from "./pages/Contact";

export default function App(){
  return (
    <AppProvider>
      <HashRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="catalog" element={<Catalog />} />
            <Route path="about" element={<About />} />
            <Route path="mission" element={<Mission />} />
            <Route path="leadership" element={<Leadership />} />
            <Route path="locations" element={<Locations />} />
            <Route path="contact" element={<Contact />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </HashRouter>
    </AppProvider>
  );
}
