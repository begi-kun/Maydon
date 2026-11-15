/** Repeatable UI acceptance checks. Run npm run test:design (uses local Chrome, or Playwright Chromium). */
import assert from 'node:assert/strict';
import {mkdir, writeFile, access} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import {chromium} from 'playwright';
const require=createRequire(import.meta.url);
const output=new URL('../../artifacts/design/',import.meta.url);
await mkdir(output,{recursive:true});
const port=5187;
const server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port)],{cwd:new URL('..',new URL('.',import.meta.url)),env:{...process.env,VITE_API_URL:'http://127.0.0.1:8009'},stdio:'ignore'});
let browser;
try {
 for(let i=0;i<80;i++){try{if((await fetch(`http://127.0.0.1:${port}`)).ok)break}catch{}await new Promise(r=>setTimeout(r,100));}
 const macChrome='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
 const executablePath=process.env.CHROME_PATH || await access(macChrome).then(()=>macChrome).catch(()=>undefined);
 browser=await chromium.launch({executablePath,headless:true});
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,timezoneId:'Asia/Tashkent'});
 const page=await context.newPage();
 await page.route('https://fonts.googleapis.com/**',r=>r.abort());
 await page.route('https://telegram.org/**',r=>r.abort());
 const tomorrow=new Date(Date.now()+86400000).toLocaleDateString('en-CA',{timeZone:'Asia/Tashkent'});
 const start=`${tomorrow}T20:00:00+05:00`;
 let mode='normal',contact=false,searchCount=0,bookingCount=0;
 const venue={id:1,name:'Namangan sport maydoni',sport:'football',address:'Namangan, Davlatobod tumani',price:150000,photos:[],latitude:41,longitude:71,hours:'08:00–23:00',status:'approved',suspended:false};
 let ownerBookings=[];
 await page.addInitScript(()=>{window.Telegram={WebApp:{ready(){},expand(){},get initData(){return sessionStorage.getItem('test-auth')||''},requestContact(callback){window.dispatchEvent(new Event('test-contact'));callback(true)}}}});
 await page.route('http://127.0.0.1:8009/**',async route=>{
  const url=new URL(route.request().url()),path=url.pathname;
  const json=data=>route.fulfill({json:data});
  if(path==='/auth/config')return json({bot_username:'maydon_test_bot'});
  if(path==='/auth/me')return json({id:101,first_name:'Test egasi',admin:false});
  if(path==='/auth/contact')return json({phone:contact?'+998900000001':null});
  if(path==='/owner/venues')return json([venue]);
  if(path==='/owner/overview')return json({today:1,pending:1,value:150000,unpaid:1});
  if(path==='/owner/bookings')return json([{id:10,venue_name:venue.name,start_at:start,status:'pending',source:'telegram',customer_name:'Test',customer_phone:null,payment_status:'unpaid',booked_price:150000}]);
  if(path==='/owner/schedule')return json({hours:'08:00–23:00',slots:[{start_at:start,status:'available',booking:null,block:null}]});
  if(path==='/owner/manual-bookings'||path==='/owner/blocks'){ownerBookings.push({path,body:route.request().postDataJSON()});return json({id:11})}
  if(path==='/bookings'&&route.request().method()==='POST'){bookingCount++;if(mode==='conflict')return route.fulfill({status:409,json:{detail:'Conflict'}});return json({id:42,status:'pending'})}
  if(path==='/bookings/me')return json([{id:42,venue_name:venue.name,start_at:start,status:'pending'}]);
  if(path.startsWith('/photos/'))return mode==='photo-error'?route.fulfill({status:500,body:''}):route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540"><rect width="960" height="540" fill="#204f36"/></svg>'});
  if(path.includes('/availability')){if(mode==='slot-error')return route.fulfill({status:500,json:{}});return json({hours:'08:00–23:00',slots:[{start_at:start,label:'20:00',status:mode==='conflict'?'booked':'available'}]})}
  if(path==='/venues'){
   if(mode==='error')return route.fulfill({status:500,json:{}});
   if(url.searchParams.has('available_at')){searchCount++;if(mode==='slow-search')await new Promise(r=>setTimeout(r,700));if(mode==='search-error')return route.fulfill({status:500,json:{}})}
   if(mode==='slow')await new Promise(r=>setTimeout(r,700));
   return json(mode==='empty'?[]:[mode==='gallery'?{...venue,photos:[1,2]}:mode==='photo-error'?{...venue,photos:[1]}:mode==='long'?{...venue,name:'Uzun nomli sport majmuasi '.repeat(5),address:'Juda uzun manzil '.repeat(12),sport:'table_tennis'}:venue]);
  }
  return json({});
 });
 const results=[];
 async function home(query=''){await page.goto(`http://127.0.0.1:${port}/${query}`,{waitUntil:'domcontentloaded'});}
 async function noOverflow(){assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'horizontal overflow')}
 async function shot(name){await page.screenshot({path:new URL(name+'.png',output).pathname,fullPage:true})}
 async function audit(name){await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});const result=await page.evaluate(()=>window.axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}}));results.push({name,violations:result.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))});}
 for(const width of [360,390,430,768,1280]){
  await page.setViewportSize({width,height:844});await home();await page.locator('.venue-card').waitFor();await noOverflow();const firstCardTop=await page.locator('.venue-card').evaluate(e=>e.getBoundingClientRect().top);if(width===390)assert(firstCardTop<768,'first card must start above mobile navigation');await shot(`after-${width}`);results.push({width,firstCardTop,overflow:false});
 }
 await audit('home-desktop');await page.setViewportSize({width:390,height:844});await audit('home');
 // Real keyboard focus and named controls, with programmatic pressed states for screen readers.
 await page.keyboard.press('Tab');assert(await page.locator(':focus').count());
 assert(await page.getByRole('button',{name:'Barchasi',exact:true}).getAttribute('aria-pressed')==='true');
 for(const button of await page.locator('.chips button,.quick-times button,.map-toggle,.nearby-filter,.profile-button,.bottom-nav button').all()){const box=await button.boundingBox();assert(box.width>=44&&box.height>=44,`small touch target: ${await button.innerText()}`)}
 // Refresh retains card position; old availability is not presented as confirmed.
 mode='slow-search';await page.getByRole('button',{name:'Ertaga 20:00',exact:true}).click();await page.locator('.venue-card:not(:disabled)').waitFor();const before=await page.locator('.venue-card').evaluate(e=>e.getBoundingClientRect().top+scrollY);await page.getByRole('button',{name:'Yangilash',exact:true}).click();await page.locator('.venue-card:disabled').waitFor();assert.match(await page.locator('.venue-slot').innerText(),/Tekshirilmoqda/);const during=await page.locator('.venue-card').evaluate(e=>e.getBoundingClientRect().top+scrollY);assert(Math.abs(during-before)<1,`refresh layout shift: ${before} → ${during}`);await page.locator('.venue-card:not(:disabled)').waitFor();mode='normal';
 await page.locator('.venue-card').click();await page.locator('.booking-summary').waitFor();assert.match(await page.locator('.booking-summary').innerText(),/20:00–21:00/);assert.match(await page.getByRole('link',{name:'Telegramda bron qilish'}).getAttribute('href'),/start=book_1_\d+/);await audit('booking-login');await shot('detail-390');
 // Return from bot carries venue and selected slot.
 await home(`?venue=1&slot=${Date.parse(start)/1000}`);await page.locator('.booking-summary').waitFor();assert.match(await page.locator('.booking-summary').innerText(),/20:00/);
 // Signed Telegram UI test double, including contact and actual request payload.
 await page.evaluate(()=>sessionStorage.setItem('test-auth','test-only'));await home(`?venue=1&slot=${Date.parse(start)/1000}`);await page.locator('.booking-contact').waitFor();await page.locator('.booking-summary').waitFor();assert.match(await page.getByRole('link',{name:'Bot orqali ulashish'}).getAttribute('href'),/start=phone_1_\d+/);await page.getByRole('button',{name:'Telefon raqamimni ulashish'}).click();contact=true;await page.getByRole('button',{name:'Bron soʻrovi yuborish',exact:true}).waitFor();await audit('booking-contact');await page.getByRole('button',{name:'Bron soʻrovi yuborish',exact:true}).click();await page.getByRole('heading',{name:venue.name,exact:true}).waitFor();assert.equal(bookingCount,1);await audit('pending-booking');
 // A 409 invalidates the selection and reloads the calendar.
 await home(`?venue=1&slot=${Date.parse(start)/1000}`);await page.locator('.booking-summary').waitFor();mode='conflict';await page.getByRole('button',{name:'Bron soʻrovi yuborish',exact:true}).click();await page.getByText('Bu vaqt hozirgina band qilindi.',{exact:false}).waitFor();await page.locator('.time-grid button.booked').waitFor();assert.equal(await page.locator('.booking-summary').count(),0);await audit('booking-conflict');
 for(const state of ['empty','error','long','slow','search-error','photo-error']){mode=state;await home(state==='search-error'?`?day=${tomorrow}&time=20:00`:'');if(state==='slow'){await page.getByRole('status',{name:'Yuklanmoqda',exact:true}).waitFor();await shot('loading-390');await page.locator('.venue-card').waitFor()}else if(state==='empty')await page.getByRole('heading',{name:'Birinchi maydonni kutyapmiz'}).waitFor();else if(state==='error')await page.getByRole('heading',{name:'Maydonlar yuklanmadi'}).waitFor();else if(state==='search-error')await page.getByRole('heading',{name:'Vaqtlarni tekshirib boʻlmadi'}).waitFor();else if(state==='photo-error')await page.getByText('Rasm mavjud emas',{exact:true}).waitFor();else await page.locator('.sport-placeholder').waitFor();await noOverflow();await audit(state);await shot(`${state}-390`)}
 mode='gallery';await home('?venue=1');await page.locator('.detail-gallery img').nth(1).waitFor();await page.getByRole('group',{name:'Maydon rasmlari — yon tomonga suring'}).focus();await audit('gallery-scroll');await shot('gallery-390');mode='normal';await home();await page.locator('.venue-card').waitFor();await page.addStyleTag({content:'html{font-size:200%} button,input,select,p,h1,h2,h3,span,label{font-size:1rem!important}'});await noOverflow();await shot('text-large-390');
 await home('?owner=1');await page.getByRole('heading',{name:'Boshqaruv paneli'}).waitFor();await page.locator('.owner-slot').waitFor();await audit('owner-schedule');await shot('owner-390');await page.getByRole('button',{name:/Yangi soʻrovlar/}).click();await page.getByRole('button',{name:'Tasdiqlash',exact:true}).waitFor();assert.equal(await page.locator('select[name=status]').inputValue(),'pending');await audit('owner-pending');await shot('owner-pending-390');
 await page.getByRole('button',{name:'Jadval',exact:true}).click();await page.getByRole('button',{name:'Vaqtni yopish',exact:true}).click();await page.locator('.owner-slot').click();assert.equal(await page.locator('.owner-slot-editor select').inputValue(),'block');await page.locator('.owner-slot-editor input[name=reason]').fill('Test yopish');await audit('owner-block-editor');await shot('owner-block-390');await page.locator('.owner-slot-editor .primary').click();await page.getByText('Vaqt yopildi.',{exact:true}).waitFor();assert.equal(ownerBookings.at(-1).path,'/owner/blocks');
 await page.getByRole('button',{name:'+ Qoʻlda bron',exact:true}).click();await page.locator('.owner-slot').click();await page.locator('input[name=customer_name]').fill('Sinov mijoz');await page.locator('input[name=customer_phone]').fill('+998900000001');await audit('owner-manual-editor');await page.locator('.owner-slot-editor .primary').click();await page.getByText('Bron saqlandi.',{exact:true}).waitFor();assert.equal(ownerBookings.at(-1).path,'/owner/manual-bookings');
 await page.setViewportSize({width:360,height:844});await noOverflow();await shot('owner-360');await page.setViewportSize({width:1280,height:900});await shot('owner-1280');await noOverflow();await home();await page.locator('.venue-card').waitFor();await page.setViewportSize({width:390,height:360});await page.getByRole('textbox',{name:'Maydon qidirish'}).focus();await noOverflow();assert.equal(await page.locator('.bottom-nav').evaluate(e=>getComputedStyle(e).position),'static');await shot('keyboard-short-viewport');
 await writeFile(new URL('check-results.json',output),JSON.stringify({checkedAt:new Date().toISOString(),environment:'Local Vite + controlled API/Telegram test doubles; not a real Telegram device',checks:['all viewports','44px primary targets','keyboard focus','no horizontal overflow at enlarged text','refresh position stable and no stale available label','bot return venue and slot','contact sharing','pending booking','409 invalidation','owner pending shortcut','manual booking and blocking'],results},null,2));
 const violations=results.filter(r=>r.violations?.length);assert.deepEqual(violations,[],'WCAG audit failures: '+JSON.stringify(violations));console.log(`PASS: design acceptance, ${results.length} checks/audits`);
} finally {await browser?.close();server.kill('SIGTERM');}
