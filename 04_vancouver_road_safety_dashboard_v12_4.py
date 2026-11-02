"""Vancouver Road Safety Dashboard v12.4: contextual feedback and multi-select road highlights, comparative analytics, spatial-index hover, QA.
Run in project root: python 04_vancouver_road_safety_dashboard_v12_4.py
Reads CLEAN semicolon CSV and official public-streets.csv; writes self-contained DATA HTML
(the Leaflet JS/CSS dependencies still load from CDNs)."""
from pathlib import Path
from collections import defaultdict
import json, re
import numpy as np
import pandas as pd
import folium
from shapely.geometry import shape, Point
from shapely.ops import transform
from shapely.strtree import STRtree

from project_paths import ROOT, RAW, INTERMEDIATE, QUALITY, COLLISION, MAPS, ensure_output_dirs
ensure_output_dirs()
ROOT=Path(__file__).resolve().parent
CLEAN=QUALITY/'parking_tickets_clean_geocoded.csv'
ROADS=RAW/'public-streets.csv'
if not ROADS.exists():
 matches=list(RAW.glob('public-streets*.csv'))
 if matches:ROADS=matches[0]
COLLISIONS=COLLISION/'collision_locations.csv'
OUT=MAPS
OUT.mkdir(exist_ok=True)
YEARS=list(range(2020,2026))
STATUSES=['IS','VA','WR','VS']
PALETTES={
 'total':['#fee2e2','#fecaca','#fca5a5','#ef4444','#7f1d1d'],
 'IS':['#fee2e2','#fecaca','#fca5a5','#ef4444','#7f1d1d'],
 'VA':['#dcfce7','#86efac','#4ade80','#16a34a','#166534'],
 'WR':['#fef9c3','#fde68a','#fbbf24','#d97706','#92400e'],
 'VS':['#dbeafe','#93c5fd','#60a5fa','#2563eb','#1e3a8a'],
 'VA_rate':['#f0fdf4','#bbf7d0','#86efac','#22c55e','#166534'],
 'WR_rate':['#fffbeb','#fde68a','#fbbf24','#f59e0b','#92400e'],
 'delta':['#2563eb','#93c5fd','#e5e7eb','#fca5a5','#b91c1c']
}
def norm(v):
 s=re.sub(r'\s+',' ',str(v).upper().replace('.',' ').strip())
 for old,new in [('AVENUE','AV'),('AVE','AV'),('STREET','ST'),('DRIVE','DR'),('ROAD','RD'),('BOULEVARD','BLVD'),('CRESCENT','CRES'),('PLACE','PL'),('LANE','LN')]:
  s=re.sub(r'\b'+old+r'\b',new,s)
 return s

def parse_road(v):
 m=re.match(r'^\s*(\d+)(?:\s*-\s*(\d+))?\s+(.+?)\s*$',str(v))
 return (int(m[1]),int(m[2] or m[1]),norm(m[3])) if m else None

def load_counts():
 if not CLEAN.exists():raise FileNotFoundError(f'Missing cleaned data: {CLEAN}. Run stages 01-03 first.')
 print('Reading cleaned records by year and status:',CLEAN,flush=True)
 pieces=[]; annual={y:{'total':0,**{s:0 for s in STATUSES}} for y in YEARS}; nrows=0
 for chunk in pd.read_csv(CLEAN,sep=';',encoding='utf-8-sig',usecols=['Block','Street','Year','Status'],dtype='string',chunksize=200000):
  chunk['Year']=pd.to_numeric(chunk['Year'],errors='coerce')
  chunk=chunk[chunk['Year'].isin(YEARS)].copy()
  chunk['Status']=chunk['Status'].str.strip().str.upper()
  nrows+=len(chunk)
  for (year,status),count in chunk.groupby(['Year','Status']).size().items():
   annual[int(year)]['total']+=int(count)
   if status in STATUSES:annual[int(year)][status]+=int(count)
  pieces.append(chunk.groupby(['Block','Street','Year','Status'],dropna=False).size().rename('n').reset_index())
 a=pd.concat(pieces,ignore_index=True).groupby(['Block','Street','Year','Status'],dropna=False,as_index=False)['n'].sum()
 a['blocknum']=pd.to_numeric(a.Block,errors='coerce')
 a=a.dropna(subset=['blocknum'])
 a['blocknum']=a.blocknum.astype(int)
 a['streetkey']=a.Street.map(norm)
 a=a[a.Status.isin(STATUSES)]
 grouped=a.groupby(['blocknum','streetkey','Year','Status'],as_index=False)['n'].sum()
 index=defaultdict(dict)
 for r in grouped.itertuples(index=False):
  yr=int(r.Year); k=(int(r.blocknum),r.streetkey)
  if yr not in index[k]:index[k][yr]={s:0 for s in STATUSES}
  index[k][yr][r.Status]=int(r.n)
 print('Rows with selected years:',nrows,'| Unique block keys:',len(index),flush=True)
 return index,annual

def load_infractions():
 print('Aggregating exact InfractionText by unique block and year...',flush=True)
 pieces=[]
 for chunk in pd.read_csv(CLEAN,sep=';',encoding='utf-8-sig',usecols=['Block','Street','Year','InfractionText'],dtype='string',chunksize=200000):
  chunk['blocknum']=pd.to_numeric(chunk.Block,errors='coerce')
  chunk=chunk.dropna(subset=['blocknum','Street','Year'])
  chunk['blocknum']=chunk.blocknum.astype(int)
  chunk['streetkey']=chunk.Street.map(norm)
  chunk['InfractionText']=chunk.InfractionText.fillna('(Missing infraction description)').str.strip().replace('', '(Missing infraction description)')
  pieces.append(chunk.groupby(['blocknum','streetkey','Year','InfractionText']).size().rename('n').reset_index())
 a=pd.concat(pieces,ignore_index=True).groupby(['blocknum','streetkey','Year','InfractionText'],as_index=False)['n'].sum()
 names=sorted(a.InfractionText.unique().tolist())
 code={v:i for i,v in enumerate(names)}
 out=defaultdict(dict)
 for r in a.itertuples(index=False):
  out[(int(r.blocknum),r.streetkey)].setdefault(str(r.Year),[]).append([code[r.InfractionText],int(r.n)])
 print('Infraction groups:',len(a),'| distinct types:',len(names),flush=True)
 return out,names

def load_collisions():
 if not COLLISIONS.exists():
  raise FileNotFoundError(f'Missing {COLLISIONS}. Run 05_collision_extension.py first.')
 d=pd.read_csv(COLLISIONS,low_memory=False)
 d=d.dropna(subset=['Latitude','Longitude','Year']).copy()
 d['Year']=pd.to_numeric(d.Year,errors='coerce').astype(int)
 d['Crashes']=pd.to_numeric(d.Crashes,errors='coerce').fillna(0)
 d['casualty']=d['Crash Severity'].astype(str).str.strip().str.upper().eq('CASUALTY CRASH')
 for col,flag in [('Pedestrian Flag','ped'),('Cyclist Flag','cyclist'),('Parked Vehicle Flag','parked')]:
  d[flag]=d[col].astype(str).str.strip().str.upper().eq('YES')
 d['latkey']=d.Latitude.round(5);d['lonkey']=d.Longitude.round(5)
 d['config']=d['Derived Crash Configuration'].fillna('UNKNOWN / MISSING').astype(str).str.strip().str.upper()
 names=sorted(d['config'].unique().tolist())
 code={v:i for i,v in enumerate(names)}
 d['config_code']=d['config'].map(code)
 for flag in ['casualty','ped','cyclist','parked']:
  d[flag+'_n']=d.Crashes*d[flag]
 cols=['Crashes','casualty_n','ped_n','cyclist_n','parked_n']
 a=d.groupby(['latkey','lonkey','Year','config_code'],as_index=False)[cols].sum()
 print('ICBC mapped location/year/configuration groups:',len(a),flush=True)
 return [[round(float(r.latkey),5),round(float(r.lonkey),5),int(r.Year),int(r.Crashes),int(r.casualty_n),int(r.ped_n),int(r.cyclist_n),int(r.parked_n),int(r.config_code)] for r in a.itertuples(index=False)],names

def assign_crashes_to_roads(features, collisions):
 """Approximate nearest road assignment; reject ambiguous intersections and >50m locations."""
 print('Assigning ICBC approximate locations to road labels (ambiguous intersections excluded)...',flush=True)
 sx=111320*np.cos(np.deg2rad(49.25)); sy=111132
 def project(x,y,z=None):return ((x+123.12)*sx,(y-49.25)*sy)
 geometries=[]; labels=[]
 for f in features:
  try:
   geom=transform(project,shape(f['geometry']))
   if not geom.is_empty:geometries.append(geom);labels.append(f['properties']['road'])
  except Exception:pass
 tree=STRtree(geometries)
 # one assignment per approximate coordinate, shared across years/configurations
 keys={(r[0],r[1]) for r in collisions}
 lookup={}; excluded={'too_far':0,'ambiguous':0,'matched':0}
 for lat,lon in keys:
  point=Point((lon+123.12)*sx,(lat-49.25)*sy)
  nearest=int(tree.nearest(point));distance=geometries[nearest].distance(point)
  if distance>50:excluded['too_far']+=1;continue
  # An intersection may be close to several distinct road labels; do not force one.
  candidates=tree.query(point.buffer(distance+12))
  nearby={labels[int(i)] for i in candidates if geometries[int(i)].distance(point)<=distance+12}
  if len(nearby)>1:excluded['ambiguous']+=1;continue
  lookup[(lat,lon)]=labels[nearest];excluded['matched']+=1
 aggregated=defaultdict(lambda:defaultdict(lambda:[0,0,0,0,0,0]))
 for r in collisions:
  road=lookup.get((r[0],r[1]))
  if road is None:continue
  row=aggregated[road][str(r[2])]
  for i in range(5):row[i]+=r[3+i]
  row[5]+=3*r[4]+(r[3]-r[4])
 print('Road-level assignment:',excluded,'| road labels:',len(aggregated),flush=True)
 (OUT/'v12_4_geocoding_quality.json').write_text(json.dumps({'unique_approximate_locations':len(keys),'assignment_counts':excluded,'method':'Nearest road within 50m; reject multiple road labels within 12m of nearest distance. This is approximate, not ground-truth accuracy.','limitations':['Intersection ambiguity','Coordinate rounding','Road-label duplication across segments']},indent=2),encoding='utf-8')
 return aggregated,excluded

def build():
 idx,annual=load_counts()
 collisions,collision_names=load_collisions()
 infra,infra_names=load_infractions()
 if not ROADS.exists():raise FileNotFoundError(f'Missing {ROADS}')
 roads=pd.read_csv(ROADS,sep=';',encoding='utf-8-sig',usecols=['HBLOCK','Geom'],dtype='string')
 bystreet=defaultdict(list)
 for (block,street),year_data in idx.items():bystreet[street].append((block,year_data))
 features=[]; matched=0
 for road in roads.itertuples(index=False):
  parsed=parse_road(road.HBLOCK)
  if not parsed:continue
  lo,hi,key=parsed
  try:
   geom=json.loads(road.Geom)
   if geom['type'] not in ('LineString','MultiLineString'):continue
  except (TypeError,ValueError,KeyError):continue
  candidates=bystreet.get(key,[])
  exact=[v for v in candidates if v[0]==lo]
  selected=exact if exact else [v for v in candidates if lo<=v[0]<=hi]
  per_year={}
  for year in YEARS:
   counts={s:sum(v[1].get(year,{}).get(s,0) for v in selected) for s in STATUSES}
   per_year[str(year)]=[counts[s] for s in STATUSES]
  if selected:matched+=1
  features.append({'type':'Feature','geometry':geom,'properties':{
   'road':str(road.HBLOCK),'years':per_year,
   'blockKeys':[str(v[0])+' '+key for v in selected],
   'join':'ExactStart' if exact else ('InclusiveRange' if selected else 'No match')}})
 print('Official road geometries:',len(features),'| joined geometries:',matched,flush=True)
 road_crashes,match_audit=assign_crashes_to_roads(features,collisions)
 for f in features:f['properties']['crashes']=road_crashes.get(f['properties']['road'],{})
 # Store all infraction types by unique block and year. Do not truncate to top 10 before aggregating selected years.
 infra_data={str(block)+' '+street:year_counts for (block,street),year_counts in infra.items()}
 print('Unique infraction blocks:',len(infra_data),flush=True)
 m=folium.Map(location=[49.255,-123.12],zoom_start=12,tiles=None,control_scale=True,prefer_canvas=True)
 geo=folium.GeoJson({'type':'FeatureCollection','features':features},
  style_function=lambda f:{'color':'#cbd5e1','weight':1,'opacity':.45},
  name='Vancouver road network')
 geo.add_to(m)
 panel='''<div id="pk-panel" style="position:fixed;top:12px;left:12px;z-index:9999;width:300px;max-height:calc(67vh - 30px);overflow:auto;box-sizing:border-box;background:#fff;border:1px solid #cbd5e1;border-radius:10px;padding:14px;font:13px Arial;box-shadow:0 3px 12px #0002;color:#172033">
 <b style="font-size:16px">Vancouver Road Safety Analytics</b><div style="font-size:11px;color:#64748b;margin-top:3px">Parking violations & ICBC collisions · 2020–2025</div>
 <div style="margin-top:12px"><b>1. Analysis Layer</b><select id="pk-layer" style="width:100%;padding:6px;margin-top:4px"><option value="parking">Parking Violations</option><option value="collision" selected>Traffic Collisions</option><option value="compare">Parking vs. Collisions</option></select></div>
 <div style="margin-top:12px"><b>2. Analysis Period</b><select id="pk-mode" style="width:100%;padding:6px;margin-top:4px"><option value="filter">Selected years · aggregate</option><option value="compare">Year comparison (B − A)</option></select></div>
 <div id="pk-years" style="margin-top:10px"><b>Years (select one or multiple)</b><div id="pk-year-box" style="display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:7px"></div><div style="margin-top:6px"><button id="pk-all">All years</button> <button id="pk-none">Clear</button></div></div>
 <div id="pk-compare" style="display:none;margin-top:10px"><b>Year comparison</b><div style="display:flex;gap:7px;margin-top:5px"><select id="pk-a" style="flex:1;padding:5px"></select><span style="align-self:center">vs</span><select id="pk-b" style="flex:1;padding:5px"></select></div></div>
 <div style="margin-top:12px"><b>3. Analysis Metric</b><div id="pk-parking-metric"><label style="font-size:11px">Parking metric</label><select id="pk-metric" style="width:100%;padding:6px;margin-top:4px"><option value="total">All tickets</option><option value="IS">Issued (IS)</option><option value="VA">VA-coded</option><option value="WR">Warning (WR)</option><option value="VS">VS-coded</option><option value="VA_rate">VA share (%)</option><option value="WR_rate">Warning share (%)</option></select></div><div id="pk-crash-metric" style="margin-top:6px"><label style="font-size:11px">Collision metric</label><select id="pk-cmetric" style="width:100%;padding:6px;margin-top:4px"><option value="0">Total crashes</option><option value="1">Casualty crashes</option><option value="2">Pedestrian-related</option><option value="3">Cyclist-related</option><option value="4">Parked-vehicle related</option><option value="5">Severity-weighted score (3:1)</option></select></div></div>
 <div style="margin-top:12px"><b>4. Road Highlights</b><div id="pk-highlight-options" style="display:grid;gap:7px;margin-top:7px"><label><input type="checkbox" id="pk-h-top" checked> <span style="color:#6d28d9">●</span> Highest-volume roads</label><label><input type="checkbox" id="pk-h-improved"> <span style="color:#0d9488">●</span> Most improved roads</label><label><input type="checkbox" id="pk-h-deteriorated"> <span style="color:#ea580c">●</span> Most deteriorated roads</label></div><div style="margin-top:6px"><button type="button" id="pk-h-clear">Clear highlights</button> <button type="button" id="pk-h-all">Select all</button></div><div style="display:flex;align-items:center;gap:8px;margin-top:7px"><label>Highlight top</label><select id="pk-topn"><option>50</option><option>100</option><option selected>150</option><option>250</option></select><span>per category</span></div><div id="pk-road-note" style="font-size:11px;color:#64748b;margin-top:5px"></div><div style="font-size:10px;color:#64748b;margin-top:5px">Improved/deteriorated use Year Comparison (B − A). Purple = high volume; teal = fewer; orange = more. Dashed stroke = also Top N.</div></div>
 <div style="margin-top:10px"><label><input id="pk-streets" type="checkbox" checked> Show unmatched / zero roads</label></div>
 <div style="display:none"><input id="pk-best" type="checkbox"><input id="pk-worst" type="checkbox"><span id="pk-highlight-summary"></span><select id="pk-min"><option value="30">30</option></select></div>
 <div id="pk-help" role="status" aria-live="polite" style="display:none;margin-top:10px;padding:9px;background:#eff6ff;border-left:3px solid #2563eb;border-radius:5px;font-size:12px;line-height:1.5"></div><div id="pk-summary" style="margin-top:12px;padding:8px;background:#f1f5f9;border-radius:6px"></div><div id="pk-annual" style="margin-top:10px"></div><div id="pk-legend" style="margin-top:9px"></div><div id="pk-detail" style="font-size:12px;margin-top:10px;color:#334155">Click a street segment for yearly details.</div>
 <div style="font-size:10px;color:#64748b;margin-top:12px;line-height:1.4">ICBC geocodes are approximate; ambiguous intersection assignments are excluded from road ranking. Severity weights are exploratory, not ICBC official. Counts are not exposure-adjusted risk.</div></div>'''
 panel += '''<div id="pk-ranking" style="position:fixed;right:12px;top:12px;z-index:9999;width:325px;max-height:calc(67vh - 30px);overflow:auto;background:white;border:1px solid #cbd5e1;border-radius:10px;padding:14px;font:13px Arial;box-shadow:0 3px 12px #0002;color:#172033">
 <b style="font-size:16px">Top 10 · Infraction Types</b><div id="pk-rank-subtitle" style="color:#64748b;font-size:11px;margin-top:5px">Hover over a street segment to inspect its block</div>
 <div id="pk-rank-items" style="margin-top:12px"><p style="color:#64748b">Move the cursor over a road. Click a road to lock the result.</p></div>
 <div style="margin-top:10px"><button id="pk-unlock" style="padding:6px 10px">Unlock / Follow mouse</button></div>
 <div style="font-size:10px;color:#64748b;line-height:1.4;margin-top:12px">Counts are grouped by unique Block + Street + Year + InfractionText, not summed road geometries. Multiple geometries may represent the same block. Comparison shows B − A for each infraction type.</div>
 </div>'''
 panel += '''<div id="pk-collision" style="position:fixed;bottom:10px;left:12px;right:12px;height:33vh;min-height:220px;z-index:9999;box-sizing:border-box;overflow:auto;background:#fff;border:1px solid #94a3b8;border-radius:10px;padding:12px 16px;font:13px Arial;color:#172033;box-shadow:0 3px 12px #0003">
 <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap"><b style="font-size:16px">Collision Details & Severity · 2021–2025</b><span style="font-size:11px;color:#64748b">Approximate locations · spatial proximity is not causation</span></div>
 <div style="margin-top:9px;display:flex;gap:12px;align-items:center;flex-wrap:wrap"><label>Search radius <select id="pk-radius"><option value="100">100 m</option><option value="200" selected>200 m</option><option value="300">300 m</option><option value="500">500 m</option><option value="1000">1,000 m</option></select></label><label><input id="pk-collision-points" type="checkbox" checked> Show nearby collision markers</label><label><input id="pk-collision-circle" type="checkbox" checked> Show search radius circle</label><label><input id="pk-follow-cursor" type="checkbox" checked> Follow mouse (hover)</label><button id="pk-collision-unlock" type="button">Unlock location</button></div>
 <div id="pk-collision-content" style="margin-top:12px;color:#475569">Click a road segment on the map to inspect nearby recorded collisions.</div>
 <div style="font-size:10px;color:#64748b;margin-top:8px">Counts sum ICBC Total Crashes, not CSV rows. Unmatched/ambiguous locations are excluded from mapped proximity results. Approximate geocodes are not measured collision risk.</div></div>'''
 m.get_root().html.add_child(folium.Element(panel))
 js=r'''
window.addEventListener('load',function(){
 const map=MAPVAR,layer=GEOVAR,annual=ANNUAL,palettes=PALETTES,infraData=INFRADATA,infraNames=INFRANAMES,collisionData=COLLISIONDATA,collisionNames=COLLISIONNAMES;
 const $=id=>document.getElementById(id), years=[2020,2021,2022,2023,2024,2025],statuses=['IS','VA','WR','VS'];
 const mode=$('pk-mode'),metric=$('pk-metric'),min=$('pk-min'),streets=$('pk-streets'),best=$('pk-best'),worst=$('pk-worst'),highlightSummary=$('pk-highlight-summary'),summary=$('pk-summary'),legend=$('pk-legend'),detail=$('pk-detail');
 const yearBox=$('pk-year-box'), a=$('pk-a'), b=$('pk-b'), rankItems=$('pk-rank-items');
 // Accessible contextual feedback: use an inline explanation plus a brief toast.
 let noticeTimer;
 const toast=document.createElement('div');toast.id='pk-toast';toast.setAttribute('role','status');
 Object.assign(toast.style,{position:'fixed',left:'50%',top:'18px',transform:'translateX(-50%)',zIndex:'20000',maxWidth:'min(520px,90vw)',padding:'12px 16px',background:'#172033',color:'white',borderRadius:'9px',boxShadow:'0 4px 20px #0004',font:'13px Arial',display:'none',lineHeight:'1.5'});
 document.body.appendChild(toast);
 function explain(msg){const help=$('pk-help');help.textContent=msg;help.style.display='block';toast.textContent=msg;toast.style.display='block';clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>{toast.style.display='none'},4500)}
 const no2020='ICBC collision records in this dashboard cover 2021–2025. Year 2020 is available only for Parking Violations. Switch Analysis Layer to Parking to use 2020.';
 const noChanges='Most Improved and Most Deteriorated require Year Comparison (B − A). Select two different years in Analysis Period.';

 years.forEach(y=>{yearBox.insertAdjacentHTML('beforeend','<label><input type="checkbox" class="pk-y" value="'+y+'" checked> '+y+'</label>');a.add(new Option(y,y));b.add(new Option(y,y))});a.value='2020';b.value='2025';
 // Grid index (~0.002 degrees per cell) avoids scanning every ICBC record on mouse hover.
 const gridSize=.002, collisionGrid=new Map();
 const gridKey=(x,y)=>x+','+y;
 collisionData.forEach((r,i)=>{const key=gridKey(Math.floor(r[0]/gridSize),Math.floor(r[1]/gridSize));if(!collisionGrid.has(key))collisionGrid.set(key,[]);collisionGrid.get(key).push(i)});
 function nearbyCandidates(lat,lon,latDelta,lonDelta){
  const found=[];
  const x0=Math.floor((lat-latDelta)/gridSize),x1=Math.floor((lat+latDelta)/gridSize);
  const y0=Math.floor((lon-lonDelta)/gridSize),y1=Math.floor((lon+lonDelta)/gridSize);
  for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++){
   const bucket=collisionGrid.get(gridKey(x,y));if(bucket)for(const i of bucket)found.push(collisionData[i]);
  }
  return found;
 }
 const lines=[];let activeRoad=null,locked=false,activePoint=null,locationLocked=false,hoverTimer=null,pendingPoint=null;const collisionMarkers=L.layerGroup().addTo(map);const searchCircle=L.circle([49.255,-123.12],{radius:200,color:"#7c3aed",weight:2,dashArray:"7 5",fillColor:"#a78bfa",fillOpacity:.09,interactive:false});
 layer.eachLayer(l=>{if(l.feature&&l.feature.properties){lines.push(l);
 l.on('mouseover',()=>{if(!locked){activeRoad=l.feature.properties;rankRender()}});
 l.on('click',(event)=>{activeRoad=l.feature.properties;activePoint=event.latlng;locked=true;locationLocked=true;showDetail(activeRoad);rankRender();collisionRender()});
 }});
 $('pk-unlock').addEventListener('click',()=>{locked=false;locationLocked=false;rankRender()});
 $('pk-collision-unlock').addEventListener('click',()=>{locationLocked=false;locked=false;rankRender()});
 // Hover sampling is debounced to limit repeated proximity scans and marker redraws.
 // Click on a road locks both road details and the collision search location.
 map.on('mousemove',function(event){
   if(locationLocked || !$('pk-follow-cursor').checked) return;
   pendingPoint=event.latlng;
   if(hoverTimer!==null) clearTimeout(hoverTimer);
   hoverTimer=setTimeout(function(){
     hoverTimer=null;
     if(locationLocked || !$('pk-follow-cursor').checked || !pendingPoint) return;
     if(activePoint && map.distance(activePoint,pendingPoint)<8)return;
     activePoint=pendingPoint;
     collisionRender();
   },180);
 });
 $('pk-follow-cursor').addEventListener('change',function(){
   if(this.checked){locationLocked=false;locked=false;rankRender()}
 });
 function selection(){return [...yearBox.querySelectorAll('input:checked')].map(x=>x.value)}
 function aggregate(p,selected){const vals=[0,0,0,0];selected.forEach(y=>{const arr=p.years[y]||[0,0,0,0];arr.forEach((n,i)=>vals[i]+=n)});return vals}
 function stats(vals){const total=vals.reduce((s,v)=>s+v,0);return {total,IS:vals[0],VA:vals[1],WR:vals[2],VS:vals[3],VA_rate:total?100*vals[1]/total:null,WR_rate:total?100*vals[2]/total:null}}
 function selectedValue(p,ys,field){return stats(aggregate(p,ys))[field]}
 function getValue(p){const field=metric.value;if(mode.value==='filter')return selectedValue(p,selection(),field);const av=selectedValue(p,[a.value],field),bv=selectedValue(p,[b.value],field);return (bv??0)-(av??0)}
 function eligible(p){const field=metric.value;if(!field.endsWith('_rate'))return true;const threshold=Number(min.value);return mode.value==='filter'?stats(aggregate(p,selection())).total>=threshold:stats(aggregate(p,[a.value])).total>=threshold&&stats(aggregate(p,[b.value])).total>=threshold}
 function showDetail(p){const ys=mode.value==='filter'?selection():[a.value,b.value];let content='<b>'+p.road+'</b><br>Road match: '+p.join+'<br><table style="font-size:11px;margin-top:5px"><tr><th>Year</th><th>Total</th><th>IS</th><th>VA</th><th>WR</th><th>VS</th></tr>';
  [...new Set(ys)].sort().forEach(y=>{const s=stats(aggregate(p,[y]));content+='<tr>'+[y,s.total,s.IS,s.VA,s.WR,s.VS].map(v=>'<td style="padding:2px 4px">'+v+'</td>').join('')+'</tr>'});
  detail.innerHTML=content+'</table><small>Values are assigned to this road segment; multiple segments may share a ticket block.</small>';
 }
 function rankRender(){
  if(!activeRoad){$('pk-rank-subtitle').textContent='Hover over a road segment';rankItems.innerHTML='<p style="color:#64748b">Move your mouse over a street to see the ten most common infraction descriptions.</p>';return}
  const p=activeRoad,compare=mode.value==='compare',ys=compare?[a.value,b.value]:selection();
  $('pk-rank-subtitle').textContent=p.road+' · '+(compare?a.value+' → '+b.value:ys.join(', ')||'No years')+(locked?' · PINNED':' · FOLLOWING MOUSE');
  const getCounts=(years)=>{const result=new Map();const uniqueKeys=new Set(p.blockKeys||[]);uniqueKeys.forEach(k=>{const data=infraData[k];if(!data)return;years.forEach(y=>{(data[y]||[]).forEach(([code,n])=>result.set(code,(result.get(code)||0)+n))})});return result};
  const current=getCounts(ys),base=compare?getCounts([a.value]):null,next=compare?getCounts([b.value]):null;
  const entries=compare?[...new Set([...base.keys(),...next.keys()])].map(k=>[k,(next.get(k)||0)-(base.get(k)||0),next.get(k)||0,base.get(k)||0]):[...current].map(([k,v])=>[k,v,v,0]);
  // Missing descriptions are tracked separately, never ranked as an infraction type.
  const missingCode=infraNames.indexOf('(Missing infraction description)');
  const missingCurrent=missingCode<0?0:(current.get(missingCode)||0);
  const missingBase=compare&&missingCode>=0?(base.get(missingCode)||0):0;
  const missingNext=compare&&missingCode>=0?(next.get(missingCode)||0):0;
  const ranked=entries.filter(row=>row[0]!==missingCode);
  ranked.sort((x,y)=>compare?Math.abs(y[1])-Math.abs(x[1])||y[1]-x[1]:y[1]-x[1]);
  const items=ranked.slice(0,10),max=Math.max(1,...items.map(x=>Math.abs(x[1])));
  const total=[...current.values()].reduce((x,y)=>x+y,0);
  rankItems.innerHTML='';
  const summary=document.createElement('div');summary.style.cssText='background:#f1f5f9;padding:9px;border-radius:7px;margin-bottom:10px;font-size:12px';
  summary.textContent=compare?'Infraction differences (right year − left year)':'Tickets in this block: '+total.toLocaleString();rankItems.appendChild(summary);
  const missing=document.createElement('div');missing.style.cssText='padding:8px 10px;margin-bottom:10px;border:1px solid #fcd34d;background:#fffbeb;border-radius:7px;font-size:12px;line-height:1.5;color:#78350f';
  if(compare){
    missing.textContent='Missing descriptions (not ranked): '+missingBase.toLocaleString()+' → '+missingNext.toLocaleString()+' (change '+((missingNext-missingBase)>0?'+':'')+(missingNext-missingBase).toLocaleString()+')';
  }else{
    missing.textContent='Missing descriptions (not ranked): '+missingCurrent.toLocaleString()+' ('+(total?(100*missingCurrent/total).toFixed(1):'0.0')+'% of all tickets)';
  }
  rankItems.appendChild(missing);
  if(!items.length){rankItems.insertAdjacentHTML('beforeend','<p>No matched tickets for this block and selected years.</p>');return}
  items.forEach(([code,value,newCount,oldCount],i)=>{
   const item=document.createElement('div');item.style.cssText='padding:7px 0;border-bottom:1px solid #e2e8f0';
   const name=document.createElement('div');name.style.cssText='font-size:11px;line-height:1.35;overflow-wrap:anywhere';name.textContent=(i+1)+'. '+infraNames[code];
   const count=document.createElement('div');count.style.cssText='text-align:right;font-weight:600;margin-top:3px;font-size:12px';
   count.textContent=compare?(value>0?'+':'')+value.toLocaleString()+' ('+oldCount.toLocaleString()+' → '+newCount.toLocaleString()+')':value.toLocaleString()+' · '+(total?((100*value/total).toFixed(1)):'0')+'%';
   const track=document.createElement('div');track.style.cssText='height:6px;background:#e2e8f0;border-radius:5px;margin-top:5px';
   const fill=document.createElement('div');fill.style.cssText='height:6px;border-radius:5px;width:'+(100*Math.abs(value)/max)+'%;background:'+(compare&&value<0?'#3b82f6':'#df6974');track.appendChild(fill);
   item.append(name,count,track);rankItems.appendChild(item);
  });
 }
 function collisionRender(){
  const out=$('pk-collision-content');
  if(!activePoint){if(map.hasLayer(searchCircle))map.removeLayer(searchCircle)}
  else if($('pk-collision-circle').checked){searchCircle.setLatLng(activePoint);searchCircle.setRadius(Number($('pk-radius').value));if(!map.hasLayer(searchCircle))searchCircle.addTo(map)}
  else if(map.hasLayer(searchCircle))map.removeLayer(searchCircle);
  if(!activePoint){collisionMarkers.clearLayers();out.textContent='Move your mouse over the map to inspect nearby collisions; click a road to lock the location.';return}
  const radius=Number($('pk-radius').value);
  const selected=mode.value==='compare'?[a.value,b.value]:selection();
  const allowed=new Set(selected.map(Number));let total=0,casualty=0,ped=0,cyclist=0,parked=0,locations=0;
  const yearly=new Map(),near=[],configCounts=new Map();
  const lat=activePoint.lat,lon=activePoint.lng,latDelta=radius/111132,lonDelta=radius/(111320*Math.cos(lat*Math.PI/180));
  nearbyCandidates(lat,lon,latDelta,lonDelta).forEach(r=>{if(!allowed.has(r[2])||Math.abs(r[0]-lat)>latDelta||Math.abs(r[1]-lon)>lonDelta)return;
   const dy=(r[0]-lat)*111132,dx=(r[1]-lon)*111320*Math.cos(lat*Math.PI/180);
   if(dx*dx+dy*dy>radius*radius)return;
   total+=r[3];casualty+=r[4];ped+=r[5];cyclist+=r[6];parked+=r[7];locations++;
   yearly.set(r[2],(yearly.get(r[2])||0)+r[3]);configCounts.set(r[8],(configCounts.get(r[8])||0)+r[3]);near.push(r);
  });
  const fmtN=n=>n.toLocaleString();
  out.innerHTML='<div style="font-weight:600;margin-bottom:8px">Selected location: '+lat.toFixed(5)+', '+lon.toFixed(5)+' · within '+radius+' m · '+(selected.join(', ')||'No years')+'</div>'+
   '<div style="display:grid;grid-template-columns:repeat(5,minmax(110px,1fr));gap:8px">'+
   [['Total crashes',total],['Casualty crashes',casualty],['Pedestrian-related',ped],['Cyclist-related',cyclist],['Parked-vehicle flag',parked]].map(([k,v])=>'<div style="background:#f1f5f9;border-radius:7px;padding:8px"><div style="font-size:11px;color:#475569">'+k+'</div><div style="font-size:20px;font-weight:bold">'+fmtN(v)+'</div></div>').join('')+'</div>'+
   '<div style="margin-top:8px;font-size:12px">Yearly crashes: '+[2021,2022,2023,2024,2025].filter(y=>allowed.has(y)).map(y=>y+': '+fmtN(yearly.get(y)||0)).join(' · ')+' · Matched location-year groups: '+fmtN(locations)+'</div>';
  // Crash configuration is collision geometry, not a verified cause of the crash.
  const unknownNames=new Set(['UNDETERMINED','CONFLICTED','UNKNOWN','UNKNOWN / MISSING','NOT STATED']);
  const unknownCount=[...configCounts].filter(([k])=>unknownNames.has(collisionNames[k])).reduce((s,[k,v])=>s+v,0);
  // Merge closely related configurations without treating them as causal explanations.
  const groupName=name=>{
   if(name.startsWith('SIDE SWIPE'))return 'Sideswipe (either direction)';
   if(name==='SIDE IMPACT')return 'Side impact';
   if(name==='REAR END')return 'Rear-end collision';
   if(name==='SINGLE VEHICLE')return 'Single-vehicle collision';
   if(name==='HEAD ON')return 'Head-on collision';
   if(name==='REAR TO REAR')return 'Rear-to-rear collision';
   if(name==='MULTIPLE IMPACTS')return 'Multiple impacts';
   if(name==='OVERTAKING')return 'Overtaking collision';
   return name.toLowerCase();
  };
  const merged=new Map();
  configCounts.forEach((n,k)=>{const name=collisionNames[k];if(unknownNames.has(name))return;
   const label=groupName(name);merged.set(label,(merged.get(label)||0)+n);
  });
  const types=[...merged].sort((a,b)=>b[1]-a[1]).slice(0,10);
  const maxType=Math.max(1,...types.map(x=>x[1]));
  const typeHtml=types.length?types.map(([k,n],i)=>'<div style="margin:7px 0"><div style="display:flex;justify-content:space-between;gap:12px"><span>'+(i+1)+'. '+k+'</span><b>'+fmtN(n)+' · '+(total?100*n/total:0).toFixed(1)+'%</b></div><div style="height:7px;background:#e2e8f0;border-radius:4px;margin-top:4px"><div style="width:'+(100*n/maxType)+'%;height:7px;background:#8b5cf6;border-radius:4px"></div></div></div>').join(''):'No classified crash configurations in the selected area.';
  const propertyDamage=total-casualty;
  out.innerHTML+='<div style="display:grid;grid-template-columns: minmax(260px,1.5fr) minmax(220px,1fr);gap:16px;margin-top:12px;align-items:start">'+
   '<section style="border:1px solid #e2e8f0;border-radius:8px;padding:10px"><b>Top Crash Types · Grouped</b><div style="font-size:11px;color:#64748b;margin-top:3px">Related crash configurations combined (e.g. both sideswipe directions). Shares use all mapped crashes; unknown/conflicted shown separately</div>'+typeHtml+'<div style="font-size:11px;background:#fff7ed;padding:7px;margin-top:8px;border-radius:5px">Undetermined / conflicted: '+fmtN(unknownCount)+' ('+(total?100*unknownCount/total:0).toFixed(1)+'%)</div></section>'+
   '<section style="border:1px solid #e2e8f0;border-radius:8px;padding:10px"><b>Severity & Involvement</b><div style="font-size:11px;color:#64748b;margin:4px 0 9px">Counts are crash records, not victims or proven causes.</div>'+
   [['Casualty crashes',casualty],['Property damage only',propertyDamage],['Severity-weighted score (3:1)',3*casualty+propertyDamage],['Casualty rate (%)',total?100*casualty/total:0],['Pedestrian-related',ped],['Cyclist-related',cyclist],['Parked-vehicle-related',parked]].map(([label,n])=>'<div style="display:flex;justify-content:space-between;border-bottom:1px solid #e2e8f0;padding:6px 0"><span>'+label+'</span><b>'+(label.includes('score')?fmtN(n):label.includes('rate')?n.toFixed(1)+'%':fmtN(n)+' · '+(total?100*n/total:0).toFixed(1)+'%')+'</b></div>').join('')+
   '<p style="font-size:10px;color:#64748b">Involvement flags overlap: do not add their percentages. A casualty crash is not necessarily a fatal crash.</p></section></div>';
  // Merge records with identical approximate coordinates across years and crash types.
  // Each visible dot represents a matched LOCATION, not an individual collision.
  collisionMarkers.clearLayers();
  if($('pk-collision-points').checked){
   const byLocation=new Map();
   near.forEach(r=>{const key=r[0].toFixed(5)+','+r[1].toFixed(5);
    if(!byLocation.has(key))byLocation.set(key,{lat:r[0],lon:r[1],n:0,casualty:0});
    const p=byLocation.get(key);p.n+=r[3];p.casualty+=r[4];
   });
   [...byLocation.values()].sort((x,y)=>y.n-x.n).slice(0,600).forEach(p=>{
    const size=Math.min(10,Math.max(3,3+Math.sqrt(p.n)*.55));
    L.circleMarker([p.lat,p.lon],{radius:size,color:'#6d28d9',weight:1.4,
      fillColor:'#a78bfa',fillOpacity:.85,interactive:true})
     .bindTooltip('<b>Approximate crash location</b><br>Crashes: '+fmtN(p.n)+
       '<br>Casualty crashes: '+fmtN(p.casualty)+'<br>Selected years and radius',
       {direction:'top'}).addTo(collisionMarkers);
   });
  }
 }
 ['pk-radius','pk-collision-points','pk-collision-circle'].forEach(id=>$(id).addEventListener('change',collisionRender));
 const layerChoice=$('pk-layer'), cmetric=$('pk-cmetric'),topN=$('pk-topn');
 const hTop=$('pk-h-top'),hImproved=$('pk-h-improved'),hDeteriorated=$('pk-h-deteriorated');
 yearBox.addEventListener('pointerdown',e=>{const label=e.target.closest('label');if(label){const input=label.querySelector('input');if(input&&input.value==='2020'&&$('pk-layer').value!=='parking'){e.preventDefault();explain(no2020)}}},true);
 [hImproved,hDeteriorated].forEach(el=>el.addEventListener('change',()=>{if(el.checked&&mode.value!=='compare')explain(noChanges)}));
 $('pk-h-all').addEventListener('click',()=>{if(mode.value!=='compare')explain(noChanges)});
 [a,b].forEach(el=>el.addEventListener('change',()=>{if($('pk-layer').value!=='parking'&&el.value==='2020'){explain(no2020);el.value=el===a?'2021':'2025'}else if(a.value===b.value){explain('Select two different years to measure change. The same year compared with itself has zero change.')};}));
 mode.addEventListener('change',()=>{if(mode.value!=='compare'&&(hImproved.checked||hDeteriorated.checked))explain(noChanges)});

 function highlightFlags(){return {top:hTop.checked,improved:hImproved.checked&&mode.value==='compare',deteriorated:hDeteriorated.checked&&mode.value==='compare'}}
 const crashPalette=['#ede9fe','#c4b5fd','#a78bfa','#7c3aed','#4c1d95'];
 function currentYears(){return mode.value==='compare'?[a.value,b.value]:selection()}
 function crashValue(p,ys){return ys.reduce((sum,y)=>sum+((p.crashes||{})[y]||[0,0,0,0,0,0])[Number(cmetric.value)],0)}
 function currentMetric(p,ys){return layerChoice.value==='parking'?selectedValue(p,ys,metric.value):crashValue(p,ys)}
 function unifiedLegend(){
  if(layerChoice.value==='compare')return '<b>Parking vs. Collisions</b><div style="margin-top:5px">🟥 High parking only · 🟪 High crashes only<br>🟧 High both · Grey = low both</div><small>Relative to each metric’s road-level 75th percentile; spatial association, not causation.</small>';
  return '<b>ICBC road-level '+cmetric.options[cmetric.selectedIndex].text+'</b><div style="display:flex;margin:5px 0">'+(mode.value==='compare'?['#0d9488','#99f6e4','#e2e8f0','#fdba74','#ea580c']:crashPalette).map(c=>'<span style="flex:1;height:12px;background:'+c+'"></span>').join('')+'</div><small>'+(mode.value==='compare'?'Decrease → Increase':'Lower → Higher')+' · approximate road assignment</small>';
 }
 function applyUnifiedMap(){
  const choice=layerChoice.value,compare=mode.value==='compare',ys=currentYears(),yearA=[a.value],yearB=[b.value],n=Number(topN.value);
  $('pk-parking-metric').style.display=choice==='collision'?'none':'block';
  $('pk-crash-metric').style.display=choice==='parking'?'none':'block';
  $('pk-road-note').textContent=choice==='parking'?'Ticket road-label counts may repeat across geometry segments.':'Road-level crashes exclude ambiguous nearest-road matches; exact incident locations are not available.';
  yearBox.querySelectorAll('input').forEach(x=>{x.disabled=choice!=='parking'&&x.value==='2020';if(x.disabled){x.checked=false;x.parentElement.title=no2020;x.parentElement.style.cursor='help'}else{x.parentElement.title='';x.parentElement.style.cursor='pointer'}});
  [...a.options,...b.options].forEach(o=>{o.disabled=false;o.title=o.value==='2020'&&choice!=='parking'?no2020:''});
  if(choice!=='parking'){if(a.value==='2020')a.value='2021';if(b.value==='2020')b.value='2025'}
  const flags=highlightFlags();
  if(choice==='parking'){
   const scores=new Map();lines.forEach(l=>{const p=l.feature.properties;if(!scores.has(p.road))scores.set(p.road,{
     volume:selectedValue(p,compare?yearB:ys,metric.value),delta:selectedValue(p,yearB,metric.value)-selectedValue(p,yearA,metric.value)
   })});
   const entries=[...scores].filter(x=>Number.isFinite(x[1].volume)&&Number.isFinite(x[1].delta));
   const topSet=new Set(flags.top?[...entries].filter(x=>x[1].volume>0).sort((x,y)=>y[1].volume-x[1].volume).slice(0,n).map(x=>x[0]):[]);
   const goodSet=new Set(flags.improved?[...entries].filter(x=>x[1].delta<0).sort((x,y)=>x[1].delta-y[1].delta).slice(0,n).map(x=>x[0]):[]);
   const badSet=new Set(flags.deteriorated?[...entries].filter(x=>x[1].delta>0).sort((x,y)=>y[1].delta-x[1].delta).slice(0,n).map(x=>x[0]):[]);
   lines.forEach(l=>{const road=l.feature.properties.road,isTop=topSet.has(road),good=goodSet.has(road),bad=badSet.has(road);
     if(isTop||good||bad)l.setStyle({weight:7,color:good?'#0d9488':bad?'#ea580c':'#6d28d9',opacity:1,dashArray:isTop&&(good||bad)?'9 4':null});
   });
   $('pk-road-note').textContent='Active road highlights: '+[flags.top?'Top '+topSet.size:null,flags.improved?'Improved '+goodSet.size:null,flags.deteriorated?'Deteriorated '+badSet.size:null].filter(Boolean).join(' · ')+(mode.value!=='compare'&&(hImproved.checked||hDeteriorated.checked)?' · Select Year Comparison for change highlights.':'');
   return;
  }
  const unique=new Map();lines.forEach(l=>{const p=l.feature.properties;if(!unique.has(p.road))unique.set(p.road,p)});
  const vals=[...unique].map(([key,p])=>({key,p,crash:compare?crashValue(p,yearB)-crashValue(p,yearA):crashValue(p,ys),volume:crashValue(p,compare?yearB:ys),park:currentMetric(p,ys)}));
  const nonzero=vals.filter(x=>compare?x.crash!==0:x.crash>0);
  const cuts=nonzero.length?[.2,.4,.6,.8].map(q=>quantile(nonzero.map(x=>x.crash),q)):[0,0,0,0];
  const parkCut=quantile(vals.map(x=>selectedValue(x.p,ys,metric.value)),.75),crashCut=quantile(vals.map(x=>crashValue(x.p,ys)),.75);
  const topSet=new Set(flags.top?[...vals].filter(x=>x.volume>0).sort((x,y)=>y.volume-x.volume).slice(0,n).map(x=>x.key):[]);
  const goodSet=new Set(flags.improved?[...vals].filter(x=>x.crash<0).sort((x,y)=>x.crash-y.crash).slice(0,n).map(x=>x.key):[]);
  const badSet=new Set(flags.deteriorated?[...vals].filter(x=>x.crash>0).sort((x,y)=>y.crash-x.crash).slice(0,n).map(x=>x.key):[]);
  const selected=new Set([...topSet,...goodSet,...badSet]);
  const lookup=new Map(vals.map(x=>[x.key,x]));const maxAbs=Math.max(1,...vals.map(x=>Math.abs(x.crash)));
  lines.forEach(l=>{const p=l.feature.properties,x=lookup.get(p.road),v=x.crash;
   if(!v&&choice==='collision'){l.setStyle({color:'#cbd5e1',weight:1,opacity:streets.checked?.45:0});return}
   let color;
   if(choice==='compare'){
    const hp=selectedValue(p,ys,metric.value)>parkCut,hc=crashValue(p,ys)>crashCut;
    color=hp&&hc?'#c2410c':hp?'#ef4444':hc?'#8b5cf6':'#cbd5e1';
   }else if(compare){color=v<0?'#0d9488':v>0?'#ea580c':'#cbd5e1'}
   else{let i=0;cuts.forEach(c=>{if(v>c)i++});color=crashPalette[Math.min(4,i)]}
   const isTop=topSet.has(p.road),good=goodSet.has(p.road),bad=badSet.has(p.road);
   if(good)color='#0d9488';else if(bad)color='#ea580c';else if(isTop)color='#6d28d9';
   l.setStyle({color,weight:selected.has(p.road)?7:choice==='compare'?3.5:4.5,opacity:.94,interactive:true,dashArray:isTop&&(good||bad)?'9 4':null});
  });
  $('pk-road-note').textContent='Active road highlights: '+[flags.top?'Top '+topSet.size:null,flags.improved?'Improved '+goodSet.size:null,flags.deteriorated?'Deteriorated '+badSet.size:null].filter(Boolean).join(' · ')+(mode.value!=='compare'&&(hImproved.checked||hDeteriorated.checked)?' · Select Year Comparison for change highlights.':'');
  const totalRoads=nonzero.length;summary.innerHTML='<b>'+ (choice==='compare'?'Parking vs. Collisions':'Traffic Collisions')+'</b><br>Selected period: '+(compare?a.value+' → '+b.value:ys.join(', '))+'<br>Road labels with nonzero '+(compare?'change':'collision burden')+': '+totalRoads.toLocaleString()+'<br>Highlighted road labels (union): '+selected.size+'<br><small>Road-level matched subset only; not citywide totals or traffic-adjusted risk.</small>';
  if(choice==='compare'){
   const observations=vals.map(x=>({road:x.key,parking:selectedValue(x.p,ys,metric.value),crashes:crashValue(x.p,ys)})).filter(x=>Number.isFinite(x.parking)&&Number.isFinite(x.crashes)&&x.parking>=0&&x.crashes>=0);
   const rankWithTies=(arr)=>{const sorted=arr.map((v,i)=>({v,i})).sort((a,b)=>a.v-b.v),out=new Array(arr.length);let i=0;while(i<sorted.length){let j=i+1;while(j<sorted.length&&sorted[j].v===sorted[i].v)j++;const rank=(i+j+1)/2;for(let k=i;k<j;k++)out[sorted[k].i]=rank;i=j}return out};
   const rp=rankWithTies(observations.map(x=>x.parking)),rc=rankWithTies(observations.map(x=>x.crashes));
   const avg=(rp.length+1)/2;let cross=0,ssP=0,ssC=0;
   rp.forEach((v,i)=>{const dp=v-avg,dc=rc[i]-avg;cross+=dp*dc;ssP+=dp*dp;ssC+=dc*dc});
   const rho=ssP>0&&ssC>0?cross/Math.sqrt(ssP*ssC):null;
   const k=Math.min(n,observations.length),pTop=new Set([...observations].sort((x,y)=>y.parking-x.parking).slice(0,k).map(x=>x.road));
   const cTop=new Set([...observations].sort((x,y)=>y.crashes-x.crashes).slice(0,k).map(x=>x.road));
   const overlap=[...pTop].filter(key=>cTop.has(key)).length;
   const bothHigh=observations.filter(x=>x.parking>parkCut&&x.crashes>crashCut).length;
   $('pk-annual').innerHTML='<b>Comparative Analytics · Road labels</b>'+
    '<div style="margin-top:6px">Matched road labels: <b>'+observations.length.toLocaleString()+'</b></div>'+
    '<div>Spearman rank correlation: <b>'+(rho===null?'N/A':rho.toFixed(3))+'</b></div>'+
    '<div>Top '+k+' overlap: <b>'+overlap+'</b> road labels ('+(k?100*overlap/k:0).toFixed(1)+'% of each Top '+k+')</div>'+
    '<div>High parking + high collisions: <b>'+bothHigh+'</b> labels</div>'+
    '<small style="display:block;margin-top:5px">Descriptive spatial association, not causation. Shared road labels may cover multiple geometries. Rankings are not adjusted for road length, traffic volume or enforcement exposure. Overlap uses fixed Top N with arbitrary tie ordering.</small>';
  }else $('pk-annual').innerHTML='<small>Collision score = 3 × casualty crashes + 1 × property-damage-only crashes. Year filtering also controls nearby collision analysis.</small>';
 }
 layerChoice.addEventListener('change',render);cmetric.addEventListener('change',render);[hTop,hImproved,hDeteriorated,topN].forEach(el=>el.addEventListener('change',render));
 $('pk-h-clear').addEventListener('click',()=>{hTop.checked=hImproved.checked=hDeteriorated.checked=false;render()});
 $('pk-h-all').addEventListener('click',()=>{hTop.checked=hImproved.checked=hDeteriorated.checked=true;render()});
 function render(){
  const compare=mode.value==='compare',field=metric.value,rate=field.endsWith('_rate'),ys=selection();
  $('pk-years').style.display=compare?'none':'block';$('pk-compare').style.display=compare?'block':'none';
  const valid=lines.map(l=>({l,p:l.feature.properties,v:getValue(l.feature.properties)})).filter(o=>eligible(o.p)&&Number.isFinite(o.v)&&(compare?o.v!==0:o.v>0));
  const values=valid.map(o=>o.v);
  const cuts=compare?[0,0,0,0]:values.length?[.2,.4,.6,.8].map(q=>quantile(values,q)):[0,0,0,0];
  const palette=compare?palettes.delta:palettes[field];
  // Rank unique official road labels, never individual geometry segments.
  // Positive B-A means more recorded tickets; negative means fewer.
  const changes=new Map();
  if(compare){valid.forEach(o=>{if(!changes.has(o.p.road))changes.set(o.p.road,o.v);});}
  const improvements=[...changes].filter(([name,v])=>v<0).sort((x,y)=>x[1]-y[1]).slice(0,150);
  const deteriorations=[...changes].filter(([name,v])=>v>0).sort((x,y)=>y[1]-x[1]).slice(0,150);
  const bestSet=new Set(improvements.map(x=>x[0])),worstSet=new Set(deteriorations.map(x=>x[0]));
  best.disabled=!compare;worst.disabled=!compare;
  highlightSummary.textContent=compare?'Available: '+improvements.length+' improved and '+deteriorations.length+' deteriorated road labels (selected metric).':'Select Compare two years to enable these highlights.';
  const abs=values.length?Math.max(...values.map(Math.abs)):1;
  lines.forEach(l=>{const p=l.feature.properties,v=getValue(p),active=eligible(p)&&Number.isFinite(v)&&(compare?v!==0:v>0);
   if(!active){l.setStyle({color:'#cbd5e1',weight:1,opacity:streets.checked?.45:0,interactive:streets.checked});return}
   let color;if(compare){const ratio=v/(abs||1);color=ratio<=-.5?palette[0]:ratio<0?palette[1]:ratio===0?palette[2]:ratio<.5?palette[3]:palette[4]}
   else{let i=0;cuts.forEach(c=>{if(v>c)i++});color=palette[Math.min(i,4)]}
   const improved=compare&&best.checked&&bestSet.has(p.road);
   const deteriorated=compare&&worst.checked&&worstSet.has(p.road);
   l.setStyle({color:improved?'#1d4ed8':deteriorated?'#b91c1c':color,weight:(improved||deteriorated)?7:4.5,opacity:.95,interactive:true});
  });
  const agg=(ys)=>{const result=[0,0,0,0];ys.forEach(y=>{const d=annual[y];if(d)statuses.forEach((s,i)=>result[i]+=d[s])});return stats(result)};
  if(compare){const aa=agg([a.value]),bb=agg([b.value]);const dv=field.endsWith('_rate')?((bb[field]||0)-(aa[field]||0)).toFixed(2)+' pp':(bb[field]-aa[field]).toLocaleString();summary.innerHTML='<b>'+a.value+' → '+b.value+'</b><br>'+field+': '+fmt(aa[field])+' → '+fmt(bb[field])+'<br>Difference: <b>'+dv+'</b><br><small>Totals from unique cleaned tickets, not mapped segments.</small>'}
  else{const s=agg(ys);summary.innerHTML='<b>'+ (ys.length?ys.join(', '):'No years selected')+'</b><br>Tickets: '+s.total.toLocaleString()+'<br>IS: '+s.IS.toLocaleString()+' · VA: '+s.VA.toLocaleString()+'<br>WR: '+s.WR.toLocaleString()+' · VS: '+s.VS.toLocaleString()+'<br><small>Totals from unique cleaned tickets.</small>'}
  const barYears=compare?[a.value,b.value]:ys;const barMetric=field;const series=barYears.map(y=>({y,v:agg([y])[barMetric]??0}));const maxBar=Math.max(1,...series.map(x=>x.v));$('pk-annual').innerHTML='<b>Year-by-year '+barMetric+'</b>'+series.map(x=>'<div style="display:flex;align-items:center;gap:5px;margin-top:4px;font-size:11px"><span style="width:35px">'+x.y+'</span><div style="height:10px;background:#e2e8f0;flex:1"><div style="height:10px;width:'+(100*x.v/maxBar)+'%;background:#64748b"></div></div><span style="min-width:55px;text-align:right">'+fmt(x.v)+'</span></div>').join('');
  rankRender();collisionRender();
  applyUnifiedMap();
  const grad=palette.map(c=>'<span style="flex:1;height:12px;background:'+c+'"></span>').join('');legend.innerHTML='<b>'+ (compare?'Difference (B − A)':field)+'</b><div style="display:flex;margin:5px 0">'+grad+'</div><div style="display:flex;justify-content:space-between;font-size:11px"><span>'+(compare?'Decrease':'Lower')+'</span><span>'+(compare?'Increase':'Higher')+'</span></div>'+(rate?'<small>Shares: ≥'+min.value+' tickets per period</small>':'');
  if($('pk-layer').value!=='parking')legend.innerHTML=unifiedLegend();
 }
 function fmt(v){return v==null?'N/A':Number(v).toLocaleString(undefined,{maximumFractionDigits:2})}
 function quantile(v,q){const sorted=v.slice().sort((x,y)=>x-y);const at=(sorted.length-1)*q,lo=Math.floor(at),hi=Math.ceil(at);return sorted[lo]+(sorted[hi]-sorted[lo])*(at-lo)}
 [mode,metric,min,streets,best,worst,a,b].forEach(el=>el.addEventListener('change',render));yearBox.addEventListener('change',render);
 $('pk-all').addEventListener('click',()=>{yearBox.querySelectorAll('input').forEach(el=>el.checked=!el.disabled);render()});
 $('pk-none').addEventListener('click',()=>{yearBox.querySelectorAll('input').forEach(el=>el.checked=false);render()});
 render();
});
'''.replace('MAPVAR',m.get_name()).replace('GEOVAR',geo.get_name()).replace('ANNUAL',json.dumps(annual)).replace('PALETTES',json.dumps(PALETTES)).replace('INFRADATA',json.dumps(infra_data,separators=(',',':'),ensure_ascii=False)).replace('INFRANAMES',json.dumps(infra_names,ensure_ascii=False)).replace('COLLISIONDATA',json.dumps(collisions,separators=(',',':'))).replace('COLLISIONNAMES',json.dumps(collision_names,ensure_ascii=False))
 m.get_root().script.add_child(folium.Element(js))
 output=OUT/'vancouver_road_safety_dashboard_v12_4.html'
 m.save(str(output))
 (OUT/'annual_ticket_summary_v6.csv').write_text('Year,Total,IS,VA,WR,VS\n'+''.join(f"{y},{annual[y]['total']},{annual[y]['IS']},{annual[y]['VA']},{annual[y]['WR']},{annual[y]['VS']}\n" for y in YEARS),encoding='utf-8')
 print('Saved:',output,'| bytes:',output.stat().st_size,flush=True)
 print('Annual summary:',OUT/'annual_ticket_summary_v6.csv',flush=True)

if __name__=='__main__':build()
