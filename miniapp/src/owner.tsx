import React, {useEffect, useRef, useState} from 'react';
import {ImagePlus} from 'lucide-react';

export const AMENITIES = [
 ['changing_room','Kiyim almashtirish xonasi'],['shower','Dush'],['stands','Tribuna'],['lighting','Yoritish uskunalari'],
 ['parking','Avtoturargoh'],['toilet','Hojatxona'],['drinking_water','Ichimlik suvi'],['equipment_rental','Sport anjomlari ijarasi'],
 ['wifi','Wi-Fi'],['cafe','Kafe / bufet'],['covered_field','Yopiq maydon'],['lockers','Buyumlar uchun shkaflar'],
] as const;
export function VenueAmenities({amenities=[],extra_amenities=''}:{amenities?:string[];extra_amenities?:string}) {
 const available=AMENITIES.filter(([value])=>amenities.includes(value));
 return available.length||extra_amenities?<section className="venue-amenities"><h3>Qulayliklar</h3><ul>{available.map(([value,label])=><li key={value}>{label}</li>)}</ul>{extra_amenities&&<p className="extra-amenities">{extra_amenities}</p>}</section>:null;
}

export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const authHeaders = () => ({'X-Telegram-Init-Data': window.Telegram?.WebApp?.initData || ''});
export const directions = (lat:number, lon:number) => `https://yandex.com/maps/?rtext=~${lat},${lon}&rtt=auto`;
// Map previews use longitude,latitude; routing uses latitude,longitude.
export const mapLocation = (lat:number, lon:number) => `https://yandex.com/maps/?${new URLSearchParams({ll:`${lon},${lat}`,pt:`${lon},${lat}`,z:'18',l:'map'})}`;

export function PhotoGallery({ids=[],fallback}:{ids?:number[];fallback?:React.ReactNode}) {
 const track=useRef<HTMLDivElement>(null);
 const [index,setIndex]=useState(0);
 function show(next:number){
  const row=track.current;
  const slide=row?.children[next] as HTMLElement|undefined;
  if(row && slide)row.scrollLeft+=slide.getBoundingClientRect().left-row.getBoundingClientRect().left;
 }
 return <div className="venue-gallery">
  <div className="photos" ref={track} onScroll={()=>{
   const row=track.current;
   if(row?.clientWidth)setIndex(Math.round(row.scrollLeft/row.clientWidth));
  }}>{ids.map(id=><div className="gallery-slide" key={id}><PitchPhoto id={id} fallback={fallback}/></div>)}</div>
  {ids.length>1&&<div className="gallery-controls">
   <button type="button" aria-label="Oldingi rasm" onClick={()=>show((index+ids.length-1)%ids.length)}>‹</button>
   <span>{Math.min(index+1,ids.length)}/{ids.length}</span>
   <button type="button" aria-label="Keyingi rasm" onClick={()=>show((index+1)%ids.length)}>›</button>
  </div>}
 </div>;
}
function PitchPhoto({id,fallback}:{id:number;fallback?:React.ReactNode}) {
 const [url,setUrl]=useState('');const [failed,setFailed]=useState(false);
 useEffect(()=>{setUrl('');setFailed(false);let active=true;let objectUrl='';const abort=new AbortController();
  fetch(`${API}/photos/${id}`,{headers:authHeaders(),signal:abort.signal}).then(r=>{if(!r.ok)throw Error();return r.blob()}).then(blob=>{if(active){objectUrl=URL.createObjectURL(blob);setUrl(objectUrl)}}).catch(()=>{if(active&&!abort.signal.aborted)setFailed(true)});
  return()=>{active=false;abort.abort();if(objectUrl)URL.revokeObjectURL(objectUrl)};
 },[id]);
 if(fallback && (failed || !url))return <div className="gallery-fallback">{fallback}<span className="sr-only">{failed?'Rasm mavjud emas':'Rasm yuklanmoqda…'}</span></div>;
 return failed?<span className="photo-unavailable">Rasm mavjud emas</span>:url?<img src={url} onError={()=>setFailed(true)} alt="Maydon rasmi"/>:<span role="status">Rasm yuklanmoqda…</span>;
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
export type OwnerVenue=Location & {id:number;name:string;sport:string;price:number;phone:string;hours:string;photos?:number[];amenities?:string[];extra_amenities?:string};
function LocationPicker({onChange,initial}:{onChange:(value:Location|null)=>void;initial?:Location}) {
 const element=useRef<HTMLDivElement>(null);const map=useRef<any>();const marker=useRef<any>();
 const [location,setLocation]=useState<Location|null>(initial?{latitude:initial.latitude,longitude:initial.longitude,address:initial.address}:null);const [error,setError]=useState('');const [gps,setGps]=useState(false);
 const generation=useRef(0);const active=useRef(true);const callback=useRef(onChange);callback.current=onChange;
 const selectedCoords=useRef<number[]|null>(initial?[initial.latitude,initial.longitude]:null);
 const select=useRef((coords:number[])=>{});
 function showPin(coords:number[]){
  if(!map.current||!window.ymaps)return;
  if(marker.current)marker.current.geometry.setCoordinates([...coords]);
  else{marker.current=new window.ymaps.Placemark([...coords],{}, {draggable:true});map.current.geoObjects.add(marker.current);marker.current.events.add('dragend',()=>select.current(marker.current.geometry.getCoordinates()));}
  map.current.setCenter([...coords],17);
 }
 select.current=async(coords:number[])=>{
  const version=++generation.current;const [latitude,longitude]=coords;
  selectedCoords.current=[latitude,longitude];setGps(false);
  const picked={latitude,longitude,address:`Xaritadagi joy: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}`};
  setLocation(picked);callback.current(picked);setError('');
  if(map.current&&window.ymaps){
   showPin([latitude,longitude]);
   try {const result=await window.ymaps.geocode(coords);const address=result.geoObjects.get(0)?.getAddressLine();
    if(active.current&&version===generation.current&&address){const resolved={...picked,address};setLocation(resolved);callback.current(resolved);}
   } catch {/* The selected coordinates remain usable without geocoding. */}
  }
 };
 useEffect(()=>{active.current=true;let observer:ResizeObserver|undefined;loadMaps().then(ymaps=>{if(!active.current||!element.current)return;
  map.current=new ymaps.Map(element.current,{center:[41.0011,71.6726],zoom:12,controls:['zoomControl']});
  observer=new ResizeObserver(()=>map.current?.container.fitToViewport());observer.observe(element.current);
  map.current.events.add('click',(event:any)=>select.current(event.get('coords')));
  if(selectedCoords.current)showPin(selectedCoords.current);
 }).catch(e=>{if(active.current)setError(e.message)});
 return()=>{active.current=false;generation.current++;observer?.disconnect();map.current?.destroy()};},[]);
 function locate(){if(!navigator.geolocation){setError('GPS mavjud emas. Xaritadan nuqta tanlang.');return;}
  const version=++generation.current;
  setGps(true);navigator.geolocation.getCurrentPosition(p=>{if(!active.current||version!==generation.current)return;setGps(false);select.current([p.coords.latitude,p.coords.longitude]);},()=>{if(!active.current||version!==generation.current)return;setGps(false);setError('Joylashuvga ruxsat bering yoki xaritada maydonni bosing.');},{enableHighAccuracy:true,timeout:15000,maximumAge:0});
 }
 return <div className="location-picker"><h4>Maydon joylashuvi</h4><p>Maydonning kirish joyini xaritada bosing yoki maydonda turgan holda GPSdan foydalaning.</p>
  <button type="button" className="setting full" disabled={gps} onClick={locate}>{gps?'Joylashuv aniqlanmoqda…':'📍 Hozirgi joylashuvim'}</button>
  <div ref={element} className="location-map" aria-label="Maydon joylashuvini tanlash xaritasi"/>
  {error&&<p role="status">{error}</p>}{location&&<><p>{location.address}</p><a href={mapLocation(location.latitude,location.longitude)} target="_blank" rel="noreferrer">Tanlangan nuqtani xaritada koʻrish ↗</a>
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

export function OwnerForm({onSaved,onExpired,initial,onCancel,invite}:{invite?:string;onSaved:()=>void;onExpired:()=>void;initial?:OwnerVenue;onCancel?:()=>void}) {
 const [kept,setKept]=useState<number[]>(initial?.photos||[]);
 const [location,setLocation]=useState<Location|null>(initial?{latitude:initial.latitude,longitude:initial.longitude,address:initial.address}:null);const [photos,setPhotos]=useState<string[]>([]);const [busy,setBusy]=useState(false);const [processing,setProcessing]=useState(false);const [error,setError]=useState('');const [saved,setSaved]=useState(false);
 async function submit(event:React.FormEvent<HTMLFormElement>){event.preventDefault();
  if(busy||processing)return;
  const form=event.currentTarget;
  if(!form.checkValidity()){setError('Majburiy maydonlarni toʻldiring va maydonni boshqarishga ruxsatingiz borligini belgilang.');form.reportValidity();return;}
  if(!location){setError('Maydon joylashuvini xaritada bosing yoki “Hozirgi joylashuvim” tugmasidan foydalaning.');return;}
  if(!photos.length&&!kept.length){setError('Maydonning kamida bitta rasmini yuklang.');return;}
  const data=new FormData(form);setBusy(true);setError('');
  try{const response=await fetch(invite?`${API}/venue-invites/${invite}/submit`:initial?`${API}/owner/venues/${initial.id}/edit`:`${API}/venues`,{method:'POST',headers:{'Content-Type':'application/json',...authHeaders()},body:JSON.stringify({...Object.fromEntries(data.entries()),price:Number(data.get('price')),amenities:data.getAll('amenities'),...location,photos,...(initial?{keep_photos:kept}:{})})});
   if(response.status===401){onExpired();throw Error('Kirish muddati tugadi. Ilovani Telegramdan qayta oching.');}
   if(!response.ok){const body=await response.json();throw Error(typeof body.detail==='string'?body.detail:'Maʼlumotlarni tekshiring.');}
   setSaved(true);onSaved();
  }catch(e){setError(e instanceof Error?e.message:'Yuborilmadi. Qayta urinib koʻring.')}finally{setBusy(false)}
 }
 if(saved)return <div className="setting" role="status"><h4>✓ Ariza yuborildi</h4><p>Maydoningiz va rasmlaringiz admin tekshiruvida. Tasdiqlangandan keyin ommaga koʻrinadi.</p>{!invite&&<button onClick={()=>{setSaved(false);setPhotos([]);setLocation(null)}}>Yana maydon qoʻshish</button>}</div>;
 return <form onSubmit={submit} noValidate><fieldset disabled={busy}><h4>{initial?'Maydonni tahrirlash':'Yangi maydon qoʻshish'}</h4>{initial&&<><p>Oʻzgarishlar admin tekshiruviga yuboriladi. Mavjud bronlar saqlanadi.</p><button type="button" className="back" onClick={onCancel}>Tahrirni bekor qilish</button></>}
  {!initial&&!invite&&<label>Maydon egasining Telegram ID raqami<input name="owner_telegram_id" inputMode="numeric" pattern="[1-9][0-9]*" required/></label>}
  <label>Maydon nomi<input name="name" defaultValue={initial?.name} required minLength={2} maxLength={120}/></label>
  <label>Sport<select name="sport" defaultValue={initial?.sport||'football'}><option value="football">Futbol</option><option value="table_tennis">Stol tennisi</option><option value="billiards">Bilyard</option></select></label>
  <label>Bir soat narxi (soʻm)<input name="price" defaultValue={initial?.price} type="number" min={0} max={100000000} step={1} required/></label>
  <label>Aloqa telefoni<input name="phone" defaultValue={initial?.phone} type="tel" maxLength={40} required/></label>
  <label>Ish vaqti<input name="hours" defaultValue={initial?.hours} placeholder="08:00–23:00 yoki 24/7" maxLength={120} required/></label>
  <fieldset className="amenities-picker"><legend>Maydon qulayliklari</legend><p>Mavjud qulayliklarni belgilang.</p><div className="amenities-grid">{AMENITIES.map(([value,label])=><label key={value}><input type="checkbox" name="amenities" value={value} defaultChecked={initial?.amenities?.includes(value)}/>{label}</label>)}</div>
   <label>Boshqa qulayliklar<textarea name="extra_amenities" defaultValue={initial?.extra_amenities} maxLength={500} rows={3} placeholder="Masalan: bolalar uchun joy, isitiladigan xona. Pullik xizmatlar bo‘lsa, narxini ham yozing."/></label>
  </fieldset>
  <LocationPicker onChange={setLocation} initial={initial}/>
  <label className="upload-label">Maydon rasmlari (1–5 ta)<span className="upload-zone"><ImagePlus size={29}/><strong>{processing?'Rasmlar tayyorlanmoqda…':'Rasmlarni tanlang'}</strong><small>JPEG, PNG yoki WebP · 10 MB gacha</small><input aria-label="Maydon rasmlarini tanlash" type="file" accept="image/jpeg,image/png,image/webp" multiple disabled={processing} onChange={async event=>{
   const files=Array.from(event.target.files||[]);event.target.value='';if(!files.length)return;
   if(kept.length+photos.length+files.length>5){setError('Koʻpi bilan 5 ta rasm tanlang.');return;}setProcessing(true);setError('');
   try{const next:string[]=[];for(const file of files)next.push(await resizePhoto(file));setPhotos(old=>[...old,...next]);}catch(e){setError(e instanceof Error?e.message:'Rasm yuklanmadi.')}finally{setProcessing(false)}
  }}/></span></label><p>Maydonning umumiy koʻrinishi, kirish joyi va oʻyin hududini koʻrsating. Shaxsiy hujjatlarni yuklamang. Rasmlar tasdiqlangach eʼlonda koʻrinadi.</p>
  <div className="photos">{kept.map(id=><div key={id}><PitchPhoto id={id}/><button type="button" onClick={()=>setKept(old=>old.filter(value=>value!==id))}>Oʻchirish</button></div>)}{photos.map((photo,index)=><div key={index}><img src={`data:image/jpeg;base64,${photo}`} alt={`Maydon rasmi ${index+1}`}/><button type="button" disabled={processing} onClick={()=>setPhotos(old=>old.filter((_,i)=>i!==index))}>Oʻchirish</button></div>)}</div>
  <p role="status">{location?'✓ Joylashuv tanlandi':'○ Xaritadan yoki GPS orqali joylashuvni tanlang'} · {photos.length+kept.length?`✓ ${photos.length+kept.length} ta rasm tayyor`:'○ Kamida bitta rasm yuklang'}</p>
  <label className="consent"><input type="checkbox" required/>Bu maydonni boshqarishga va ushbu rasmlarni joylashga ruxsatim bor.</label>
  {error&&<p role="alert">{error}</p>}
  <button className="primary" disabled={busy||processing}>{busy?'Yuborilmoqda…':processing?'Rasmlar tayyorlanmoqda…':initial?'Oʻzgarishlarni yuborish':'Admin tekshiruviga yuborish'}</button>
 </fieldset></form>;
}

export function OwnerVenueActions({venue,onEdit,onDeleted}:{venue:OwnerVenue;onEdit:()=>void;onDeleted:()=>void}){
 const [confirm,setConfirm]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function remove(){setBusy(true);setError('');try{
  const response=await fetch(`${API}/owner/venues/${venue.id}/delete`,{method:'POST',headers:authHeaders()});
  if(!response.ok){const body=await response.json();throw Error(typeof body.detail==='string'?body.detail:'Maydon oʻchirilmadi.');}
  onDeleted();
 }catch(e){setError(e instanceof Error?e.message:'Qayta urinib koʻring.')}finally{setBusy(false)}}
 return <div className="venue-actions">{!confirm?<div className="decision-actions"><button onClick={onEdit}>Tahrirlash</button><button onClick={()=>setConfirm(true)}>Oʻchirish</button></div>:<div className="delete-confirm" role="alertdialog" aria-label="Maydonni oʻchirish"><p><strong>{venue.name}</strong> eʼlonini oʻchirmoqchimisiz? Bronlar tarixi saqlanadi. Faol kelgusi bronlar boʻlsa, oʻchirish mumkin emas.</p><div className="decision-actions"><button disabled={busy} onClick={()=>{setConfirm(false);setError('')}}>Bekor qilish</button><button disabled={busy} onClick={remove}>{busy?'Oʻchirilmoqda…':'Ha, oʻchirish'}</button></div></div>}{error&&<p role="alert">{error}</p>}</div>;
}
