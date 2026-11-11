import React, {useEffect, useRef, useState} from 'react';
import {ArrowRight, CalendarDays, Clock3, RefreshCw, Send} from 'lucide-react';
import {API} from './owner';
import {BookingContact} from './contact';

const weekdays=['Yak','Du','Se','Chor','Pay','Ju','Sha'];
const months=['yanvar','fevral','mart','aprel','may','iyun','iyul','avgust','sentabr','oktabr','noyabr','dekabr'];
function dateLabel(value:string){const day=localDate(new Date(value));return `${Number(day.slice(8))} ${months[Number(day.slice(5,7))-1]}`;}
type Slot={start_at:string;label:string;status:'available'|'booked'|'past'|'unavailable'};
function localDate(date:Date){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tashkent',year:'numeric',month:'2-digit',day:'2-digit'}).format(date)}
export function BookingPicker({venueId,price,authenticated,botUsername,busy,revision,onBook}:{venueId:number;price:number;authenticated:boolean;botUsername:string;busy:boolean;revision:number;onBook:(time:string)=>void}){
 const today=localDate(new Date());const maxDate=localDate(new Date(Date.now()+60*86400000));
 const [contactPhone,setContactPhone]=useState<string|null>(null);
 const requested=Number(new URLSearchParams(window.location.search).get('slot'))*1000;
 const restore=useRef(requested>Date.now()&&requested<Date.now()+60*86400000?requested:0);
 const [day,setDay]=useState(restore.current?localDate(new Date(restore.current)):today);const [time,setTime]=useState('');const [slots,setSlots]=useState<Slot[]>([]);const [hours,setHours]=useState('');const [loading,setLoading]=useState(true);const [error,setError]=useState('');const [retry,setRetry]=useState(0);
 useEffect(()=>{setTime('');setSlots([]);setLoading(true);setError('');const controller=new AbortController();
  fetch(`${API}/venues/${venueId}/availability?day=${day}`,{signal:controller.signal}).then(async r=>{if(!r.ok)throw Error('Vaqtlarni yuklab boʻlmadi. Qayta urinib koʻring.');return r.json()}).then(data=>{if(controller.signal.aborted)return;setSlots(data.slots);setHours(data.hours||'');if(restore.current){const match=data.slots.find((slot:Slot)=>new Date(slot.start_at).getTime()===restore.current&&slot.status==='available');if(match)setTime(match.start_at);restore.current=0;}}).catch(e=>{if(!controller.signal.aborted)setError(e.message)}).finally(()=>{if(!controller.signal.aborted)setLoading(false)});
  return()=>controller.abort();
 },[venueId,day,revision,retry]);
 const days=Array.from({length:7},(_,index)=>{const date=new Date(`${today}T12:00:00+05:00`);date.setUTCDate(date.getUTCDate()+index);return {value:localDate(date),date}});
 const chosen=slots.find(slot=>slot.start_at===time);
 const signIn=`https://t.me/${botUsername}?start=book_${venueId}${time?'_'+Math.floor(new Date(time).getTime()/1000):''}`;
 return <div className="booking-picker">
  <div className="booking-step"><b>1</b><h3>Kunni tanlang</h3></div>
  <div className="day-strip">{days.map(({value,date},index)=><button key={value} type="button" disabled={busy} aria-pressed={day===value} onClick={()=>setDay(value)} className={day===value?'selected':''}><small>{index===0?'Bugun':index===1?'Ertaga':weekdays[date.getUTCDay()]}</small><strong>{date.toLocaleDateString('uz-UZ',{day:'numeric',timeZone:'Asia/Tashkent'})}</strong></button>)}</div>
  <label className="date-select"><CalendarDays size={17}/><span>Boshqa sana</span><input aria-label="Bron sanasi" type="date" min={today} max={maxDate} value={day} disabled={busy} onChange={e=>{if(e.target.value>=today&&e.target.value<=maxDate)setDay(e.target.value)}}/></label>
  <div className="booking-step"><b>2</b><h3>Vaqtni tanlang</h3><span className="timezone-tag">Namangan · UTC+5</span></div>
  <p className="slot-hours"><Clock3 size={14}/> Ish vaqti: {hours||'Egasi bilan aniqlashtiring'}</p>
  {loading?<p className="slot-loading" role="status">Vaqtlar tekshirilmoqda…</p>:error?<div role="alert">{error}<button className="back" onClick={()=>setRetry(n=>n+1)}><RefreshCw size={14}/> Qayta yuklash</button></div>:<><div className="time-grid">{slots.map(slot=><button type="button" key={slot.start_at} disabled={busy||slot.status!=='available'} aria-pressed={time===slot.start_at} aria-label={`${slot.label}${slot.status==='booked'?' — band':slot.status!=='available'?' — mavjud emas':''}`} className={`${time===slot.start_at?'selected ':''}${slot.status==='booked'?'booked':''}`} onClick={()=>setTime(slot.start_at)}>{slot.label}{slot.status==='booked'&&<small>Band</small>}</button>)}</div><p className="field-help">Band vaqtlarni tanlab boʻlmaydi. Koʻrsatilgan ish vaqtiga mos soatni tanlang. Bron egasi tasdiqlagach kuchga kiradi.</p></>}
  {chosen&&<div className="booking-summary"><div><strong>{dateLabel(time)} · {chosen.label}</strong><span>1 soat</span></div><strong>{new Intl.NumberFormat('uz-UZ').format(price)} soʻm</strong></div>}
  {authenticated?<><BookingContact venueId={venueId} time={time} botUsername={botUsername} onChange={setContactPhone}/><button className="primary" disabled={!chosen||!contactPhone||busy||loading} onClick={()=>onBook(time)}>{busy?'Yuborilmoqda…':!chosen?'Kunni va vaqtni tanlang':!contactPhone?'Avval telefon raqamingizni ulashing':'Bron soʻrovi yuborish'}<ArrowRight size={18}/></button></>:<div className="booking-login"><p>Telegram hisobingiz bilan davom eting. Botdagi tugma sizni shu maydonga qaytaradi.</p>{botUsername?<a href={signIn} className="primary"><Send size={17}/> Telegramda bron qilish</a>:<p>Telegram botining menyusidan MAYDONni oching.</p>}</div>}
 </div>;
}
