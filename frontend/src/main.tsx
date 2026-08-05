import React, {FormEvent, useEffect, useState} from "react";
import {createRoot} from "react-dom/client";
import {campaignReadinessLabel, validationMessage} from "./flow";
import "./styles.css";

type Campaign={id:string;name:string;brief:string;state:string;channels:string;assets:Asset[]};
type Asset={id:string;title:string;channel:string;content:string;state:string;version:number};
type Cockpit={campaign:Campaign;readiness:{score:number;ready_channels:string[];blockers:string[]}};

async function request<T>(url:string, options?:RequestInit):Promise<T>{
 const response=await fetch(url,{...options,headers:{"Content-Type":"application/json",...(options?.headers||{})}});
 if(!response.ok) throw new Error(await response.text());
 return response.json() as Promise<T>;
}

function App(){
 const [cockpit,setCockpit]=useState<Cockpit|null>(null);
 const [active,setActive]=useState<Asset|null>(null);
 const [draft,setDraft]=useState("");
 const [saveState,setSaveState]=useState("All changes saved");
 const [error,setError]=useState("");
 const [workCount,setWorkCount]=useState(0);
 const refresh=(id:string)=>request<Cockpit>(`/api/v1/campaigns/${id}/cockpit`).then(setCockpit);
 useEffect(()=>{request<{count:number}>("/api/v1/my-work").then(x=>setWorkCount(x.count)).catch(()=>setWorkCount(0));},[]);
 async function createCampaign(event:FormEvent<HTMLFormElement>){
  event.preventDefault(); setError("");
  const form=new FormData(event.currentTarget);
  try{
   const result=await request<{id:string}>("/api/v1/campaigns",{method:"POST",body:JSON.stringify({name:form.get("name"),brief:form.get("brief"),channels:String(form.get("channels")).split(",").map(x=>x.trim()).filter(Boolean)})});
   await refresh(result.id);
  }catch(reason){setError(validationMessage(reason));}
 }
 async function createAsset(){
  if(!cockpit)return;
  try{
   const channel=JSON.parse(cockpit.campaign.channels)[0] as string;
   const asset=await request<{id:string}>(`/api/v1/campaigns/${cockpit.campaign.id}/assets`,{method:"POST",body:JSON.stringify({channel,title:"Campaign launch",content:"Write the first campaign draft here…",author:"You"})});
   await refresh(cockpit.campaign.id); const next=(await request<Cockpit>(`/api/v1/campaigns/${cockpit.campaign.id}/cockpit`)).campaign.assets.find(a=>a.id===asset.id); if(next){setActive(next);setDraft(next.content);}
  }catch(reason){setError(validationMessage(reason));}
 }
 async function save(){
  if(!active)return; setSaveState("Saving…"); setError("");
  try{const revision=await request<{version:number}>(`/api/v1/assets/${active.id}/autosave`,{method:"PUT",body:JSON.stringify({content:draft,expected_version:active.version,author:"You"})}); setActive({...active,content:draft,version:revision.version}); setSaveState(`Saved as v${revision.version}`);}
  catch(reason){setSaveState("Save needs attention");setError(validationMessage(reason));}
 }
 if(!cockpit)return <div className="shell"><Sidebar count={workCount}/><main className="welcome"><div className="eyebrow">CONTENT OPERATIONS, WITH CONTROL</div><h1>Turn a brief into publish-ready content.</h1><p className="lead">Create one focused campaign workspace for writing, channel readiness, approvals, and reliable publishing.</p>{error&&<div role="alert" className="alert">{error}</div>}<form className="onboarding" onSubmit={createCampaign}><label>Campaign name<input required name="name" placeholder="Autumn product launch"/></label><label>Campaign brief<textarea required name="brief" placeholder="Audience, goal, offer, proof and outcome…"/></label><label>Channels<input required name="channels" defaultValue="linkedin, x"/></label><button>Create campaign cockpit <span>→</span></button></form><div className="trust"><span>✓ Versioned editing</span><span>✓ Explainable readiness</span><span>✓ Recovery-first publishing</span></div></main></div>;
 const {campaign,readiness}=cockpit;
 return <div className="shell"><Sidebar count={workCount}/><main><header className="top"><div><div className="crumb">Campaigns / {campaign.name}</div><h1>{campaign.name}</h1><p>{campaign.brief}</p></div><div className="score" aria-label={`${readiness.score} percent ready`}><strong>{readiness.score}%</strong><span>ready</span></div></header>{error&&<div role="alert" className="alert">{error}</div>}<nav className="tabs" aria-label="Campaign sections"><button className="selected">Overview</button><button>Content {campaign.assets.length}</button><button>Approvals</button><button>Publish</button><button>Analytics</button></nav><section className="grid"><article className="panel primary"><div className="panel-title"><div><span className="eyebrow">ASSET PIPELINE</span><h2>Campaign content</h2></div><button onClick={createAsset}>+ New asset</button></div>{campaign.assets.length===0?<div className="empty"><div className="spark">✦</div><h3>{campaignReadinessLabel(readiness.score)}</h3><p>Create the first channel draft. Every save becomes an auditable revision.</p><button onClick={createAsset}>Create first asset</button></div>:<div className="assets">{campaign.assets.map(asset=><button className="asset" key={asset.id} onClick={()=>{setActive(asset);setDraft(asset.content)}}><span className="channel">{asset.channel}</span><strong>{asset.title}</strong><small>{asset.state.replaceAll("_"," ")} · v{asset.version}</small></button>)}</div>}</article><aside className="panel"><span className="eyebrow">NEXT BEST ACTION</span><h2>{campaignReadinessLabel(readiness.score)}</h2><div className="meter"><i style={{width:`${readiness.score}%`}}/></div>{readiness.blockers.map(x=><div className="blocker" key={x}>! <span>{x}</span></div>)}</aside></section>{active&&<div className="modal" role="dialog" aria-modal="true" aria-label="Content editor"><div className="editor"><header><div><span className="eyebrow">{active.channel} · VERSION {active.version}</span><h2>{active.title}</h2></div><button className="ghost" onClick={()=>setActive(null)} aria-label="Close editor">×</button></header><label className="editor-label">Content<textarea value={draft} onChange={event=>{setDraft(event.target.value);setSaveState("Unsaved changes")}}/></label><footer><span aria-live="polite">{saveState}</span><div><button className="ghost" onClick={()=>setActive(null)}>Close</button><button onClick={save}>Save revision</button></div></footer></div></div>}</main></div>;
}
function Sidebar({count}:{count:number}){return <aside className="sidebar"><div className="brand"><b>Content</b>Forge</div><nav><a className="active" href="#">⌂ <span>My work</span>{count>0&&<em>{count}</em>}</a><a href="#">◫ <span>Campaigns</span></a><a href="#">✦ <span>Content</span></a><a href="#">◷ <span>Calendar</span></a><a href="#">✓ <span>Approvals</span></a><a href="#">◎ <span>Localization</span></a><a href="#">↗ <span>Analytics</span></a></nav><div className="profile"><i>CF</i><span><b>Content team</b><small>Professional workspace</small></span></div></aside>}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);
