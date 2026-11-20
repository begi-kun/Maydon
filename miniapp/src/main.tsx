import {HourPicker} from './hour-picker';
import {recordDiscovery} from './discovery-events';
import {AvailabilitySubscriptions, useProductFeatures} from './product';
import {VenueAmenities} from './owner';
import {readDiscovery, discoveryLink, validDiscoveryTime} from './discovery';
import React, {useEffect, useMemo, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {House, Search, MapPin, UserRound, CalendarDays, ArrowUpRight, ArrowLeft, ArrowRight, Clock3, Phone, ShieldCheck, RefreshCw, X, Check, Compass, Goal, SlidersHorizontal, Send} from 'lucide-react';
import './style.css';
import {AdminPanel} from './admin';
import {OwnerPanel} from './owner-panel';
import {MapExplorer} from './map-explorer';
import {BookingPicker, localDate} from './booking';
import {PhotoGallery, directions, API, authHeaders} from './owner';

type Venue={amenities?:string[];extra_amenities?:string;photos?:number[];id:number;name:string;sport:string;address:string;latitude:number;longitude:number;price:number;phone:string;hours:string;status?:string;suspended?:boolean;review_reason?:string;owner_telegram_id?:number};
type Booking={venue_id:number;customer_phone?:string|null;id:number;venue_name:string;start_at:string;status:string};
type Tab='home'|'map'|'bookings'|'profile'|'owner'|'admin';
const sports=[['all','Barchasi'],['football','Futbol'],['table_tennis','Stol tennisi'],['billiards','Bilyard']];
const sportName=(sport:string)=>sports.find(([id])=>id===sport)?.[1]||sport;
const price=(amount:number)=>new Intl.NumberFormat('uz-UZ').format(amount);
const statusName:Record<string,string>={pending:'Kutilmoqda',approved:'Tasdiqlangan',confirmed:'Tasdiqlangan',rejected:'Rad etilgan',cancelled:'Bekor qilingan'};
declare global {interface Window {Telegram?:{WebApp?:{ready:()=>void;expand:()=>void;initData?:string;requestContact?:(callback:(shared:boolean)=>void)=>void;initDataUnsafe?:{user?:{id:number;first_name:string}}}};ymaps?:any}}
const initData=()=>window.Telegram?.WebApp?.initData||'';
function Status({value}:{value:string}){return <span className={`status status-${value}`}><i/>{statusName[value]||value}</span>}
function Empty({title,children,action}:{title:string;children:React.ReactNode;action?:React.ReactNode}){return <div className="empty"><div className="empty-icon"><Goal size={30}/></div><h3>{title}</h3><p>{children}</p>{action}</div>}
function VenueArt({sport}:{sport:string}){return sport==='football'?<PitchArt/>:<div className="sport-placeholder" aria-hidden="true"><img src={`/icons/${sport==='table_tennis'?'table-tennis':'billiards'}.svg`} alt=""/></div>}
function PitchArt(){return <div className="pitch-art" aria-hidden="true"><div className="pitch-lines"><i className="pitch-center"/><i className="pitch-box left"/><i className="pitch-box right"/></div></div>}
function AvailabilityPreview({venueId,day}:{venueId:number;day:string}){
 const [label,setLabel]=useState('');
 useEffect(()=>{
  const controller=new AbortController();
  async function refresh(){
   try {
    const response=await fetch(`${API}/venues/${venueId}/availability?day=${day}`,{signal:controller.signal});
    if(!response.ok)throw Error();
    const {slots}=await response.json();
    const available=slots.filter((slot:{status:string;start_at:string})=>slot.status==='available'&&Date.parse(slot.start_at)>Date.now()+300000);
    const tonight=available.find((slot:{label:string})=>slot.label>='18:00');
    const next=tonight||available[0];
    const prefix=day===localDate(new Date())?'Bugun':day.split('-').reverse().join('.');
    if(!controller.signal.aborted)setLabel(next?`${prefix} ${next.label} · Boʻsh`:`${prefix} · Boʻsh vaqt yoʻq`);
   }catch{if(!controller.signal.aborted)setLabel('')}
  }
  void refresh();
  const timer=window.setInterval(refresh,30000);
  return ()=>{controller.abort();window.clearInterval(timer)};
 },[venueId,day]);
 return label?<p className="venue-slot"><Clock3 size={14}/>{label}</p>:null;
}
function App(){
 const productFeatures=useProductFeatures();
 const mainRef=useRef<HTMLElement>(null);const navRef=useRef<HTMLElement>(null);
 useEffect(()=>{const nav=navRef.current;if(!nav)return;const resize=new ResizeObserver(()=>document.documentElement.style.setProperty('--nav-height',`${nav.getBoundingClientRect().height}px`));resize.observe(nav);return()=>resize.disconnect()},[]);
 const [tab,setTab]=useState<Tab>(() => { const params=new URLSearchParams(window.location.search); return params.has('admin')?'admin':params.has('owner')?'owner':'home' });
 const [initialDiscovery]=useState(()=>readDiscovery(window.location.search));
 const [sport,setSport]=useState(initialDiscovery.sport);const [query,setQuery]=useState(initialDiscovery.query);const [venues,setVenues]=useState<Venue[]>([]);
 const [selected,setSelected]=useState<Venue|null>(null);const [availabilityRevision,setAvailabilityRevision]=useState(0);const [message,setMessage]=useState('');
 const [venueError,setVenueError]=useState('');const [loading,setLoading]=useState(true);const [bookingBusy,setBookingBusy]=useState(false);
 const [isAdmin,setIsAdmin]=useState(false);const [verifiedUser,setVerifiedUser]=useState<{id:number;first_name:string}|null>(null);
 const [authLoading,setAuthLoading]=useState(!!initData());const [botUsername,setBotUsername]=useState('');const [myBookings,setMyBookings]=useState<Booking[]>([]);
 useEffect(()=>{window.Telegram?.WebApp?.ready();window.Telegram?.WebApp?.expand();loadVenues();},[]);
 useEffect(()=>{fetch(`${API}/auth/config`).then(r=>r.json()).then(v=>setBotUsername(v.bot_username||'')).catch(()=>{});if(initData())fetch(`${API}/auth/me`,{headers:authHeaders()}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(v=>{setVerifiedUser(v);setIsAdmin(v.admin)}).catch(()=>setMessage('Telegram orqali qayta kiring.')).finally(()=>setAuthLoading(false));},[]);
 const [filterNow,setFilterNow]=useState(Date.now);
 useEffect(()=>{const refresh=()=>setFilterNow(Date.now());const timer=window.setInterval(refresh,30000);window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh);return()=>{window.clearInterval(timer);window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh)}},[]);
 const today=localDate(new Date(filterNow));const maxDay=localDate(new Date(filterNow+60*86400000));
 function filterTimeDisabled(day:string,time:string,now=filterNow){return !validDiscoveryTime(day,time,now)}
 const [filterDay,setFilterDay]=useState(initialDiscovery.day||today);const [filterTime,setFilterTime]=useState(initialDiscovery.time);
 const [nearby,setNearby]=useState(false);const [position,setPosition]=useState<{latitude:number;longitude:number}|null>(null);const [locating,setLocating]=useState(false);const [locationError,setLocationError]=useState('');
 useEffect(()=>{let active=true;if(navigator.permissions&&navigator.geolocation)navigator.permissions.query({name:'geolocation'}).then(permission=>{if(active&&permission.state==='granted')navigator.geolocation.getCurrentPosition(p=>{if(active)setPosition({latitude:p.coords.latitude,longitude:p.coords.longitude})},()=>{},{timeout:12000,maximumAge:60000})}).catch(()=>{});return()=>{active=false}},[]);
 const [availabilityBusy,setAvailabilityBusy]=useState(false);
 const [availableIds,setAvailableIds]=useState<number[]>([]);const [availabilityKey,setAvailabilityKey]=useState('');const [searchError,setSearchError]=useState('');const [searchRetry,setSearchRetry]=useState(0);
 useEffect(()=>{if(filterDay<today){setFilterDay(today);setFilterTime('')}else if(filterTime&&filterTimeDisabled(filterDay,filterTime))setFilterTime('')},[filterNow,filterDay,filterTime,today]);
 const searchTime=filterTime&&filterDay>=today&&!filterTimeDisabled(filterDay,filterTime)?`${filterDay}T${filterTime}:00+05:00`:'';
 useEffect(()=>{if(!searchTime){setSearchError('');setAvailabilityBusy(false);return;}const controller=new AbortController();setSearchError('');setAvailabilityBusy(true);
  fetch(`${API}/venues?available_at=${encodeURIComponent(searchTime)}`,{signal:controller.signal}).then(async r=>{if(!r.ok)throw Error(r.status===422?'Kelajakdagi vaqtni tanlang (5 daqiqadan 60 kungacha).':'Vaqtlarni tekshirib boʻlmadi. Qayta urinib koʻring.');return r.json()}).then((list:Venue[])=>{if(!controller.signal.aborted){setAvailableIds(list.map(v=>v.id));setAvailabilityKey(searchTime)}}).catch(e=>{if(!controller.signal.aborted)setSearchError(e.message)}).finally(()=>{if(!controller.signal.aborted)setAvailabilityBusy(false)});
  return()=>controller.abort();
 },[searchTime,searchRetry,availabilityRevision,venues,filterNow]);
 const searchLoading=!!searchTime&&(availabilityBusy||availabilityKey!==searchTime)&&!searchError;
 function distance(v:Venue){if(!position)return 0;const rad=Math.PI/180;const a=Math.sin((v.latitude-position.latitude)*rad/2)**2+Math.cos(position.latitude*rad)*Math.cos(v.latitude*rad)*Math.sin((v.longitude-position.longitude)*rad/2)**2;return 6371*2*Math.asin(Math.sqrt(Math.min(1,a)))}
 function distanceLabel(v:Venue){const km=distance(v);return km<1?`${Math.max(10,Math.round(km*1000/10)*10)} m`:`${km.toLocaleString('uz-UZ',{maximumFractionDigits:1,minimumFractionDigits:1})} km`}
 function toggleNearby(){if(nearby){setNearby(false);return;}if(position){setNearby(true);return;}if(!navigator.geolocation){setLocationError('Qurilmangiz joylashuvni aniqlashni qoʻllamaydi.');return;}setLocating(true);setLocationError('');navigator.geolocation.getCurrentPosition(p=>{setPosition({latitude:p.coords.latitude,longitude:p.coords.longitude});setNearby(true);setLocating(false)},e=>{setLocating(false);setLocationError(e.code===1?'Yaqin maydonlarni koʻrish uchun joylashuvga ruxsat bering.':'Joylashuv aniqlanmadi. Qayta urinib koʻring.')},{timeout:12000,maximumAge:60000,enableHighAccuracy:true})}
 function clearFilters(){setQuery('');setSport('all');setFilterTime('');setFilterDay(today);setNearby(false);setLocationError('')}
 const hasFilters=!!query||sport!=='all'||!!filterTime||nearby;
 const shown=useMemo(()=>venues.filter(v=>(sport==='all'||v.sport===sport)&&`${v.name} ${v.address}`.toLocaleLowerCase().includes(query.toLocaleLowerCase().trim())&&(!searchTime||availabilityKey===searchTime&&availableIds.includes(v.id))).sort((a,b)=>nearby&&position?distance(a)-distance(b):0),[venues,sport,query,searchTime,availabilityKey,availableIds,nearby,position]);
 const discoveryId=useMemo(()=>crypto.randomUUID(),[sport,query,filterDay,filterTime,nearby]);
 const recordedSearch=useRef('');const discoveryPending=useRef<Promise<void>>(Promise.resolve());
 function recordResults(){if(loading||venueError||searchLoading||searchError||recordedSearch.current===discoveryId)return discoveryPending.current;recordedSearch.current=discoveryId;discoveryPending.current=recordDiscovery({search_id:discoveryId,event:'discovery_results',sport,day:searchTime?filterDay:null,hour:searchTime?Number(filterTime.slice(0,2)):null,result_count:shown.length});return discoveryPending.current}
 useEffect(()=>{const timer=window.setTimeout(recordResults,500);return()=>window.clearTimeout(timer)},[discoveryId,loading,venueError,searchLoading,searchError,shown.length]);
 useEffect(()=>{if(selected){recordResults();recordDiscovery({search_id:discoveryId,event:'venue_open',sport,day:searchTime?filterDay:null,hour:searchTime?Number(filterTime.slice(0,2)):null,venue_id:selected.id})}},[selected?.id]);
 function openVenue(venue:Venue){recordResults();setSelected(venue);window.scrollTo({top:0})}
 async function loadVenues(){setLoading(true);setVenueError('');try{const r=await fetch(`${API}/venues`);if(!r.ok)throw Error();const list=await r.json();setVenues(list);const venueId=Number(new URLSearchParams(window.location.search).get('venue'));if(venueId){const match=list.find((v:Venue)=>v.id===venueId);if(match)setSelected(match)}}catch{setVenueError('Maydonlarni yuklab boʻlmadi. Qayta urinib koʻring.')}finally{setLoading(false)}}
 function openBookedVenue(booking:Booking){const venue=venues.find(v=>v.id===booking.venue_id);if(venue){openVenue(venue)}else{setMessage('Bu maydon hozir mavjud emas. Boshqa maydonni tanlang.')}}
 async function loadBookings(){if(!initData())return;try{const r=await fetch(`${API}/bookings/me`,{headers:authHeaders()});if(!r.ok)throw Error();setMyBookings(await r.json())}catch{setMessage('Bronlarni yuklab boʻlmadi.')}}

 useEffect(()=>{mainRef.current?.focus({preventScroll:true})},[tab,selected?.id]);
 function navigate(next:Tab){
  const url=new URL(window.location.href);
  url.searchParams.delete('owner');
  url.searchParams.delete('admin');
  if(next==='owner'||next==='admin')url.searchParams.set(next,'1');
  window.history.replaceState(null,'',url);
  setTab(next);setSelected(null);if(next==='bookings')loadBookings();window.scrollTo({top:0,behavior:'smooth'})}
 async function decide(path:string,refresh:()=>void){try{const r=await fetch(`${API}${path}`,{method:'POST',headers:authHeaders()});if(!r.ok)throw Error();setAvailabilityRevision(n=>n+1);refresh()}catch{setMessage('Amal bajarilmadi. Qayta urinib koʻring.')}}
 async function book(time:string){
  if(!selected||!time)return;if(!verifiedUser){navigate('profile');return;}
  const date=new Date(time);
  setBookingBusy(true);try{await recordResults();const r=await fetch(`${API}/bookings`,{method:'POST',headers:{'Content-Type':'application/json',...authHeaders()},body:JSON.stringify({venue_id:selected.id,start_at:date.toISOString(),discovery_id:discoveryId})});
   if(!r.ok){if(r.status===409){setAvailabilityRevision(n=>n+1);throw Error('Bu vaqt hozirgina band qilindi. Yangilangan roʻyxatdan boshqa vaqtni tanlang.');}if(r.status===428)throw Error('Bron qilishdan oldin Telegram orqali telefon raqamingizni ulashing.');if(r.status===401)throw Error('Telegram orqali qayta kiring.');throw Error('Bron yuborilmadi. Kelajakdagi vaqtni tanlab, qayta urinib koʻring.');}
   setAvailabilityRevision(n=>n+1);setMessage('Bron soʻrovi yuborildi. Egasi tasdiqlashini kuting.');navigate('bookings');
  }catch(e){setMessage(e instanceof Error?e.message:'Bron yuborilmadi.')}finally{setBookingBusy(false)}
 }
 const loginPanel=<div className="login-card"><div className="login-symbol"><Send size={30}/></div><span className="eyebrow">SIZNING HISOBINGIZ</span><h2>Oʻyinga qoʻshiling.</h2><p>Oʻz Telegram hisobingiz orqali kiring. Maydonlarni bron qiling yoki oʻz maydoningizni joylang.</p>{authLoading?<p>Hisob tekshirilmoqda…</p>:botUsername?<a className="primary login-link" href={`https://t.me/${botUsername}?start=owner`}>Telegram orqali kirish <ArrowUpRight size={18}/></a>:<p>Ilovani Telegram botining menyusidan oching.</p>}<small>Botni oching → Start → Bronnni ochish</small></div>;
 function venueCard(v:Venue){
  const pending=!!searchTime && searchLoading;
  const address=v.address.startsWith('Xaritadagi joy:')?'Joylashuv xaritada belgilangan':v.address;
  return <button className="venue-card" disabled={pending} key={v.id} onClick={()=>openVenue(v)}>
   <div className="venue-image">{v.photos?.length?<PhotoGallery ids={v.photos.slice(0,1)} fallback={<VenueArt sport={v.sport}/>}/>:<VenueArt sport={v.sport}/>}</div>
   <div className="venue-content">
    <span className="venue-sport">{sportName(v.sport)}</span>
    <h3>{v.name}</h3>
    <p className="venue-address"><MapPin size={14}/><span>{address}</span></p>
    {position&&<p className="venue-distance"><Compass size={14}/>Sizdan ≈ {distanceLabel(v)}</p>}
    {!searchTime&&shown[0]?.id===v.id&&<AvailabilityPreview key={filterDay} venueId={v.id} day={filterDay}/>}
    {searchTime&&!searchError&&<p className="venue-slot"><Clock3 size={14}/>{filterTime} · {pending?'Tekshirilmoqda…':'1 soat uchun boʻsh'}</p>}
   </div>
   <div className="venue-footer"><div><strong>{price(v.price)}</strong> <span>soʻm / soat</span></div><span className="card-book">{searchTime?'Vaqtni tanlash':'Boʻsh vaqtlarni koʻrish'} <ArrowRight size={14}/></span></div>
  </button>
 }
 const tomorrow=localDate(new Date(Date.parse(`${today}T12:00:00+05:00`)+86400000));
 const quickTimes=[{day:today,time:'18:00',label:'Bugun 18:00'},{day:today,time:'20:00',label:'Bugun 20:00'},{day:today,time:'22:00',label:'Bugun 22:00'},{day:tomorrow,time:'20:00',label:'Ertaga 20:00'}].filter(item=>!filterTimeDisabled(item.day,item.time));
 async function shareDiscovery(){
  const url=discoveryLink(window.location.href,{sport,query,day:filterDay,time:filterTime});
  try{if(navigator.share){await navigator.share({title:'Bronn — maydon topish',url})}else{await navigator.clipboard.writeText(url);setMessage('Qidiruv havolasi nusxalandi. Jamoangizga yuboring.')}}catch(e){if(!(e instanceof DOMException&&e.name==='AbortError'))setMessage('Havolani ulashib boʻlmadi. Qayta urinib koʻring.')}
 }
 const sportFilters=<div className="chips" aria-label="Sport turi">{sports.map(([id,label])=><button aria-pressed={sport===id} className={sport===id?'active':''} key={id} onClick={()=>setSport(id)}>{id==='all'?<SlidersHorizontal size={15}/>:<span className={`sport-icon ${id}`} aria-hidden="true">{id==='football'?'⚽':<img src={`/icons/${id==='table_tennis'?'table-tennis':'billiards'}.svg`} alt="" width={22} height={22}/>}</span>}{label}</button>)}</div>;
 const searchFilters=<section className="search-filters" aria-label="Maydon filtrlari"><div className="discovery-toolbar"><label className="search-box"><Search size={19}/><input aria-label="Maydon qidirish" placeholder="Maydon yoki manzilni qidiring…" value={query} onChange={e=>setQuery(e.target.value)}/>{query&&<button aria-label="Qidiruvni tozalash" onClick={()=>setQuery('')}><X size={17}/></button>}</label></div><div className="quick-times" aria-label="Tezkor vaqt tanlash">{quickTimes.map(item=><button key={item.label} aria-pressed={filterDay===item.day&&filterTime===item.time} onClick={()=>{setFilterDay(item.day);setFilterTime(item.time)}}>{item.label}</button>)}</div><div className="search-filter-controls"><label>Sana<input type="date" min={today} max={maxDay} value={filterDay} onChange={e=>{if(e.target.value>=today&&e.target.value<=maxDay){setFilterDay(e.target.value);if(filterTime&&filterTimeDisabled(e.target.value,filterTime,Date.now()))setFilterTime('')}}}/></label><HourPicker value={filterTime} disabled={hour=>filterTimeDisabled(filterDay,hour,Date.now())} onChange={setFilterTime}/>{hasFilters&&<button onClick={clearFilters}>Filtrlarni tozalash</button>}</div><p>1 soatlik bron · Oʻzbekiston vaqti (UTC+5){filterTime&&` · ${filterTime}–${String((Number(filterTime.slice(0,2))+1)%24).padStart(2,'0')}:00`}</p>{locationError&&<p role="alert">{locationError}</p>}{searchError&&<p role="alert">{searchError} <button onClick={()=>setSearchRetry(n=>n+1)}>Qayta tekshirish</button></p>}</section>;
 const discoverySummary=searchTime?<div className="discovery-summary"><p role="status">{searchLoading?'Boʻsh vaqtlar tekshirilmoqda…':searchError?'Natijalar tekshirilmadi.':`${filterDay} · ${filterTime} uchun ${shown.length} ta maydon topildi.`}</p><button onClick={()=>setSearchRetry(n=>n+1)} disabled={searchLoading}><RefreshCw size={15}/> Yangilash</button><small>Boʻsh vaqtlar har 30 soniyada qayta tekshiriladi; bu doimiy real vaqt kafolati emas. Bron yuborishda server vaqtni yana tekshiradi. Bron egasi tasdiqlagach kuchga kiradi.</small></div>:null;
 const pageTitle=(eyebrow:string,title:string,description:string)=><div className="page-title"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>;
 return <div className="app"><a className="skip-link" href="#main-content">Asosiy mazmunga oʻtish</a>
  <header className="site-header"><button className="brand" onClick={()=>navigate('home')} aria-label="Bronn bosh sahifa"><span className="brand-mark"><Goal size={23}/></span>Bronn<span className="brand-dot">.</span></button><div className="header-right"><span className="location-pill"><MapPin size={14}/> Namangan</span><button className="profile-button" aria-label="Profil" onClick={()=>navigate('profile')}>{verifiedUser?verifiedUser.first_name.slice(0,1):<UserRound size={19}/>}</button></div></header>
  {message&&<div className="notice" role="status"><span>{message}</span><button aria-label="Xabarni yopish" onClick={()=>setMessage('')}><X size={18}/></button></div>}
  <main ref={mainRef} tabIndex={-1} id="main-content">
  {selected?<>
   <button className="back" onClick={()=>{setSelected(null)}}><ArrowLeft size={17}/> Maydonlarga qaytish</button>
   <div className="detail-layout"><div className="detail-heading"><span className="eyebrow">{sportName(selected.sport)}</span><h1>{selected.name}</h1><p><MapPin size={16}/>{selected.address.startsWith('Xaritadagi joy:')?'Joylashuv xaritada belgilangan':selected.address}</p></div><aside className="booking-panel"><h2>{price(selected.price)} <small>soʻm / soat</small></h2><div className="divider"/><BookingPicker key={selected.id} sport={selected.sport} venueId={selected.id} price={selected.price} authenticated={!!verifiedUser} botUsername={botUsername} busy={bookingBusy} revision={availabilityRevision} initialDay={filterDay} initialTime={searchTime||undefined} onBook={book}/></aside><div className="venue-information"><div className="detail-gallery">{selected.photos?.length?<PhotoGallery ids={selected.photos} fallback={<VenueArt sport={selected.sport}/>}/>:<VenueArt sport={selected.sport}/>}</div><div className="detail-facts"><div><Clock3/><span>Ish vaqti<strong>{selected.hours||'Egasi bilan aniqlashtiring'}</strong></span></div><a href={directions(selected.latitude,selected.longitude)} target="_blank" rel="noreferrer"><MapPin/><span>Manzilga borish<strong>Yoʻnalishni ochish ↗</strong></span></a>{selected.phone&&<a href={`tel:${selected.phone}`}><Phone/><span>Maydon egasi<strong>{selected.phone}</strong></span></a>}</div><VenueAmenities amenities={selected.amenities} extra_amenities={selected.extra_amenities}/></div>
   </div>
  </>:<>
  {tab==='home'&&<>
   <section className="welcome welcome-compact"><div className="welcome-copy"><h1>Bugun qayerda <em>oʻynaymiz?</em></h1></div><div className="welcome-icon" aria-hidden="true"><Goal size={52}/></div></section>
   {sportFilters}

   {searchFilters}
   {discoverySummary}

   <div className="section-heading"><div><h2>{hasFilters?'Qidiruv natijalari':'Maydonlar'}</h2></div><div className="result-tools"><button className="nearby-filter" aria-pressed={nearby} disabled={locating} onClick={toggleNearby}><Compass size={17}/>{locating?'Joylashuv aniqlanmoqda…':nearby?'Eng yaqin maydonlar':'Menga yaqin'}</button><button className="share-results" aria-label="Ulashish" title="Ulashish" onClick={shareDiscovery}><Send size={16}/></button><span className="count">{loading||(searchLoading&&availabilityKey!==searchTime)?'Tekshirilmoqda…':venueError||searchError?'—':`${shown.length} ta maydon`}</span></div></div>
   {loading||(searchLoading&&availabilityKey!==searchTime)?<div className="venue-grid" role="status" aria-label="Yuklanmoqda">{[1,2,3].map(i=><div key={i} className="skeleton"/>)}</div>:venueError?<Empty title="Maydonlar yuklanmadi" action={<button className="secondary" onClick={loadVenues}>Qayta yuklash</button>}>{venueError}</Empty>:searchError?<Empty title="Vaqtlarni tekshirib boʻlmadi">Filtrdagi vaqtni oʻzgartiring yoki qayta tekshiring.</Empty>:shown.length?<div className="venue-grid" aria-busy={searchLoading}>{shown.map(venueCard)}</div>:<Empty title={hasFilters?'Mos maydon topilmadi':'Birinchi maydonni kutyapmiz'} action={<button className="secondary" onClick={()=>hasFilters?clearFilters():navigate('owner')}>{hasFilters?'Filtrlarni tozalash':'Maydonimni qoʻshish'}<ArrowRight size={16}/></button>}>{hasFilters?'Boshqa sana, vaqt yoki qidiruv soʻzini sinab koʻring.':'Maydon egasimisiz? Joyingizni taqdim eting va yangi oʻyinchilarni kutib oling.'}</Empty>}
  </>}
  {tab==='map'&&<>{pageTitle('YAQIN ATROFDA','Maydonlar xaritada','Tasdiqlangan maydonlarning aniq joylashuvini koʻring.')}{searchFilters}<div className="result-tools"><button className="nearby-filter" aria-pressed={nearby} disabled={locating} onClick={toggleNearby}><Compass size={17}/>{locating?'Joylashuv aniqlanmoqda…':nearby?'Eng yaqin maydonlar':'Menga yaqin'}</button><button onClick={shareDiscovery}><Send size={15}/> Ulashish</button></div>{discoverySummary}{venueError?<Empty title="Maydonlar yuklanmadi" action={<button className="secondary" onClick={loadVenues}>Qayta yuklash</button>}>{venueError}</Empty>:searchLoading&&availabilityKey!==searchTime?<p role="status">Vaqtlar tekshirilmoqda…</p>:!searchError&&!venueError&&!loading&&<MapExplorer sportFilters={sportFilters} venues={shown} onSelect={openVenue} time={searchTime?filterTime:undefined}/>}</>}
  {tab==='bookings'&&<>{verifiedUser&&productFeatures.availability_alerts&&<AvailabilitySubscriptions/>}{pageTitle('SIZNING OʻYINLARINGIZ','Bronlarim','Rejalashtirilgan oʻyinlar va soʻrovlaringiz shu yerda.')}<button className="back" onClick={loadBookings}><RefreshCw size={15}/> Yangilash</button>{!verifiedUser?loginPanel:myBookings.length?<div className="booking-list">{myBookings.map(b=><article className="booking-card" key={b.id}><button className="booking-venue-link" aria-label={`${b.venue_name} maydonini ochish`} onClick={()=>openBookedVenue(b)}/><div className="date-tile"><span>{new Date(b.start_at).toLocaleDateString('uz-UZ',{month:'short',timeZone:'Asia/Tashkent'})}</span><strong>{new Date(b.start_at).toLocaleDateString('uz-UZ',{day:'numeric',timeZone:'Asia/Tashkent'})}</strong></div><div className="booking-card-body"><Status value={b.status}/><h3>{b.venue_name}</h3><p><Clock3 size={14}/>{new Date(b.start_at).toLocaleTimeString('uz-UZ',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Tashkent'})} · 1 soat</p></div>{b.status==='pending'&&<button className="text-danger" onClick={()=>decide(`/bookings/${b.id}/cancel`,loadBookings)}>Bekor qilish</button>}</article>)}</div>:<Empty title="Keyingi oʻyiningiz hali oldinda" action={<button className="primary compact" onClick={()=>navigate('home')}>Maydon topish <ArrowRight size={16}/></button>}>Maydon tanlang va birinchi bron soʻrovingizni yuboring.</Empty>}</>}
  {tab==='profile'&&<>{pageTitle('SHAXSIY KABINET','Profil','Hisobingiz, maydonlaringiz va barcha bronlaringiz.')}{!verifiedUser?loginPanel:<><div className="profile-card"><div className="avatar">{verifiedUser.first_name.slice(0,1)}</div><div><h2>{verifiedUser.first_name}</h2><p><ShieldCheck size={15}/> Telegram hisobi tasdiqlangan</p></div></div><div className="profile-links"><button onClick={()=>navigate('owner')}><span className="menu-icon"><Goal/></span><span><strong>Maydon egasi paneli</strong><small>Maydon qoʻshish va bronlarni boshqarish</small></span><ArrowUpRight/></button><button onClick={()=>navigate('bookings')}><span className="menu-icon"><CalendarDays/></span><span><strong>Bronlar tarixi</strong><small>Oʻyinlaringiz va bron holati</small></span><ArrowUpRight/></button>{isAdmin&&<button onClick={()=>navigate('admin')}><span className="menu-icon"><ShieldCheck/></span><span><strong>Admin paneli</strong><small>Maydonlar, arizalar va bronlarni boshqarish</small></span><ArrowUpRight/></button>}</div></>}</>}
  {tab==='owner'&&<><button className="back" onClick={()=>navigate('profile')}><ArrowLeft size={16}/> Profil</button>{!verifiedUser?loginPanel:<OwnerPanel onExpired={()=>{setVerifiedUser(null);setIsAdmin(false)}} onChange={loadVenues}/>}</>}
  {tab==='admin'&&<><button className="back" onClick={()=>navigate('profile')}><ArrowLeft size={16}/> Profil</button>{!verifiedUser?loginPanel:isAdmin?<AdminPanel onChanged={loadVenues}/>:<p role="alert">Bu panelga kirish uchun admin huquqi kerak.</p>}</>}
  </>}
  <footer className="site-footer"><span>Bronn.</span><p>Yaxshi oʻyin — yaxshi maydondan.</p><small>Namangan, Oʻzbekiston</small></footer>
  </main>
  <nav hidden={tab==='admin'||tab==='owner'} style={tab==='admin'||tab==='owner'?{display:'none'}:undefined} ref={navRef} className="bottom-nav" aria-label="Asosiy menyu">{([['home',House,'Bosh sahifa'],['map',MapPin,'Xarita'],['bookings',CalendarDays,'Bronlar'],['profile',UserRound,'Profil']] as const).map(([id,Icon,label])=><button key={id} className={tab===id||(id==='profile'&&(tab==='owner'||tab==='admin'))?'on':''} aria-current={tab===id?'page':undefined} onClick={()=>navigate(id)}><Icon size={21}/><span>{label}</span></button>)}</nav>
 </div>
}
createRoot(document.getElementById('root')!).render(<App/>);
