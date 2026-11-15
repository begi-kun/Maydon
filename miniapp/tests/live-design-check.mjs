/** Read-only public production check. Never creates a booking or uses signed user data. */
import assert from 'node:assert/strict';
import {access,mkdir,writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {chromium} from 'playwright';
const require=createRequire(import.meta.url);
const web=process.env.DESIGN_WEB_URL||'https://maydon-web-production-3612.up.railway.app';
const api=process.env.DESIGN_API_URL||'https://maydon-production-ba2c.up.railway.app';
const output=new URL('../../artifacts/design/',import.meta.url);await mkdir(output,{recursive:true});
const mac='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const executablePath=process.env.CHROME_PATH||await access(mac).then(()=>mac).catch(()=>undefined);
const browser=await chromium.launch({headless:true,executablePath});
try {
 const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,timezoneId:'Asia/Tashkent'});
 const failures=[];page.on('pageerror',e=>failures.push(e.message));
 const report={checkedAt:new Date().toISOString(),web,environment:'Public production, real API/photos; no authenticated or mutating calls',checks:[],accessibility:[]};
 const venues=await (await fetch(api+'/venues')).json();
 for(const width of [360,390,430,768,1280]){await page.setViewportSize({width,height:844});await page.goto(web,{waitUntil:'domcontentloaded'});await page.locator('.welcome-compact').waitFor();if(venues.length)await page.locator('.venue-card').first().waitFor();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:new URL(`live-${width}.png`,output).pathname,fullPage:true});report.checks.push({width,overflow:false})}
 async function audit(name){await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});const {violations}=await page.evaluate(()=>window.axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}}));report.accessibility.push({name,violations:violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))});}
 await audit('home-desktop');await page.setViewportSize({width:390,height:844});await audit('home');
 if(venues.length){const venue=venues.find(v=>v.photos?.length)||venues[0];await page.goto(`${web}/?venue=${venue.id}`,{waitUntil:'domcontentloaded'});await page.locator('.booking-picker').waitFor();await page.locator('.time-grid,.booking-picker [role=alert]').first().waitFor();if(venue.photos?.length){await page.locator('.detail-gallery img').first().waitFor();assert(await page.locator('.detail-gallery img').first().evaluate(img=>img.complete&&img.naturalWidth>0));report.checks.push('real production photo loaded')}
 const available=page.locator('.time-grid button:not(:disabled)');if(await available.count()){await available.first().click();await page.locator('.booking-summary').waitFor();const link=page.getByRole('link',{name:'Telegramda bron qilish'});await link.waitFor();assert.match(await link.getAttribute('href'),new RegExp(`start=book_${venue.id}_\\d+`));report.checks.push('production availability, summary and Telegram venue/slot link')}
 await audit('detail');await page.screenshot({path:new URL('live-detail-390.png',output).pathname,fullPage:true});}
 assert.deepEqual(failures,[]);await writeFile(new URL('live-results.json',output),JSON.stringify(report,null,2));assert.deepEqual(report.accessibility.filter(a=>a.violations.length),[],'Production accessibility failures: '+JSON.stringify(report.accessibility));console.log('PASS: production design, real photos/availability, Telegram return link and WCAG audits');
} finally {await browser.close()}
