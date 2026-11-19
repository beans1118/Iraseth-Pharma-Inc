// Run after both production builds. All database writes are isolated fixtures.
import {chromium,expect} from '@playwright/test';
import {spawn} from 'node:child_process';
import {randomBytes} from 'node:crypto';
import {existsSync,readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root=fileURLToPath(new URL('../../',import.meta.url)), site=path.join(root,'storefront-next');
const marker=randomBytes(6).toString('hex'),password=randomBytes(24).toString('base64url');
const ref='RFQ-'+randomBytes(6).toString('hex').toUpperCase(), declineRef='RFQ-'+randomBytes(6).toString('hex').toUpperCase();
const children=[];const logs=[];
function launch(exe,args,cwd,env={}) {
  const child=spawn(exe,args,{cwd,env:{...process.env,...env},stdio:['pipe','pipe','pipe'],windowsHide:true});
  child.stdout.on('data',data=>logs.push(data.toString()));child.stderr.on('data',data=>logs.push(data.toString()));
  children.push(child);return child;
}
async function ready(url) {
  const deadline=Date.now()+60000;
  while(Date.now()<deadline){try{if((await fetch(url,{signal:AbortSignal.timeout(1000)})).ok)return;}catch{}await new Promise(r=>setTimeout(r,200));}
  throw new Error('QA service did not become ready: '+url+'\n'+logs.join('').slice(-6000));
}
async function login(page,role){
  await page.goto('http://127.0.0.1:5174');
  await page.getByLabel('Email address',{exact:true}).fill(`qa-${role}-${marker}@example.invalid`);
  await page.getByLabel('Password',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Inventory overview'})).toBeVisible();
}
let browser, backendReady=false;
try {
  const backend=launch(path.join(root,'backend','.venv','Scripts','python.exe'),[path.join(root,'backend','tools','browser_qa_server.py')],path.join(root,'backend'));
  backend.stdin.end(JSON.stringify({marker,password,reference:ref,decline_reference:declineRef})+'\n');
  await ready('http://127.0.0.1:5011/api/health');backendReady=true;
  launch(process.execPath,[path.join(site,'node_modules','next','dist','bin','next'),'start','--hostname','127.0.0.1','--port','3101'],site,{CATALOG_API_BASE_URL:'http://127.0.0.1:5011'});
  launch(process.execPath,[path.join(root,'frontend','node_modules','vite','bin','vite.js'),'preview','--host','127.0.0.1','--port','5174','--strictPort'],path.join(root,'frontend'),{VITE_DEV_API_TARGET:'http://127.0.0.1:5011'});
  await Promise.all([ready('http://127.0.0.1:3101/track-order'),ready('http://127.0.0.1:5174')]);
  const executable=process.env.QA_BROWSER_EXECUTABLE||['C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe','C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'].find(existsSync);
  browser=await chromium.launch({headless:true,...(executable?{executablePath:executable}:{})});
  const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();
  const browserErrors=[];page.on('pageerror',error=>browserErrors.push(error.message));
  await page.goto('http://127.0.0.1:3101/products');
  await page.getByPlaceholder('Search products...').fill('Browser QA '+marker);
  await expect(page.getByText('105 products',{exact:true})).toBeVisible();
  const pagination=page.getByRole('navigation',{name:'Product pages'});
  for(let i=0;i<4;i++)await pagination.getByRole('button',{name:'Next',exact:true}).click();
  await expect(page.getByRole('heading',{name:`Browser QA ${marker} Product 104`,exact:true})).toBeVisible();
  await page.getByPlaceholder('Search products...').fill(`Browser QA ${marker} Product 000`);
  const opener=page.getByRole('link',{name:`View Browser QA ${marker} Product 000 details`,exact:true});
  await opener.click();
  let modal=page.getByRole('dialog',{name:`Browser QA ${marker} Product 000 details`});
  await expect(modal).toBeVisible();await expect(page).toHaveURL(new RegExp('PYTEST-BROWSER-'+marker+'-000'));
  const close=modal.getByRole('button',{name:'Close product details'});await expect(close).toBeFocused();
  await page.keyboard.press('Shift+Tab');await expect(modal.getByRole('link',{name:'Open standalone product page'})).toBeFocused();
  await page.keyboard.press('Tab');await expect(close).toBeFocused();
  await modal.getByRole('button',{name:'Next product image'}).click();await expect(modal.getByText('Image 2 of 3',{exact:true})).toBeVisible();
  await modal.getByRole('button',{name:'View image 3',exact:true}).click();await expect(modal.getByText('Image 3 of 3',{exact:true})).toBeVisible();
  await modal.locator('.gallery-viewport').focus();await page.keyboard.press('ArrowRight');await expect(modal.getByText('Image 1 of 3 · Primary image',{exact:true})).toBeVisible();
  await expect(modal.getByRole('button',{name:'Add to My Order',exact:true})).toBeEnabled();
  await page.keyboard.press('Escape');await expect(modal).not.toBeVisible();await expect(opener).toBeFocused();
  await opener.click();await expect(modal).toBeVisible();await page.goBack();await expect(modal).not.toBeVisible();await page.goForward();await expect(modal).toBeVisible();
  await page.reload();await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.getByRole('heading',{name:`Browser QA ${marker} Product 000`,exact:true})).toBeVisible();
  console.log('Browser: catalog >100 products, live filters, modal focus loop/restoration, slideshow, history and standalone URL passed.');

  await page.goto('http://127.0.0.1:3101/track-order');await expect(page.getByLabel('Email address',{exact:true})).toHaveCount(0);
  await page.getByLabel('RFQ reference code').fill(ref);await page.getByRole('button',{name:'Track inquiry',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Inquiry Received',exact:true})).toBeVisible();await expect(page.getByText('Private Browser Customer')).toHaveCount(0);
  await page.getByRole('button',{name:'Request Email Update'}).click();await page.getByLabel('Email address',{exact:true}).fill('qa-customer@example.invalid');
  await page.getByRole('button',{name:'Verify email to continue'}).click();await expect(page.locator('.tracking-error[role="alert"]')).toContainText('No email was sent');
  console.log('Browser: reference-only tracking and truthful unconfigured-email error passed.');

  const dashboard=await context.newPage();await login(dashboard,'subadmin');
  await dashboard.getByRole('button',{name:'Order Inquiries',exact:true}).click();
  const inquiry=dashboard.locator('article').filter({has:dashboard.getByText(ref,{exact:true})});
  const acceptButton=inquiry.getByRole('button',{name:'Accept Inquiry',exact:true});await acceptButton.click();
  const accept=dashboard.getByRole('dialog',{name:'Accept Order Inquiry?',exact:true});await expect(accept).toBeVisible();await expect(accept.getByRole('button',{name:'Cancel',exact:true})).toBeFocused();
  await dashboard.keyboard.press('Escape');await expect(accept).not.toBeVisible();await expect(acceptButton).toBeFocused();await acceptButton.click();
  let requests=0;await dashboard.route(`**/api/v2/quotations/${ref}/accept`,async route=>{requests++;await new Promise(r=>setTimeout(r,500));await route.continue();});
  await accept.getByRole('button',{name:'Accept & Create Order',exact:true}).click();await expect(accept.getByRole('button',{name:'Cancel',exact:true})).toBeDisabled();
  await dashboard.keyboard.press('Escape');await expect(accept).toBeVisible();await expect(accept).not.toBeVisible();assertEqual(requests,1,'one acceptance request');
  const status=await fetch('http://127.0.0.1:5011/api/public/tracking',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reference:ref})}).then(r=>r.json());assertEqual(status.status,'Pending Order','accepted inquiry stays Pending Order');
  const declined=dashboard.locator('article').filter({has:dashboard.getByText(declineRef,{exact:true})});await declined.getByRole('button',{name:'Decline',exact:true}).click();
  const decline=dashboard.getByRole('dialog',{name:'Decline Order Inquiry?',exact:true});await expect(decline).toBeVisible();await decline.getByRole('button',{name:'Cancel',exact:true}).click();await expect(decline).not.toBeVisible();
  console.log('Browser: branded inquiry dialogs, keyboard cancellation, busy Escape guard and one linked Pending Order passed.');

  await dashboard.getByRole('button',{name:'All Products',exact:true}).click();
  // Scope the exact fixture row, independent of other isolated test records.
  const row=dashboard.locator('tr').filter({hasText:`Browser QA ${marker} Product 000`});
  await row.getByRole('button',{name:'Edit metadata',exact:true}).click();await expect(dashboard.getByRole('heading',{name:'Edit Product',exact:true})).toBeVisible();
  await expect(dashboard.getByLabel('Product name *',{exact:true})).toHaveValue(`Browser QA ${marker} Product 000`);
  await dashboard.getByRole('button',{name:'Make primary',exact:true}).nth(1).click();
  await dashboard.getByRole('button',{name:'Add feature',exact:true}).click();await dashboard.getByLabel('Feature 2',{exact:true}).fill('Reviewed additional test feature');
  await dashboard.getByRole('button',{name:'Save changes',exact:true}).click();await expect(dashboard.getByRole('heading',{name:'All Products',exact:true})).toBeVisible();
  await dashboard.getByRole('button',{name:'Brochure Review',exact:true}).click();await expect(dashboard.getByText(/266 review records/)).toBeVisible();
  await expect(dashboard.getByRole('button',{name:'Run import dry run',exact:true})).toBeDisabled();
  // Approve a real source item only in the isolated QA server. This identity
  // and QA_TEST_UNIT are fixtures, never an iraseth_dev SKU/unit mapping.
  await dashboard.getByLabel('Search candidates',{exact:true}).fill('Microfusion Set');
  const candidate=dashboard.locator('.brochure-candidate').filter({has:dashboard.getByRole('heading',{name:'Microfusion Set',exact:true})});
  await expect(candidate.getByText('Source clear',{exact:true})).toBeVisible();
  const [mappingDownload]=await Promise.all([dashboard.waitForEvent('download'),dashboard.getByRole('button',{name:'Download staff mapping CSV',exact:true}).click()]);
  assertEqual(mappingDownload.suggestedFilename(),'staff-mapping-template.csv','mapping download');
  const sourceManifest=JSON.parse(readFileSync(path.join(root,'docs','brochure','import-manifest.json'),'utf8'));
  const micro=sourceManifest.candidates.find(c=>c.name==='Microfusion Set');
  const csvCells={candidate_id:micro.candidate_id,include_in_batch:'true',staff_approved_sku:'PYTEST-BROWSER-'+marker+'-BROCHURE',
    staff_approved_selling_unit:'QA_TEST_UNIT',model_decision:'not_documented',image_decision:'include',staff_approved:'false',images_approved:'false',
    name:'UNTRUSTED CSV NAME MUST NOT REPLACE SOURCE'};
  const csvQuote=s=>'"'+s.replaceAll('"','""')+'"';
  const mappingCsv=Object.keys(csvCells).map(csvQuote).join(',')+'\n'+Object.values(csvCells).map(csvQuote).join(',');
  await dashboard.getByLabel('Load selected batch CSV (draft only)',{exact:true}).setInputFiles({name:'isolated-qa-batch.csv',mimeType:'text/csv',buffer:Buffer.from(mappingCsv)});
  await expect(dashboard.getByText(/1 draft records loaded/)).toBeVisible();
  await expect(candidate.getByLabel('Staff-assigned product ID / SKU')).toHaveValue('PYTEST-BROWSER-'+marker+'-BROCHURE');
  await expect(candidate.getByLabel('I reviewed this record, its claims, selling unit and source warnings.')).not.toBeChecked();
  await expect(dashboard.getByText('UNTRUSTED CSV NAME MUST NOT REPLACE SOURCE')).toHaveCount(0);
  await candidate.getByLabel('Select this individual record for review').check();
  await candidate.getByLabel('Staff-assigned product ID / SKU').fill('PYTEST-BROWSER-'+marker+'-BROCHURE');
  await candidate.getByLabel('Approved selling unit').fill('QA_TEST_UNIT');
  await candidate.getByLabel('Review note and resolution of source warnings').fill('ISOLATED QA ONLY: test source review, disposable identifier and unit; no active-catalog approval.');
  await candidate.getByLabel('I reviewed this record, its claims, selling unit and source warnings.').check();
  await candidate.getByRole('button',{name:'Review source images',exact:true}).click();
  await expect(candidate.locator('.brochure-images img')).toBeVisible();
  await candidate.getByLabel('Model review decision',{exact:true}).selectOption('not_documented');
  await candidate.getByLabel('Image review decision',{exact:true}).selectOption('include');
  await candidate.getByLabel('I verified that these images clearly depict this exact product.').check();
  await dashboard.getByRole('button',{name:'Run import dry run',exact:true}).click();
  await expect(dashboard.getByText(/No records written/)).toBeVisible();
  await dashboard.getByLabel('I explicitly approve these selected records for creation through the existing product catalog.').check();
  await dashboard.getByRole('button',{name:'Approve selected & create products',exact:true}).click();
  await expect(dashboard.getByText(/Approved products created with zero stock/)).toBeVisible();
  await page.goto('http://127.0.0.1:3101/products');
  await page.getByPlaceholder('Search products...').fill('Microfusion Set');
  await expect(page.getByRole('heading',{name:'Microfusion Set',exact:true})).toBeVisible();
  await page.getByRole('link',{name:'View Microfusion Set details',exact:true}).click();
  const imported=page.getByRole('dialog',{name:'Microfusion Set details',exact:true});
  await expect(imported).toBeVisible();
  await expect(imported.getByText('Price Upon Request',{exact:true})).toBeVisible();
  await expect(imported.getByText('Out of Stock',{exact:true})).toBeVisible();
  await expect(imported.getByRole('button',{name:'Add to My Order',exact:true})).toBeDisabled();
  await expect(imported.getByText('POLYMED',{exact:true})).toBeVisible();
  await expect(imported.getByText(/Manufacturer:/)).toHaveCount(0);
  await expect(imported.getByRole('heading',{name:'Key features',exact:true})).toBeVisible();
  await expect(imported.getByRole('heading',{name:'Specifications',exact:true})).toBeVisible();
  await expect(imported.locator('.gallery-slide img')).toHaveCount(1);
  await imported.getByRole('button',{name:'Close product details'}).click();
  await page.getByRole('combobox').first().selectOption('POLYMED');
  await expect(page.getByRole('heading',{name:'Microfusion Set',exact:true})).toBeVisible();
  console.log('Browser: actual Microfusion staff review/dry run/approval -> Flask catalog -> Next product modal, source image, brand filter, PNR and out-of-stock gating passed; test database only.');
  await dashboard.locator('.side-user').click();await login(dashboard,'admin');await dashboard.getByRole('button',{name:'Order Inquiries',exact:true}).click();
  await expect(dashboard.getByRole('button',{name:'Accept Inquiry',exact:true})).toHaveCount(0);await expect(dashboard.getByRole('button',{name:'Decline',exact:true})).toHaveCount(0);
  await dashboard.getByRole('button',{name:'Brochure Review',exact:true}).click();await expect(dashboard.getByText(/266 review records/)).toBeVisible();await expect(dashboard.getByRole('button',{name:'Run import dry run',exact:true})).toHaveCount(0);
  console.log('Browser: metadata editor gallery/feature save, brochure preview and Board Admin view-only controls passed.');

  const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const phone=await mobile.newPage();
  await phone.goto('http://127.0.0.1:3101/products');await phone.getByPlaceholder('Search products...').fill(`Browser QA ${marker} Product 000`);
  await phone.getByRole('link',{name:`View Browser QA ${marker} Product 000 details`,exact:true}).click();
  const mobileModal=phone.getByRole('dialog');await expect(mobileModal).toBeVisible();const bounds=await mobileModal.boundingBox();assertEqual(Math.round(bounds.width),390,'mobile modal full width');
  await mobileModal.getByRole('button',{name:'Close product details'}).click();await phone.getByRole('button',{name:'Open navigation menu',exact:true}).click();await expect(phone.getByRole('navigation',{name:'Mobile navigation'}).getByRole('link',{name:'Track My Order'})).toBeVisible();
  assertEqual(browserErrors.length,0,'no storefront browser errors');await mobile.close();await context.close();
  console.log('Browser: mobile full-screen modal and Track My Order navigation passed.');
} finally {
  if(browser)await browser.close();
  if(backendReady){try{await fetch('http://127.0.0.1:5011/__qa/shutdown',{method:'POST'});}catch{}await new Promise(r=>setTimeout(r,1000));}
  for(const child of children.reverse())if(child.exitCode===null)child.kill();
}
function assertEqual(actual,expected,label){if(actual!==expected)throw new Error(`${label}: expected ${expected}, got ${actual}`);}
