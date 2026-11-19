import { partnerLogos, type PartnerLogo } from '@/lib/partners';

const previewSlots = Array.from({ length: 6 }, (_, index) => index + 1);

function LogoGroup({ logos, duplicate = false }: { logos: PartnerLogo[]; duplicate?: boolean }) {
  return <div className="partner-logo-group" aria-hidden={duplicate || undefined}>
    {logos.map((partner) => <div className="partner-logo-card" key={partner.name}>
      <img src={partner.image} alt={duplicate ? '' : partner.name} loading="lazy" />
    </div>)}
  </div>;
}

function PreviewGroup({ duplicate = false }: { duplicate?: boolean }) {
  return <div className="partner-logo-group" aria-hidden={duplicate || undefined}>
    {previewSlots.map(index => <div className="partner-logo-card partner-logo-preview" key={index}>
      <svg aria-hidden="true" viewBox="0 0 36 28" fill="none"><rect x="1" y="1" width="34" height="26" rx="5" stroke="currentColor" strokeWidth="1.5"/><circle cx="12" cy="10" r="3" stroke="currentColor" strokeWidth="1.5"/><path d="m5 22 9-8 6 5 5-5 6 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
      <span>PARTNER LOGO {String(index).padStart(2, '0')}</span>
    </div>)}
  </div>;
}

/** Only genuine approved logo assets are shown in production. */
export default function EcosystemMarquee() {
  const hasLogos = partnerLogos.length > 0;
  if (!hasLogos && process.env.NODE_ENV === 'production') return null;

  return <div className="ecosystem-section" aria-labelledby="ecosystem-title">
    <div className="ecosystem-head">
      <p className="eyebrow">CONNECTED BY CARE</p>
      <h3 id="ecosystem-title">Our healthcare partners</h3>
      {!hasLogos && <p className="partner-preview-note">Preview layout — approved partner logos will appear here.</p>}
    </div>
    <div className="ecosystem-window">
      <div className="ecosystem-track">
        {hasLogos ? <><LogoGroup logos={partnerLogos} /><LogoGroup logos={partnerLogos} duplicate /></> : <><PreviewGroup/><PreviewGroup duplicate/></>}
      </div>
    </div>
  </div>;
}
