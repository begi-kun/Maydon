import React, {useEffect, useRef, useState} from 'react';

export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const authHeaders = () => ({'X-Telegram-Init-Data': window.Telegram?.WebApp?.initData || ''});
export const directions = (lat:number, lon:number) => `https://yandex.com/maps/?rtext=~${lat},${lon}&rtt=auto`;

export function PhotoGallery({ids=[]}:{ids?:number[]}) {
 return <div className="photos">{ids.map(id=><PitchPhoto key={id} id={id}/>)}</div>;
}
function PitchPhoto({id}:{id:number}) {
 const [url,setUrl]=useState('');
 useEffect(()=>{let active=true;let objectUrl='';const abort=new AbortController();
  fetch(`${API}/photos/${id}`,{headers:authHeaders(),signal:abort.signal}).then(r=>{if(!r.ok)throw Error();return r.blob()}).then(blob=>{if(active){objectUrl=URL.createObjectURL(blob);setUrl(objectUrl)}}).catch(()=>{});
  return()=>{active=false;abort.abort();if(objectUrl)URL.revokeObjectURL(objectUrl)};
 },[id]);
 return url?<img src={url} alt="Maydon rasmi"/>:<span>Rasm yuklanmoqda…</span>;
}

let mapsPromise:Promise<any>|undefined;
export function loadMaps():Promise<any> {
 if(window.ymaps)return new Promise(resolve=>window.ymaps.ready(()=>resolve(window.ymaps)));
 if(mapsPromise)return mapsPromise;
 mapsPromise=new Promise((resolve,reject)=>{
  const key=import.meta.env.VITE_YANDEX_MAPS_KEY;
  if(!key){reject(Error('Xarita hozircha mavjud emas. GPS orqali joylashuvni tanlang.'));return;}
  const script=document.createElement('script');
  const timer=setTimeout(()=>reject(Error('Xarita yuklanmadi. GPS orqali joylashuvni tanlang.')),15000);
  script.src=`https://api-maps.yandex.ru/2.1/?apikey=${encodeURIComponent(key)}&lang=ru_RU`;
  script.onload=()=>window.ymaps?.ready(()=>{clearTimeout(timer);resolve(window.ymaps)});
  script.onerror=()=>{clearTimeout(timer);reject(Error('Xarita yuklanmadi. GPS orqali joylashuvni tanlang.'))};
  document.head.appendChild(script);
 });return mapsPromise;
}
type Location={latitude:number;longitude:number;address:string};
function LocationPicker({onChange}:{onChange:(value:Location|null)=>void}) {
 const element=useRef<HTMLDivElement>(null);const map=useRef<any>();const marker=useRef<any>();
 const [location,setLocation]=useState<Location|null>(null);const [error,setError]=useState('');const [gps,setGps]=useState(false);
 const generation=useRef(0);const active=useRef(true);const callback=useRef(onChange);callback.current=onChange;
 const select=useRef((coords:number[])=>{});
 select.current=async(coords:number[])=>{
  const version=++generation.current;const [latitude,longitude]=coords;
  const picked={latitude,longitude,address:`Xaritadagi joy: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}`};
  setLocation(picked);callback.current(picked);setError('');
  if(map.current&&window.ymaps){
   if(marker.current)marker.current.geometry.setCoordinates(coords);
   else{marker.current=new window.ymaps.Placemark(coords,{}, {draggable:true});map.current.geoObjects.add(marker.current);marker.current.events.add('dragend',()=>select.current(marker.current.geometry.getCoordinates()));}
   map.current.setCenter(coords,17);
   try {const result=await window.ymaps.geocode(coords);const address=result.geoObjects.get(0)?.getAddressLine();
    if(active.current&&version===generation.current&&address){const resolved={...picked,address};setLocation(resolved);callback.current(resolved);}
   } catch {/* The selected coordinates remain usable without geocoding. */}
  }
 };
 useEffect(()=>{active.current=true;loadMaps().then(ymaps=>{if(!active.current||!element.current)return;
  map.current=new ymaps.Map(element.current,{center:[41.0011,71.6726],zoom:12,controls:['zoomControl']});
  map.current.events.add('click',(event:any)=>select.current(event.get('coords')));
 }).catch(e=>{if(active.current)setError(e.message)});
 return()=>{active.current=false;generation.current++;map.current?.destroy()};},[]);
 function locate(){if(!navigator.geolocation){setError('GPS mavjud emas. Xaritadan nuqta tanlang.');return;}
  setGps(true);navigator.geolocation.getCurrentPosition(p=>{if(!active.current)return;setGps(false);select.current([p.coords.latitude,p.coords.longitude]);},()=>{if(!active.current)return;setGps(false);setError('Joylashuvga ruxsat bering yoki xaritada maydonni bosing.');},{enableHighAccuracy:true,timeout:15000,maximumAge:0});
 }
 return <div className="location-picker"><h4>Maydon joylashuvi</h4><p>Maydonning kirish joyini xaritada bosing yoki maydonda turgan holda GPSdan foydalaning.</p>
  <button type="button" className="setting full" disabled={gps} onClick={locate}>{gps?'Joylashuv aniqlanmoqda…':'📍 Hozirgi joylashuvim'}</button>
  <div ref={element} className="location-map" aria-label="Maydon joylashuvini tanlash xaritasi"/>
  {error&&<p role="status">{error}</p>}{location&&<><p>{location.address}</p><a href={directions(location.latitude,location.longitude)} target="_blank" rel="noreferrer">Xaritada tekshirish ↗</a>
  <p role="status">✓ Joylashuv tanlandi. Oʻzgartirish uchun xaritada boshqa joyni bosing.</p></>}
 </div>;
}

async function resizePhoto(file:File):Promise<string> {
 if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>10*1024*1024)throw Error('JPEG, PNG yoki WebP rasm tanlang (10 MB gacha).');
 const image=await createImageBitmap(file);
 try {if(Math.min(image.width,image.height)<200)throw Error('Rasm juda kichik (kamida 200 × 200).');
  const scale=Math.min(1,1600/Math.max(image.width,image.height));const canvas=document.createElement('canvas');canvas.width=Math.round(image.width*scale);canvas.height=Math.round(image.height*scale);
  canvas.getContext('2d')!.drawImage(image,0,0,canvas.width,canvas.height);
  const value=canvas.toDataURL('image/jpeg',0.8).split(',')[1];if(value.length>1400000)throw Error('Rasm juda katta. Boshqa rasm tanlang.');return value;
 }finally{image.close()}
}

export function OwnerForm({onSaved,onExpired}:{onSaved:()=>void;onExpired:()=>void}) {
 const [location,setLocation]=useState<Location|null>(null);const [photos,setPhotos]=useState<string[]>([]);const [busy,setBusy]=useState(false);const [processing,setProcessing]=useState(false);const [error,setError]=useState('');const [saved,setSaved]=useState(false);
 async function submit(event:React.FormEvent<HTMLFormElement>){event.preventDefault();
  if(busy||processing)return;
  const form=event.currentTarget;
  if(!form.checkValidity()){setError('Majburiy maydonlarni toʻldiring va maydonni boshqarishga ruxsatingiz borligini belgilang.');form.reportValidity();return;}
  if(!location){setError('Maydon joylashuvini xaritada bosing yoki “Hozirgi joylashuvim” tugmasidan foydalaning.');return;}
  if(!photos.length){setError('Maydonning kamida bitta rasmini yuklang.');return;}
  const data=new FormData(form);setBusy(true);setError('');
  try{const response=await fetch(`${API}/venues`,{method:'POST',headers:{'Content-Type':'application/json',...authHeaders()},body:JSON.stringify({...Object.fromEntries(data.entries()),price:Number(data.get('price')),...location,photos})});
   if(response.status===401){onExpired();throw Error('Kirish muddati tugadi. Ilovani Telegramdan qayta oching.');}
   if(!response.ok){const body=await response.json();throw Error(typeof body.detail==='string'?body.detail:'Maʼlumotlarni tekshiring.');}
   setSaved(true);onSaved();
  }catch(e){setError(e instanceof Error?e.message:'Yuborilmadi. Qayta urinib koʻring.')}finally{setBusy(false)}
 }
 if(saved)return <div className="setting" role="status"><h4>✓ Ariza yuborildi</h4><p>Maydoningiz va rasmlaringiz admin tekshiruvida. Tasdiqlangandan keyin ommaga koʻrinadi.</p><button onClick={()=>{setSaved(false);setPhotos([]);setLocation(null)}}>Yana maydon qoʻshish</button></div>;
 return <form onSubmit={submit} noValidate><fieldset disabled={busy}><h4>Yangi maydon qoʻshish</h4>
  <label>Maydon nomi<input name="name" required minLength={2} maxLength={120}/></label>
  <label>Sport<select name="sport"><option value="football">Futbol</option><option value="table_tennis">Stol tennisi</option><option value="billiards">Bilyard</option></select></label>
  <label>Bir soat narxi (soʻm)<input name="price" type="number" min={0} max={100000000} step={1} required/></label>
  <label>Aloqa telefoni<input name="phone" type="tel" maxLength={40} required/></label>
  <label>Ish vaqti<input name="hours" placeholder="Masalan: 08:00–23:00" maxLength={120} required/></label>
  <LocationPicker onChange={setLocation}/>
  <label>Maydon rasmlari (1–5 ta)<input type="file" accept="image/jpeg,image/png,image/webp" multiple disabled={processing} onChange={async event=>{
   const files=Array.from(event.target.files||[]);event.target.value='';if(!files.length)return;
   if(photos.length+files.length>5){setError('Koʻpi bilan 5 ta rasm tanlang.');return;}setProcessing(true);setError('');
   try{const next:string[]=[];for(const file of files)next.push(await resizePhoto(file));setPhotos(old=>[...old,...next]);}catch(e){setError(e instanceof Error?e.message:'Rasm yuklanmadi.')}finally{setProcessing(false)}
  }}/></label><p>Maydonning umumiy koʻrinishi, kirish joyi va oʻyin hududini koʻrsating. Shaxsiy hujjatlarni yuklamang. Rasmlar tasdiqlangach eʼlonda koʻrinadi.</p>
  <div className="photos">{photos.map((photo,index)=><div key={index}><img src={`data:image/jpeg;base64,${photo}`} alt={`Maydon rasmi ${index+1}`}/><button type="button" disabled={processing} onClick={()=>setPhotos(old=>old.filter((_,i)=>i!==index))}>Oʻchirish</button></div>)}</div>
  <p role="status">{location?'✓ Joylashuv tanlandi':'○ Xaritadan yoki GPS orqali joylashuvni tanlang'} · {photos.length?`✓ ${photos.length} ta rasm tayyor`:'○ Kamida bitta rasm yuklang'}</p>
  <label className="consent"><input type="checkbox" required/>Bu maydonni boshqarishga va ushbu rasmlarni joylashga ruxsatim bor.</label>
  {error&&<p role="alert">{error}</p>}
  <button className="primary" disabled={busy||processing}>{busy?'Yuborilmoqda…':processing?'Rasmlar tayyorlanmoqda…':'Admin tekshiruviga yuborish'}</button>
 </fieldset></form>;
}
