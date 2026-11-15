/** Controlled browser acceptance; no real Telegram requests or messages. */
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {access} from 'node:fs/promises';
import {chromium} from 'playwright';
const port=5188,api='http://127.0.0.1:8010';
const server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port)],{cwd:new URL('..',new URL('.',import.meta.url)),env:{...process.env,VITE_API_URL:api},stdio:'ignore'});
let browser;
try{
 for(let i=0;i<80;i++){try{if((await fetch(`http://127.0.0.1:${port}`)).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 const executablePath=process.env.CHROME_PATH||await access('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome').then(()=>'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome').catch(()=>undefined);
 browser=await chromium.launch({executablePath,headless:true});
 for(const width of [390,1280]){
  const context=await browser.newContext({viewport:{width,height:1000},timezoneId:'America/Los_Angeles'});
  await context.addInitScript(()=>{window.Telegram={WebApp:{ready(){},expand(){},initData:'test-signed-session'}}});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const day=new Date(Date.now()+2*86400000).toISOString().slice(0,10);
  const start=`${day}T10:00:00+05:00`;
  const venue={id:1,name:'Pilot maydoni',sport:'football',address:'Namangan',price:100000,hours:'08:00–23:00',photos:[],latitude:41,longitude:71,status:'approved',suspended:false};
  let subscriptions=[],events=[],saved=[],recurring=[];
  const slots=[0,1,2,3].map(i=>{const date=new Date(`${day}T10:00:00+05:00`);date.setUTCDate(date.getUTCDate()+i*7);const d=new Date(date.getTime()+5*3600000).toISOString().slice(0,10);return {day:d,start_at:`${d}T10:00:00+05:00`,available:i!==1,reason:i===1?'booked':null,price:100000}});
  await page.route('https://telegram.org/**',r=>r.abort());await page.route('https://fonts.googleapis.com/**',r=>r.abort());
  await page.route(`${api}/**`,async route=>{
   const req=route.request(),path=new URL(req.url()).pathname;
   const json=data=>route.fulfill({json:data});
   if(path==='/product/features')return json({recurring_bookings:true,availability_alerts:true});
   if(path==='/auth/config')return json({bot_username:'test_bot'});
   if(path==='/auth/me')return json({id:101,first_name:'Pilot egasi',admin:true});
   if(path==='/auth/contact')return json({phone:'+998900000001'});
   if(path==='/venues')return json([venue]);
   if(path==='/venues/1/availability')return json({hours:venue.hours,slots:[{start_at:start,label:'10:00',status:'booked'}]});
   if(path==='/discovery/events'){events.push({body:req.postDataJSON(),headers:req.headers()});return json({accepted:true})}
   if(path==='/availability-subscriptions'&&req.method()==='POST'){subscriptions=[{id:1,venue_id:1,venue_name:venue.name,start_at:start,queued_at:null}];return json({id:1})}
   if(path==='/availability-subscriptions')return json(subscriptions);
   if(path==='/availability-subscriptions/1/cancel'){subscriptions=[];return json({cancelled:true})}
   if(path==='/bookings/me')return json([]);
   if(path==='/owner/venues')return json([venue]);
   if(path==='/owner/overview')return json({today:0,pending:0,value:0,unpaid:0});
   if(path==='/owner/schedule')return json({hours:venue.hours,slots:[{start_at:start,status:'available',booking:null,block:null}]});
   if(path==='/owner/recurring-bookings/preview')return json({slots,has_conflicts:true});
   if(path==='/owner/recurring-bookings'){recurring.push(req.postDataJSON());return json({booking_ids:[11,12]})}
   if(path==='/owner/bookings')return json([{id:11,venue_name:venue.name,start_at:'2020-01-01T10:00:00+05:00',status:'confirmed',source:'manual',customer_name:'Pilot',customer_phone:null,payment_status:'unpaid',booked_price:100000,outcome:'no_show'}]);
   if(path==='/owner/bookings/11/outcome'){saved.push(req.postDataJSON());return json({outcome:'attended'})}
   if(path==='/admin/pilot')return json({from_date:day,to_date:day,searches:4,timed_searches:2,venue_opens:2,converted_searches:1,converted_timed_searches:1,timed_search_conversion:.5,unrecorded_outcomes:3,attributed_requests:1,booking_requests:3,unique_customers:2,cancellations:0,measured_decisions:1,mean_decision_seconds:30,second_week_returning_customers:1,outcomes:[{outcome:'no_show',count:1}],measurement_note:'Qidiruvlar mijozlar soni emas.'});
   return json({counts:{venues:0,bookings:0,notifications:0},venues:[],bookings:[]});
  });
  await page.goto(`http://127.0.0.1:${port}/?sport=football&q=Pilot&day=${day}&time=10:00&latitude=41&tgWebAppData=secret`);
  await page.locator('.venue-card').click();
  await page.getByRole('button',{name:'10:00 — band'}).click();
  await page.getByRole('button',{name:'Boʻshasa xabar bering',exact:true}).click();
  await page.getByText('Obuna saqlandi.',{exact:false}).waitFor();
  await page.getByRole('button',{name:'Bronlar',exact:true}).click();
  await page.getByRole('button',{name:'Obunani oʻchirish'}).click();await page.getByText('Faol obunalar yoʻq.').waitFor();
  assert(events.some(e=>e.body.event==='discovery_results'));assert(events.some(e=>e.body.event==='venue_open'));
  for(const e of events){assert(!e.headers['x-telegram-init-data']);assert.deepEqual(Object.keys(e.body).filter(k=>['phone','query','latitude','longitude','telegram_id','name'].includes(k)),[])}
  await page.getByRole('button',{name:'Profil',exact:true}).last().click();await page.getByRole('button',{name:'Maydon egasi paneli',exact:false}).click();
  await page.locator('.owner-slot.available').click();
  await page.getByText('Har hafta shu vaqtga bron',{exact:true}).click();
  const form=page.locator('section').filter({has:page.getByRole('heading',{name:'Har hafta shu vaqt',exact:true})}).last();
  await form.locator('input[name=customer_name]').fill('Pilot mijoz');await form.locator('input[name=customer_phone]').fill('+998900000001');await form.getByRole('button',{name:'Sanalarni tekshirish'}).click();
  const boxes=form.locator('input[type=checkbox]');await boxes.first().waitFor();assert.equal(await boxes.count(),4);assert(await boxes.nth(1).isDisabled());assert(await form.getByRole('button',{name:'0 ta bronni tasdiqlash'}).isDisabled());
  await boxes.nth(0).check();await boxes.nth(2).check();await form.getByRole('button',{name:'2 ta bronni tasdiqlash'}).click();await page.getByText('Takroriy bronlar saqlandi.').waitFor();assert.deepEqual(recurring[0].selected_dates,[slots[0].day,slots[2].day]);
  await page.getByRole('button',{name:'Bronlar va toʻlovlar',exact:true}).click();const select=page.getByLabel('Seans natijasi');await select.waitFor();assert.equal(await select.inputValue(),'no_show');await select.selectOption('attended');await page.getByRole('button',{name:'Natijani qayd qilish'}).click();await page.getByText('Natija qayd qilindi.').waitFor();assert.deepEqual(saved,[{outcome:'attended'}]);
  await page.getByRole('button',{name:'Profil',exact:true}).last().click();await page.getByRole('button',{name:'Admin paneli',exact:false}).click();await page.getByRole('button',{name:'Pilot',exact:true}).click();await page.getByRole('button',{name:'Hisobotni olish'}).click();await page.getByText('50.0%',{exact:true}).waitFor();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);
  console.log(`PASS ${width}px: private telemetry, subscription/cancel, explicit recurrence, recorded outcome, pilot report`);
  await context.close();
 }
}finally{await browser?.close();server.kill('SIGTERM')}
