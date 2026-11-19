import {NextResponse} from 'next/server';

// Same-origin Next.js proxy: Flask remains the source of truth and validates the cart.
export async function POST(request: Request) {
  const base = process.env.CATALOG_API_BASE_URL || process.env.NEXT_PUBLIC_CATALOG_API_BASE;
  if (!base) return NextResponse.json({error:'Quotation service is not configured.'},{status:503});
  const key = request.headers.get('idempotency-key') || '';
  if (!/^[A-Za-z0-9_-]{8,120}$/.test(key)) return NextResponse.json({error:'Invalid submission key.'},{status:400});
  try {
    const raw = await request.text();
    if (raw.length > 16000) return NextResponse.json({error:'Quotation request too large.'},{status:413});
    const response = await fetch(`${base.replace(/\/$/,'')}/api/public/quotations`, {
      method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':key},body:raw,cache:'no-store',signal:AbortSignal.timeout(12000)
    });
    const result:unknown = await response.json();
    return NextResponse.json(result,{status:response.status,headers:{'Cache-Control':'no-store'}});
  } catch {
    return NextResponse.json({error:'Quotation service is temporarily unavailable. Please try again.'},{status:503});
  }
}
