import PageHero from "../components/PageHero";

const VALUES = [
  { icon: "🛡️", title: "Quality first", body: "ISO 9001-aligned standards guide how we source, store, and deliver every product." },
  { icon: "🤝", title: "Trusted partners", body: "We work with 16+ established global manufacturers of diagnostic and medical equipment." },
  { icon: "🚚", title: "Reliable delivery", body: "Nationwide distribution to hospitals, clinics, laboratories, and local government units." },
];

export default function About(){
  return (
    <>
      <PageHero eyebrow="About Iraseth Pharma" title="Who we are" subtitle="Integrated medical and diagnostics solutions for the Philippines." />
      <section>
        <div className="wrap">
          <div className="about-copy">
            <p>Iraseth Pharma Incorporated is a Philippine-based company providing integrated medical and diagnostics solutions for the country's foremost hospitals and clinical laboratories. Ever since its establishment in July 2013, we've been one of the country's rapidly growing trading companies in healthcare solutions — importing, indenting, and distributing medical and diagnostic devices, laboratory supplies, and consumables at cost, for local government units and private facilities alike.</p>
            <p>We take pride in contributing to society by creating a safe working environment for every patient and the entire healthcare team, backed by ISO 9001-aligned quality standards.</p>
          </div>
          <div className="steps">
            {VALUES.map(v => (
              <div className="step value-card" key={v.title}>
                <div className="value-icon">{v.icon}</div>
                <h3>{v.title}</h3>
                <p>{v.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
