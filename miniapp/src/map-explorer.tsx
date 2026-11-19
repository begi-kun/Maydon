import React, {useEffect, useRef, useState} from 'react';
import {ArrowRight, MapPin, X} from 'lucide-react';
import {loadMaps, PhotoGallery} from './owner';
import {sportMarkerOptions} from './sport-markers';
import './map-explorer.css';

type MapVenue={id:number;name:string;sport:string;latitude:number;longitude:number;price:number;address:string;photos?:number[]};
type Bounds=[[number,number],[number,number]];
const sportLabel=(sport:string)=>({football:'Futbol',table_tennis:'Stol tennisi',billiards:'Bilyard'}[sport]||sport);
const money=(value:number)=>new Intl.NumberFormat('uz-UZ').format(value);

export function MapExplorer<T extends MapVenue>({venues,onSelect,time,sportFilters}:{sportFilters:React.ReactNode;venues:T[];onSelect:(venue:T)=>void;time?:string}){
 const container=useRef<HTMLDivElement>(null);const map=useRef<any>(null);const cluster=useRef<any>(null);const api=useRef<any>(null);
 const [ready,setReady]=useState(false);const [error,setError]=useState('');const [retry,setRetry]=useState(0);
 const [bounds,setBounds]=useState<Bounds|null>(null);const [selectedId,setSelectedId]=useState<number|null>(null);
 const [groupIds,setGroupIds]=useState<number[]|null>(null);const fitted=useRef(false);
 const selected=venues.find(v=>v.id===selectedId);
 useEffect(()=>{
  let active=true;let instance:any;let observer:ResizeObserver|undefined;let timer:number|undefined;
  setError('');setReady(false);fitted.current=false;setBounds(null);
  loadMaps().then(ymaps=>{
   if(!active||!container.current)return;api.current=ymaps;
   instance=new ymaps.Map(container.current,{center:[41.0011,71.6726],zoom:12,controls:['zoomControl','geolocationControl']});map.current=instance;
   const update=()=>{window.clearTimeout(timer);timer=window.setTimeout(()=>{if(active)setBounds(instance.getBounds())},150)};
   instance.events.add('boundschange',update);
   cluster.current=new ymaps.Clusterer({preset:'islands#darkGreenClusterIcons',gridSize:64,groupByCoordinates:false,clusterOpenBalloonOnClick:false});
   cluster.current.events.add('click',(event:any)=>{const target=event.get('target');const objects=target.properties.get('geoObjects');if(objects){setGroupIds(objects.map((object:any)=>object.properties.get('venueId')));setSelectedId(null)}});
   instance.geoObjects.add(cluster.current);
   observer=new ResizeObserver(()=>{instance.container.fitToViewport();update()});observer.observe(container.current);
   setReady(true);update();
  }).catch(()=>{if(active)setError('Xarita yuklanmadi. Maydonlarni roʻyxatdan tanlashingiz mumkin.')});
  return()=>{active=false;window.clearTimeout(timer);observer?.disconnect();instance?.destroy();map.current=null;cluster.current=null};
 },[retry]);
 useEffect(()=>{
  if(!ready||!cluster.current)return;
  setGroupIds(null);cluster.current.removeAll();
  const markers=venues.filter(v=>Number.isFinite(v.latitude)&&Number.isFinite(v.longitude)).map(v=>{
   // Names stay in React text nodes; no venue HTML is inserted into map layouts.
   const marker=new api.current.Placemark([v.latitude,v.longitude],{venueId:v.id},{...sportMarkerOptions(v.sport),openBalloonOnClick:false});
   marker.events.add('click',()=>{setSelectedId(v.id);setGroupIds(null)});return marker;
  });cluster.current.add(markers);
  if(!fitted.current&&markers.length){fitted.current=true;const area=cluster.current.getBounds();if(area)map.current.setBounds(area,{checkZoomRange:true,zoomMargin:45,maxZoom:15})}
 },[venues,ready]);
 const visible=venues.filter(v=>!bounds||v.latitude>=bounds[0][0]&&v.latitude<=bounds[1][0]&&v.longitude>=bounds[0][1]&&v.longitude<=bounds[1][1]);
 const listed=groupIds?venues.filter(v=>groupIds.includes(v.id)):error?venues:visible;
 function choose(venue:T){setSelectedId(venue.id);setGroupIds(null);map.current?.panTo([venue.latitude,venue.longitude],{duration:250})}
 function showAll(){setGroupIds(null);const area=cluster.current?.getBounds();if(area)map.current.setBounds(area,{checkZoomRange:true,zoomMargin:45,maxZoom:15})}
 return <section className="map-explorer" aria-label="Maydonlarni xaritada qidirish">
  <div className="map-explorer-panel">
   <div className="map-sport-filters">{sportFilters}</div>
   <div className="map-explorer-canvas">
   <div ref={container} className="explorer-map" aria-label="Sport maydonlari xaritasi"/>
   {!ready&&!error&&<p className="map-loading" role="status">Xarita yuklanmoqda…</p>}
   {error&&<div className="map-error" role="alert"><p>{error}</p><button onClick={()=>setRetry(n=>n+1)}>Qayta urinish</button></div>}
   {ready&&<button className="map-show-all" onClick={showAll}>Barcha maydonlarni koʻrsatish</button>}
   {selected&&<article className="map-preview" aria-label="Tanlangan maydon"><button className="map-preview-close" aria-label="Maydon kartasini yopish" onClick={()=>setSelectedId(null)}><X size={18}/></button>{!!selected.photos?.length&&<PhotoGallery ids={selected.photos.slice(0,1)}/>}<span className="eyebrow">{sportLabel(selected.sport)}</span><h3>{selected.name}</h3><p>{selected.address}</p><strong>{money(selected.price)} soʻm / soat</strong>{time&&<p>{time} · 1 soat uchun boʻsh</p>}<button className="primary compact" onClick={()=>onSelect(selected)}>Vaqt tanlash va bron <ArrowRight size={16}/></button></article>}
  </div>
  </div>
  <aside className="map-results" aria-label="Xaritadagi maydonlar"><div className="map-results-heading"><h2>{groupIds?'Guruhdagi maydonlar':'Shu hududda'}</h2><p role="status">{listed.length} ta maydon</p>{groupIds&&<button onClick={()=>setGroupIds(null)}>Hudud roʻyxatiga qaytish</button>}</div>
   {!listed.length&&<div className="map-results-empty"><MapPin size={24}/><p>{venues.length?'Bu hududda mos maydon yoʻq. Xaritani siljiting yoki uzoqlashtiring.':'Filtrlarga mos maydon yoʻq. Sana, vaqt yoki sport turini oʻzgartiring.'}</p>{!!venues.length&&<button onClick={showAll}>Barchasini koʻrsatish</button>}</div>}
   {listed.map(v=><button key={v.id} className={`map-result ${selectedId===v.id?'is-selected':''}`} aria-pressed={selectedId===v.id} onClick={()=>choose(v)}><span className="eyebrow">{sportLabel(v.sport)}</span><h3>{v.name}</h3><p>{v.address}</p>{time&&<p className="map-result-time">{time} · 1 soat uchun boʻsh</p>}<strong>{money(v.price)} soʻm / soat</strong><span className="map-result-action">Xaritada koʻrish <MapPin size={14}/></span></button>)}
  </aside>
 </section>;
}
