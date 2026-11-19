import {NextResponse} from 'next/server';

export async function POST(request: Request) {
  const headers = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'};
  const base = process.env.CATALOG_API_BASE_URL || process.env.NEXT_PUBLIC_CATALOG_API_BASE;
  if (!base) return NextResponse.json({error: 'Tracking service is not configured.'}, {status: 503, headers});
  const origin = request.headers.get('origin');
  if (origin) {
    try {
      // Next may reconstruct request.url with its internal localhost name.
      // The browser-visible Host header retains the requested host and port.
      const parsed = new URL(origin);
      if (!['http:','https:'].includes(parsed.protocol) || parsed.host !== (request.headers.get('host') || new URL(request.url).host))
        return NextResponse.json({error: 'Invalid request origin.'}, {status: 403, headers});
    } catch {return NextResponse.json({error: 'Invalid request origin.'}, {status: 403, headers});}
  }
  try {
    const raw = await request.text();
    if (raw.length > 8000) return NextResponse.json({error: 'Request too large.'}, {status: 413, headers});
    let data;
    try {data = JSON.parse(raw);} catch {return NextResponse.json({error: 'Invalid JSON.'}, {status: 400, headers});}
    if (!data || typeof data !== 'object' || Array.isArray(data)) return NextResponse.json({error: 'A JSON object is required.'}, {status: 400, headers});
    const {operation = 'track', ...payload} = data;
    const paths: Record<string, string> = {track: '', 'request-code': '/request-code', 'verify-code': '/verify-code'};
    if (typeof operation !== 'string' || !Object.hasOwn(paths, operation)) return NextResponse.json({error: 'Invalid tracking operation.'}, {status: 400, headers});
    const response = await fetch(`${base.replace(/\/$/, '')}/api/public/tracking${paths[operation]}`, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
      cache: 'no-store', signal: AbortSignal.timeout(20000),
    });
    // Never trust browser-supplied forwarding headers. Flask's limiter uses the
    // gateway address here; direct Flask clients retain their own IP buckets.
    const retry = response.headers.get('Retry-After');
    return NextResponse.json(await response.json(), {status: response.status, headers: {...headers, ...(retry ? {'Retry-After': retry} : {})}});
  } catch {
    return NextResponse.json({error: 'Tracking service is temporarily unavailable. Please try again.'}, {status: 503, headers});
  }
}
