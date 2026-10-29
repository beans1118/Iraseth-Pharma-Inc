import PageHero from "../components/PageHero";
import ceo from "../assets/ceo.png";

export default function Leadership(){
  return (
    <>
      <PageHero eyebrow="Leadership" title="A message from our President & CEO" />
      <section>
        <div className="wrap">
          <div className="leadership-card">
            <img src={ceo} alt="Eduardo G. Tolosa Jr., President & CEO" className="leadership-photo" />
            <div>
              <p className="leadership-quote">"The Company strives to uphold its steadfast commitment to deliver quality and safe healthcare products and services through the use of the latest state-of-the-art medical supplies and equipment. By efficient use of research, we aim to introduce unparalleled technology development to enable us to be at par with the standards of the global market. We look forward to your continued support and patronage."</p>
              <p className="leadership-name">Eduardo G. Tolosa Jr.</p>
              <p className="eyebrow">President &amp; CEO</p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
