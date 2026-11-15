export const discoverySports=['all','football','table_tennis','billiards'];
export function validDiscoveryTime(day:string,time:string,now=Date.now()){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(day)||!/^([01]\d|2[0-3]):00$/.test(time))return false;
 const instant=Date.parse(`${day}T${time}:00+05:00`);
 return Number.isFinite(instant)&&new Date(instant+5*3600000).toISOString().slice(0,16)===`${day}T${time}`&&instant>now+5*60000&&instant<=now+60*86400000;
}
export function readDiscovery(search:string,now=Date.now()){
 const params=new URLSearchParams(search);const day=params.get('day')||'';const time=params.get('time')||'';
 return {sport:discoverySports.includes(params.get('sport')||'')?params.get('sport')!:'all',query:(params.get('q')||'').slice(0,100),day:validDiscoveryTime(day,time,now)?day:'',time:validDiscoveryTime(day,time,now)?time:''};
}
export function discoveryLink(href:string,state:{sport:string;query:string;day:string;time:string},now=Date.now()){
 const url=new URL(href);url.search='';url.hash='';
 if(discoverySports.includes(state.sport)&&state.sport!=='all')url.searchParams.set('sport',state.sport);
 if(state.query.trim())url.searchParams.set('q',state.query.trim().slice(0,100));
 if(validDiscoveryTime(state.day,state.time,now)){url.searchParams.set('day',state.day);url.searchParams.set('time',state.time)}
 return url.toString();
}
