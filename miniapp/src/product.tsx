import React, {useEffect, useState} from 'react';
import {API, authHeaders} from './owner';

export async function productRequest(path:string,body?:unknown){
 const r=await fetch(`${API}${path}`,{headers:{...authHeaders(),...(body!==undefined?{'Content-Type':'application/json'}:{})},...(body!==undefined?{method:'POST',body:JSON.stringify(body)}:{})});
 const data=await r.json();if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:data.detail?.message||'Amal bajarilmadi. Qayta tekshiring.');return data;
}
export function useProductFeatures(){
 const [features,setFeatures]=useState({recurring_bookings:false,availability_alerts:false});
 useEffect(()=>{let active=true;fetch(`${API}/product/features`).then(r=>{if(!r.ok)throw Error();return r.json()}).then(data=>{if(active)setFeatures(data)}).catch(()=>{});return()=>{active=false}},[]);return features;
}
const stamp=(s:string)=>new Date(s).toLocaleString('uz-UZ',{timeZone:'Asia/Tashkent',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});

export function AvailabilitySubscriptions(){
 const [rows,setRows]=useState<{id:number;venue_name:string;start_at:string;queued_at:string|null}[]>([]);const [error,setError]=useState('');const [revision,setRevision]=useState(0);const [busy,setBusy]=useState(false);
 useEffect(()=>{let active=true;productRequest('/availability-subscriptions').then(data=>{if(active){setRows(data);setError('')}}).catch(e=>{if(active)setError(e.message)});return()=>{active=false}},[revision]);
 async function cancel(id:number){setBusy(true);try{await productRequest(`/availability-subscriptions/${id}/cancel`,{});setRevision(n=>n+1)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <section className="setting"><h2>Boʻsh vaqt xabarnomalari</h2><p>Xabar joyni band qilmaydi. Har obuna uchun bir marta Telegram xabari yuboriladi; bronni alohida yuborasiz.</p>{error&&<p role="alert">{error}</p>}{rows.map(row=><div key={row.id}><p>{row.venue_name} · {stamp(row.start_at)}{row.queued_at?' · Xabar navbatga qoʻyilgan':''}</p><button disabled={busy} onClick={()=>cancel(row.id)}>Obunani oʻchirish</button></div>)}{!rows.length&&!error&&<p>Faol obunalar yoʻq.</p>}<button onClick={()=>setRevision(n=>n+1)}>Yangilash</button></section>;
}

export function SlotSubscription({venueId,time}:{venueId:number;time:string}){
 const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');
 useEffect(()=>setMessage(''),[venueId,time]);
 async function subscribe(){setBusy(true);setMessage('');try{await productRequest('/availability-subscriptions',{venue_id:venueId,start_at:time});setMessage('Obuna saqlandi. Vaqt boʻshasa, Telegramga bir marta xabar yuboriladi. Bu bron emas.')}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 return <div className="setting"><p>{stamp(time)} band. Vaqt boʻshaganda xabar olish mumkin.</p><button disabled={busy} onClick={subscribe}>{busy?'Saqlanmoqda…':'Boʻshasa xabar bering'}</button>{message&&<p role="status">{message}</p>}</div>;
}

type RecurringBody={venue_id:number;start_at:string;weeks:number;customer_name:string;customer_phone:string;request_id:string};
type RecurringSlot={day:string;start_at:string;available:boolean;reason:string|null;price:number};
export function RecurringBookingForm({venueId,time,onSaved}:{venueId:number;time:string;onSaved:()=>void}){
 const [body,setBody]=useState<RecurringBody|null>(null);const [slots,setSlots]=useState<RecurringSlot[]>([]);const [dates,setDates]=useState<string[]>([]);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function preview(e:React.FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);setError('');setSlots([]);const form=new FormData(e.currentTarget);const next={venue_id:venueId,start_at:time,weeks:Number(form.get('weeks')),customer_name:String(form.get('customer_name')),customer_phone:String(form.get('customer_phone')),request_id:crypto.randomUUID()};try{const data=await productRequest('/owner/recurring-bookings/preview',next);setBody(next);setSlots(data.slots);setDates(data.has_conflicts?[]:data.slots.map((s:RecurringSlot)=>s.day))}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function save(){if(!body)return;setBusy(true);setError('');try{await productRequest('/owner/recurring-bookings',{...body,selected_dates:dates});onSaved()}catch(e){setError((e as Error).message);setSlots([]);setDates([])}finally{setBusy(false)}}
 return <section><h3>Har hafta shu vaqt</h3><p>4 haftagacha qoʻlda bron. Har sana alohida narx, toʻlov va bekor qilishga ega. Mijozga avtomatik Telegram xabari yuborilmaydi.</p><form onSubmit={preview} onChange={()=>{setSlots([]);setDates([])}}><fieldset disabled={busy}><label>Mijoz ismi<input name="customer_name" required maxLength={120}/></label><label>Mijoz telefoni<input name="customer_phone" type="tel" required pattern="[+0-9 ()\-]{7,40}" maxLength={40}/></label><label>Haftalar soni<select name="weeks" defaultValue="4">{[1,2,3,4].map(n=><option key={n} value={n}>{n} hafta</option>)}</select></label><button>Sanalarni tekshirish</button></fieldset></form>{error&&<p role="alert">{error}</p>}{slots.length>0&&<><p>Saqlanadigan sanalarni tanlang. Band sanalar saqlanmaydi. Narx va mavjudlik saqlashda qayta tekshiriladi.</p>{slots.map(s=><label key={s.day}><input type="checkbox" disabled={busy||!s.available} checked={dates.includes(s.day)} onChange={e=>setDates(old=>e.target.checked?[...old,s.day]:old.filter(d=>d!==s.day))}/>{stamp(s.start_at)} · {s.available?`${s.price.toLocaleString('uz-UZ')} soʻm`:s.reason==='closed'?'Yopiq':'Band'}</label>)}<button className="primary" disabled={busy||!dates.length} onClick={save}>{busy?'Saqlanmoqda…':`${dates.length} ta bronni tasdiqlash`}</button></>}</section>;
}

export function BookingOutcome({bookingId,status,initialOutcome,onSaved}:{bookingId:number;status:string;initialOutcome?:string|null;onSaved:()=>void}){
 const [outcome,setOutcome]=useState(initialOutcome||'unknown');const [message,setMessage]=useState('');const [busy,setBusy]=useState(false);
 async function save(){setBusy(true);try{await productRequest(`/owner/bookings/${bookingId}/outcome`,{outcome});setMessage('Natija qayd qilindi.');onSaved()}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 return <div><label>Seans natijasi<select value={outcome} disabled={busy} onChange={e=>setOutcome(e.target.value)}><option value="unknown">Nomaʼlum / qaydni tozalash</option>{status==='confirmed'&&<><option value="attended">Mijoz keldi</option><option value="no_show">Mijoz kelmadi</option></>}<option value="schedule_error">Jadval xatosi sabab bajarilmadi</option></select></label><button disabled={busy} onClick={save}>Natijani qayd qilish</button>{message&&<p role="status">{message}</p>}</div>;
}

type PilotData={from_date:string;to_date:string;searches:number;timed_searches:number;venue_opens:number;converted_searches:number;converted_timed_searches:number;timed_search_conversion:number|null;unrecorded_outcomes:number;attributed_requests:number;booking_requests:number;unique_customers:number;cancellations:number;measured_decisions:number;mean_decision_seconds:number|null;second_week_returning_customers:number;outcomes:{outcome:string;count:number}[];measurement_note:string};
export function PilotPanel(){
 const [day,setDay]=useState(new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tashkent',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date()));const [data,setData]=useState<PilotData|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);
 async function load(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');setData(null);try{setData(await productRequest(`/admin/pilot?from_date=${day}`))}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <section><h2>Ikki haftalik pilot</h2><form onSubmit={load}><label>Pilot boshlangan sana<input type="date" required value={day} onChange={e=>setDay(e.target.value)}/></label><button disabled={busy}>Hisobotni olish</button></form>{error&&<p role="alert">{error}</p>}{data&&<><p>{data.from_date} — {data.to_date} · UTC+5</p><dl>{Object.entries({"Qidiruvlar":data.searches,"Vaqtli qidiruvlar":data.timed_searches,"Bron yaratilgan vaqtli qidiruvlar":data.converted_timed_searches,"Vaqtli qidiruvdan bronga ulush":data.timed_search_conversion===null?'Maʼlumot yoʻq':`${(data.timed_search_conversion*100).toFixed(1)}%`,"Natijasi qayd qilinmagan seanslar":data.unrecorded_outcomes,"Maydon ochishlar":data.venue_opens,"Bron yaratilgan qidiruvlar":data.converted_searches,"Qidiruvga bogʻlangan bron soʻrovlari":data.attributed_requests,"Barcha ilova bron soʻrovlari":data.booking_requests,"Alohida Telegram mijozlari":data.unique_customers,"Bekor qilingan soʻrovlar":data.cancellations,"Javob vaqti oʻlchangan soʻrovlar":data.measured_decisions,"Oʻrtacha javob vaqti (soniya)":data.mean_decision_seconds===null?'Maʼlumot yoʻq':Math.round(data.mean_decision_seconds),"Ikkinchi hafta qaytgan mijozlar":data.second_week_returning_customers}).map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><p>{data.measurement_note}</p><h3>Egalar qayd qilgan seans natijalari</h3>{data.outcomes.map(o=><p key={o.outcome}>{{attended:'Keldi',no_show:'Kelmadi',schedule_error:'Jadval xatosi',unknown:'Nomaʼlum'}[o.outcome]}: {o.count}</p>)}</>}</section>;
}
