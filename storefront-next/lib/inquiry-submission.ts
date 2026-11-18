/** Keep retry keys in this tab without persisting customer information. */
const STORE = 'iraseth_inquiry_retry_keys_v1';
// SHA-256 for HTTP contexts where SubtleCrypto is unavailable. The fingerprint
// must match Web Crypto so existing retry keys remain valid across contexts.
function sha256(bytes: Uint8Array): string {
  const primes: number[] = [];
  for (let n=2; primes.length<64; n++) {
    if (!primes.some(p => n % p === 0)) primes.push(n);
  }
  const constants=primes.map(p => (Math.cbrt(p) % 1 * 0x100000000) >>> 0);
  const state=primes.slice(0,8).map(p => (Math.sqrt(p) % 1 * 0x100000000) >>> 0);
  const padded=new Uint8Array(Math.ceil((bytes.length+9)/64)*64);
  padded.set(bytes); padded[bytes.length]=0x80;
  const view=new DataView(padded.buffer);
  view.setUint32(padded.length-8, Math.floor(bytes.length/0x20000000));
  view.setUint32(padded.length-4, (bytes.length*8) >>> 0);
  const rotate=(x:number,n:number)=>(x>>>n)|(x<<(32-n));
  for(let offset=0;offset<padded.length;offset+=64){
    const w=new Uint32Array(64);
    for(let i=0;i<16;i++)w[i]=view.getUint32(offset+i*4);
    for(let i=16;i<64;i++){
      const x=w[i-15],y=w[i-2];
      w[i]=(w[i-16]+(rotate(x,7)^rotate(x,18)^(x>>>3))+w[i-7]+(rotate(y,17)^rotate(y,19)^(y>>>10)))>>>0;
    }
    let [a,b,c,d,e,f,g,h]=state;
    for(let i=0;i<64;i++){
      const t1=(h+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+constants[i]+w[i])>>>0;
      const t2=((rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c)))>>>0;
      h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;
    }
    [a,b,c,d,e,f,g,h].forEach((value,i)=>{state[i]=(state[i]+value)>>>0});
  }
  return state.map(value=>value.toString(16).padStart(8,'0')).join('');
}

export async function submissionKey(payload: string): Promise<string> {
  const bytes = new TextEncoder().encode(payload);
  const hash = globalThis.crypto?.subtle
    ? Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', bytes)))
      .map(byte => byte.toString(16).padStart(2, '0')).join('')
    : sha256(bytes);
  // Fail before sending if durable retry storage is unavailable.
  const raw = sessionStorage.getItem(STORE);
  let keys: Record<string,string> = {};
  try { const parsed:unknown = raw ? JSON.parse(raw) : {}; if(parsed && typeof parsed === 'object' && !Array.isArray(parsed))keys=parsed as Record<string,string>; } catch {}
  if(typeof keys[hash] === 'string' && /^[A-Za-z0-9_-]{8,120}$/.test(keys[hash]))return keys[hash];
  if (!globalThis.crypto?.getRandomValues) throw new Error('Secure random generation is unavailable. Please open the storefront using localhost or HTTPS.');
  // getRandomValues is available on ordinary HTTP; randomUUID requires HTTPS.
  const key = Array.from(globalThis.crypto.getRandomValues(new Uint8Array(16)))
    .map(byte=>byte.toString(16).padStart(2,'0')).join('');
  keys[hash] = key;
  sessionStorage.setItem(STORE, JSON.stringify(keys));
  return key;
}
