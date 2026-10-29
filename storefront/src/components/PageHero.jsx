export default function PageHero({ eyebrow, title, subtitle }){
  return (
    <section className="page-hero">
      <div className="wrap">
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
    </section>
  );
}
