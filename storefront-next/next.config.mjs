/** @type {import('next').NextConfig} */
if(process.env.VERCEL==='1'){
  for(const key of ['CATALOG_API_BASE_URL','NEXT_PUBLIC_STAFF_LOGIN_URL']){
    let url;
    try{url=new URL(process.env[key]||'');}catch{throw new Error(key+' must be configured with an HTTPS origin on Vercel.');}
    if(url.protocol!=='https:'||url.pathname!=='/'||url.search||url.hash||url.username||url.password)
      throw new Error(key+' must be an HTTPS origin without /api, credentials or query.');
  }
}
const nextConfig = { reactStrictMode: true };
export default nextConfig;
