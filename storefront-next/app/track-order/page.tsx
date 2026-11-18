import TrackOrder from '@/components/TrackOrder';
export const metadata = {title: 'Track My Order', robots: {index: false, follow: false}, referrer: 'no-referrer' as const};
export default async function TrackingPage({searchParams}: {searchParams: Promise<{reference?: string}>}) {
  const {reference} = await searchParams;
  return <TrackOrder initialReference={typeof reference === 'string' && /^RFQ-[A-F0-9]{12}$/.test(reference) ? reference : ''}/>;
}
