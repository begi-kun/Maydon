import React, {useEffect, useState} from 'react';
import {API, authHeaders} from './owner';

type Metrics = {total:number;pending:number;confirmed:number;rejected:number;cancelled:number;customers:number;confirmed_value:number;unpriced_confirmed:number};
type Venue = {id:number;name:string;status:string;suspended:boolean;deleted_at:string|null};
type Report = {from_date:string|null;to_date:string|null;all_time:boolean;bucket:'day'|'month';summary:Metrics;venues:(Venue&Metrics)[];available_venues:Venue[];trend:(Metrics&{date:string})[]};
const number = (n:number)=>n.toLocaleString('uz-UZ');
const localToday = ()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tashkent',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
function daysBefore(day:string,n:number){const date=new Date(`${day}T12:00:00Z`);date.setUTCDate(date.getUTCDate()-n);return date.toISOString().slice(0,10)}
const dateLabel=(day:string)=>day.split('-').reverse().join('.');
export function AnalyticsPanel({scope,revision=0}:{scope:'admin'|'owner';revision?:number}) {
 const [period,setPeriod]=useState('30');const [from,setFrom]=useState(()=>daysBefore(localToday(),29));const [to,setTo]=useState(localToday);
 const [venue,setVenue]=useState('');const [query,setQuery]=useState('');const [refresh,setRefresh]=useState(0);
 const [report,setReport]=useState<Report|null>(null);const [options,setOptions]=useState<Venue[]>([]);const [loading,setLoading]=useState(true);const [error,setError]=useState('');
 useEffect(()=>{const controller=new AbortController();setLoading(true);setError('');setReport(null);
  fetch(`${API}/${scope}/analytics?${query}`,{headers:authHeaders(),signal:controller.signal}).then(async response=>{if(!response.ok){const body=await response.json();throw Error(response.status===401?'Telegram orqali qayta kiring.':response.status===403?'Bu hisobotga ruxsat yoʻq.':typeof body.detail==='string'?body.detail:'Hisobot yuklanmadi. Qayta urinib koʻring.')}return response.json()}).then((data:Report)=>{setReport(data);setOptions(data.available_venues)}).catch(e=>{if(!controller.signal.aborted)setError(e.message)}).finally(()=>{if(!controller.signal.aborted)setLoading(false)});
  return()=>controller.abort();
 },[scope,query,refresh,revision]);
 function apply(e:React.FormEvent){e.preventDefault();const params=new URLSearchParams();if(period==='all')params.set('all_time','true');else {const end=period==='custom'?to:localToday();params.set('to_date',end);params.set('from_date',period==='custom'?from:daysBefore(end,Number(period)-1))}if(venue)params.set('venue_id',venue);setQuery(params.toString());setRefresh(n=>n+1)}
 const summary=report?.summary;
 const statuses:[keyof Metrics,string][]=[['pending','Kutilmoqda'],['confirmed','Tasdiqlangan'],['rejected','Rad etilgan'],['cancelled','Bekor qilingan']];
 return <section className="analytics-panel" aria-label={scope==='admin'?'Barcha maydonlar tahlili':'Mening maydonlarim tahlili'}>
  <div className="section-heading"><h2>{scope==='admin'?'Umumiy tahlil':'Maydonlaringiz tahlili'}</h2></div>
  <p className="muted">Bron boshlanish sanasi boʻyicha · Oʻzbekiston vaqti (UTC+5). {scope==='owner'?'Faqat sizga tegishli maydonlar.':'Barcha egalar va maydonlar.'}</p>
  <form className="analytics-filters" onSubmit={apply}>
   <label>Davr<select value={period} onChange={e=>setPeriod(e.target.value)}><option value="1">Bugun</option><option value="7">Oxirgi 7 kun</option><option value="30">Oxirgi 30 kun</option><option value="all">Barcha davr</option><option value="custom">Sanalarni tanlash</option></select></label>
   {period==='custom'&&<><label>Boshlanish sanasi<input type="date" required value={from} max={to} onChange={e=>setFrom(e.target.value)}/></label><label>Tugash sanasi<input type="date" required value={to} min={from} onChange={e=>setTo(e.target.value)}/></label></>}
   <label>Maydon<select value={venue} onChange={e=>setVenue(e.target.value)}><option value="">Barcha maydonlar</option>{options.map(v=><option key={v.id} value={v.id}>{v.name} · #{v.id}{v.deleted_at?' (Arxiv)':''}</option>)}</select></label>
   <button type="submit">Hisobotni koʻrish</button><button type="button" disabled={loading} onClick={()=>setRefresh(n=>n+1)}>Yangilash</button>
  </form>
  {loading&&<p role="status">Hisobot yuklanmoqda…</p>}{error&&<p role="alert" className="admin-error">{error}</p>}
  {report&&summary&&<>
   <p className="analytics-period">{report.all_time?'Barcha davr, kelgusi bronlar ham kiritilgan':`${dateLabel(report.from_date!)} — ${dateLabel(report.to_date!)}`} · {report.venues.length} ta maydon</p>
   <div className="analytics-metrics"><div><span>Jami bronlar</span><strong>{number(summary.total)}</strong></div><div><span>Tasdiqlangan soatlar</span><strong>{number(summary.confirmed)}</strong><small>Har bir bron — 1 soat</small></div><div><span>Noyob mijozlar</span><strong>{number(summary.customers)}</strong><small>Telegram hisoblari; qoʻlda kiritilganlar hisoblanmaydi</small></div><div><span>Tasdiqlangan bronlar qiymati</span><strong>{number(summary.confirmed_value)} <small>soʻm</small></strong></div></div>
   <p className="analytics-note">Bron qiymati toʻlangan tushum emas. Toʻlov holatlari bronlar roʻyxatida alohida qayd etiladi.{summary.unpriced_confirmed>0&&` ${number(summary.unpriced_confirmed)} ta tasdiqlangan bronning narxi saqlanmagan; ular qiymat hisobiga kiritilmagan.`}</p>
   <div className="analytics-statuses">{statuses.map(([key,label])=><div key={key}><span>{label}</span><strong>{number(summary[key])}</strong><small>{summary.total?Math.round(summary[key]/summary.total*100):0}%</small></div>)}</div>
   {summary.total===0&&<p className="analytics-note">Tanlangan davrda bronlar yoʻq. Boshqa davr yoki maydonni tanlang.</p>}
   {report.trend.length>0&&<div className="analytics-section"><h3>Bronlar dinamikasi · {report.bucket==='month'?'oylar':'kunlar'} boʻyicha</h3><p className="muted">Bron bo‘lmagan {report.bucket==='month'?'oylar':'kunlar'} koʻrsatilmagan. Ustun ustiga bosing yoki olib boring.</p><div className="analytics-chart" aria-label="Davr boʻyicha bronlar soni">{report.trend.map(row=><button type="button" key={row.date} className="analytics-bar" title={`${dateLabel(row.date)}: ${row.total} ta bron, ${row.confirmed} ta tasdiqlangan`} aria-label={`${dateLabel(row.date)}: ${row.total} ta bron, ${row.confirmed} ta tasdiqlangan`} onClick={()=>{setPeriod('custom');setFrom(row.date);const end=report.bucket==='month'?new Date(Date.UTC(Number(row.date.slice(0,4)),Number(row.date.slice(5,7)),0)).toISOString().slice(0,10):row.date;setTo(end);const params=new URLSearchParams(query);params.delete('all_time');params.set('from_date',row.date);params.set('to_date',end);setQuery(params.toString())}}><span>{row.total}</span><i style={{height:`${Math.max(4,row.total/Math.max(...report.trend.map(r=>r.total))*90)}px`}}/><small>{report.bucket==='month'?row.date.slice(0,7):row.date.slice(5)}</small></button>)}</div></div>}
   <div className="analytics-section"><h3>Maydonlar boʻyicha natijalar</h3>{report.venues.length===0?<p>Hozircha maydonlar yoʻq.</p>:<div className="analytics-table-scroll" tabIndex={0} role="region" aria-label="Maydonlar hisoboti"><table className="analytics-table"><thead><tr><th>Maydon</th><th>Jami</th><th>Tasdiqlangan</th><th>Kutilmoqda</th><th>Rad etilgan</th><th>Bekor qilingan</th><th>Mijozlar</th><th>Bron qiymati (soʻm)</th></tr></thead><tbody>{report.venues.map(v=><tr key={v.id}><th scope="row">{v.name}<small>#{v.id}{v.deleted_at?' · Arxiv':v.suspended?' · Toʻxtatilgan':''}</small></th><td>{number(v.total)}</td><td>{number(v.confirmed)}</td><td>{number(v.pending)}</td><td>{number(v.rejected)}</td><td>{number(v.cancelled)}</td><td>{number(v.customers)}</td><td>{number(v.confirmed_value)}{v.unpriced_confirmed>0&&<small>{v.unpriced_confirmed} ta bron narxi yoʻq</small>}</td></tr>)}</tbody></table></div>}</div>
  </>}
 </section>;
}
