import {API} from './owner';
let sessionId:string|undefined;
function session(){
 if(sessionId)return sessionId;
 try{sessionId=sessionStorage.getItem('maydon-discovery-session')||crypto.randomUUID();sessionStorage.setItem('maydon-discovery-session',sessionId)}catch{sessionId=crypto.randomUUID()}
 return sessionId;
}
export function recordDiscovery(data:{search_id:string;event:'discovery_results'|'venue_open';day:string|null;hour:number|null;sport:string;result_count?:number;venue_id?:number}){
 // No Telegram headers, names, phone, free text or location are sent.
 const controller=new AbortController();const timer=window.setTimeout(()=>controller.abort(),2000);
 return fetch(`${API}/discovery/events`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),session_id:session(),...data}),keepalive:true,signal:controller.signal}).then(()=>{}).catch(()=>{}).finally(()=>window.clearTimeout(timer));
}
