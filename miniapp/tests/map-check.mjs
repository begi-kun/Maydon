import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {chromium} from 'playwright';
const server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5193'],{stdio:'ignore',env:{...process.env,VITE_API_URL:'http://127.0.0.1:8009'}});let browser;
try{
 for(let i=0;i<80;i++){try{if((await fetch('http://127.0.0.1:5193')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page=await browser.newPage({viewport:{width:1280,height:900}});page.setDefaultTimeout(10000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('https://fonts.googleapis.com/**',r=>r.abort());await page.route('https://telegram.org/**',r=>r.abort());
 const venues=[{id:1,name:'Arena one',sport:'football',latitude:41,longitude:71.67,price:150000,address:'Namangan',photos:[],hours:'08:00–23:00'}, {id:2,name:'Arena two',sport:'billiards',latitude:41.01,longitude:71.68,price:50000,address:'Davlatobod',photos:[],hours:'24/7'}];
 await page.route('http://127.0.0.1:8009/**',r=>r.fulfill({json:r.request().url().includes('/availability')?{slots:[],hours:'24/7'}:r.request().url().includes('/venues')?venues:r.request().url().includes('/config')?{bot_username:'test_bot'}:{}}));
 await page.addInitScript(()=>{
  class Events{handlers={};add(k,f){(this.handlers[k]??=[]).push(f)}fire(k,e={}){for(const f of this.handlers[k]||[])f(e)}}
  class Marker{constructor(coords,props){this.coords=coords;this.properties={get:k=>props[k]};this.events=new Events()}}
  class Cluster{items=[];events=new Events();add(items){this.items=items}removeAll(){this.items=[]}getBounds(){return [[40.99,71.66],[41.02,71.69]]}}
  class Map{events=new Events();area=[[40.99,71.66],[41.02,71.69]];container={fitToViewport(){}};geoObjects={add:c=>{this.cluster=c}};constructor(){window.__map=this;window.__mapCreates=(window.__mapCreates||0)+1}getBounds(){return this.area}setBounds(b){this.area=b;this.events.fire('boundschange')}panTo(){return Promise.resolve()}destroy(){}}
  window.ymaps={ready:f=>f(),Map,Clusterer:Cluster,Placemark:Marker};
 });
 console.log('Opening app');await page.goto('http://127.0.0.1:5193',{waitUntil:'domcontentloaded'});console.log('Opening map');await page.locator('.map-toggle').click();await page.locator('.map-result').nth(1).waitFor();
 await page.locator('.map-result').first().click();await page.locator('.map-preview').waitFor();assert.match(await page.locator('.map-preview').innerText(),/Arena one/);
 await page.evaluate(()=>window.__map.cluster.items[1].events.fire('click'));assert.match(await page.locator('.map-preview').innerText(),/Arena two/);
 await page.evaluate(()=>{window.__map.area=[[40.99,71.66],[41.005,71.675]];window.__map.events.fire('boundschange')});await page.waitForTimeout(250);assert.equal(await page.locator('.map-result').count(),1);
 await page.getByRole('button',{name:'Barcha maydonlarni koʻrsatish',exact:true}).click();await page.waitForTimeout(250);assert.equal(await page.locator('.map-result').count(),2);
 await page.evaluate(()=>window.__map.cluster.events.fire('click',{get:()=>({properties:{get:()=>window.__map.cluster.items}})}));await page.getByRole('heading',{name:'Guruhdagi maydonlar'}).waitFor();assert.equal(await page.evaluate(()=>window.__mapCreates),1);
 for(const width of [360,390,1280]){await page.setViewportSize({width,height:900});await page.waitForTimeout(200);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}`);await page.screenshot({path:`/tmp/maydon-map-${width}.png`,fullPage:true})}
 await page.locator('.map-result').nth(1).click();await page.locator('.map-preview .primary').click();await page.locator('.detail-heading').waitFor();assert.match(await page.locator('.detail-heading').innerText(),/Arena two/);assert.deepEqual(errors,[]);
 console.log('PASS: map/list and marker selection, viewport filtering, cluster selection, show all, stable map, mobile/desktop overflow, detail navigation. Yandex SDK mocked.');
}finally{await browser?.close();server.kill()}
