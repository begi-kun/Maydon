import React, {useEffect, useState} from 'react';
import {Phone, RefreshCw, ShieldCheck} from 'lucide-react';
import {API, authHeaders} from './owner';

export function BookingContact({venueId,time,botUsername,onChange}:{venueId:number;time:string;botUsername:string;onChange:(phone:string|null)=>void}){
 const [phone,setPhone]=useState<string|null>(null);const [waiting,setWaiting]=useState(false);const [error,setError]=useState('');
 useEffect(()=>{let active=true;
  async function refresh(){try{const response=await fetch(`${API}/auth/contact`,{headers:authHeaders()});if(!response.ok)throw Error();const data=await response.json();if(active){setPhone(data.phone);onChange(data.phone);}}catch{if(active)setError('Raqamni tekshirib boʻlmadi. Telegramdan qayta oching.');}}
  refresh();window.addEventListener('focus',refresh);return()=>{active=false;window.removeEventListener('focus',refresh)};
 },[onChange]);
 useEffect(()=>{if(!waiting)return;let active=true;let count=0;
  const timer=setInterval(async()=>{count++;try{const response=await fetch(`${API}/auth/contact`,{headers:authHeaders()});if(!response.ok)throw Error();const data=await response.json();if(active&&data.phone){setPhone(data.phone);onChange(data.phone);setWaiting(false);setError('');return;}}catch{/* Allow a short delay for the bot to receive the contact. */}
   if(active&&count>=15){setWaiting(false);setError('Raqam hali olinmadi. Bot orqali ulashing va “Qayta tekshirish”ni bosing.');}
  },1000);return()=>{active=false;clearInterval(timer)};
 },[waiting,onChange]);
 function request(){setError('');const telegram=window.Telegram?.WebApp;
  if(!telegram?.requestContact){setError('Pastdagi “Bot orqali ulashish” havolasidan foydalaning.');return;}
  try{setWaiting(true);telegram.requestContact(shared=>{if(!shared){setWaiting(false);setError('Bron qilish uchun oʻz telefon raqamingizni ulashishingiz kerak.');}})}catch{setWaiting(false);setError('Pastdagi “Bot orqali ulashish” havolasidan foydalaning.');}
 }
 const fallback=`https://t.me/${botUsername}?start=phone_${venueId}${time?'_'+Math.floor(new Date(time).getTime()/1000):''}`;
 return <div className="booking-contact"><div className="booking-step"><b>3</b><h3>Aloqa raqamingiz</h3></div><p>Raqam bron qilingan maydon egasiga siz bilan bogʻlanish uchun beriladi.</p>
  {phone?<div className="contact-shared"><ShieldCheck size={18}/><span><strong>{phone}</strong><small>Telegram orqali ulashilgan</small></span></div>:<button className="secondary" type="button" disabled={waiting} onClick={request}><Phone size={16}/>{waiting?'Raqam tekshirilmoqda…':'Telefon raqamimni ulashish'}</button>}
  {(!phone||error)&&botUsername&&<a className="inline-link" href={fallback}>Bot orqali ulashish ↗</a>}
  {!phone&&<button type="button" className="back" disabled={waiting} onClick={()=>{setError('');setWaiting(true)}}><RefreshCw size={13}/> Qayta tekshirish</button>}
  {error&&<p role="alert">{error}</p>}
 </div>;
}
