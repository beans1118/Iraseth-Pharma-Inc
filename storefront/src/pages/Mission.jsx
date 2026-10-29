import PageHero from "../components/PageHero";

const ITEMS = [
  { title: "Mission", body: "To provide access to quality pharmaceutical and medical device products with innovative and safety features that adhere to high standards of quality and service — creating a safe working environment in hospital settings and communities." },
  { title: "Vision", body: "We envision ourselves as a prime provider of high-quality medical devices and pharmaceutical products that substantially upgrade the quality of health services for the Filipino people — and to eradicate needle stick injuries in hospital settings while promoting early screening for diabetes and communicable diseases." },
  { title: "Commitment", body: "To make a difference by being a responsible organization that builds and supports a safe working environment for every healthcare provider, patient, and community." },
];

export default function Mission(){
  return (
    <>
      <PageHero eyebrow="What drives us" title="Mission, vision & commitment" />
      <section>
        <div className="wrap">
          <div className="steps">
            {ITEMS.map(i => (
              <div className="step" key={i.title}>
                <div className="num">{i.title}</div>
                <p className="mv-body">{i.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
