import Image from 'next/image';
import PageIntro from '@/components/PageIntro';
import Reveal from '@/components/Reveal';
import {company} from '@/lib/content';
export const metadata={title:'Leadership'};
export default function Leadership(){return <><PageIntro eyebrow="LEADERSHIP" title="A message from our President & CEO" lead="The vision and commitment behind Iraseth Pharma's continued work."/><section className="section"><div className="container leadership-layout"><Reveal className="portrait-frame"><Image src="/brand/ceo.png" alt={`${company.ceo}, President and CEO`} width={400} height={421}/></Reveal><Reveal className="leadership-copy"><p className="eyebrow">A WORD FROM OUR LEADERSHIP</p><div className="quote-mark">“</div><blockquote>{company.ceoMessage}</blockquote><div className="signature-line"/><h2>{company.ceo}</h2><p>President & CEO</p></Reveal></div></section></>}
