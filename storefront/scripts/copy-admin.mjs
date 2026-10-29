import { cpSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../..");
const site = resolve(root, "site");

for(const item of ["admin.html", "css", "js", "assets"]){
  const from = resolve(root, item);
  if(existsSync(from)) cpSync(from, resolve(site, item), { recursive: true });
}
console.log("Copied admin console into", site);
