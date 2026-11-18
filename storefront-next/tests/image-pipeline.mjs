// Exercise the native decoder/encoder used by Next image optimization.
// Existing approved assets are read only; all transformed output stays in memory.
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import sharp from 'sharp';

for(const name of ['logo-mark.png','logo.png','ceo.png']){
  const source=fileURLToPath(new URL('../public/brand/'+name,import.meta.url));
  for(const format of ['png','webp']){
    const output=await sharp(source).resize({width:256,withoutEnlargement:true}).toFormat(format).toBuffer();
    const metadata=await sharp(output).metadata();
    assert.equal(metadata.format,format);
    assert.ok(metadata.width>0&&metadata.width<=256);
    assert.ok(metadata.height>0&&output.length>0);
  }
}
console.log('Native Sharp '+sharp.versions.sharp+': three existing brand PNGs decoded, resized and re-encoded as PNG/WebP; no source assets changed.');
