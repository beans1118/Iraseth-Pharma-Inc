export function resolveApiUrl(path:string,base:string=''):string {
  if(!path.startsWith('/api/'))throw new Error('API paths must start with /api/.');
  return base.trim().replace(/\/+$/,'')+path;
}
