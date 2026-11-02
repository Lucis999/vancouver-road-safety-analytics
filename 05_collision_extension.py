"""ICBC collision geocoding extension for Vancouver street-segment dashboard.
Inputs: Lower Mainland_Full Data_data.csv, public-streets.csv.
Output: 05_collision_results/collision_locations.csv and matching_audit.csv.
Requires pandas, numpy, shapely. Does not change parking pipeline.
"""
from pathlib import Path
from collections import defaultdict
import re, json
import pandas as pd
from shapely.geometry import shape
from shapely.ops import nearest_points
from shapely.strtree import STRtree
from project_paths import ROOT, RAW, INTERMEDIATE, QUALITY, COLLISION, MAPS, ensure_output_dirs
ensure_output_dirs()
ROOT=Path(__file__).resolve().parent
ICBC=RAW/'Lower Mainland_Full Data_data.csv'
if not ICBC.exists():
 matches=list(RAW.glob('Lower Mainland*csv'))
 if matches:ICBC=matches[0]
ROADS=RAW/'public-streets.csv'
if not ROADS.exists():
 matches=list(RAW.glob('public-streets*.csv'))
 if matches:ROADS=matches[0]
OUT=COLLISION;OUT.mkdir(exist_ok=True)
ALIASES={'AVENUE':'AV','AVE':'AV','STREET':'ST','DRIVE':'DR','ROAD':'RD','BOULEVARD':'BLVD','CRESCENT':'CRES','PLACE':'PL','LANE':'LN','COURT':'CT','HIGHWAY':'HWY'}
def norm(s):
 s=re.sub(r'[^A-Z0-9 ]',' ',str(s).upper());return ' '.join(ALIASES.get(w,w) for w in s.split())
def parse_block(s):
 m=re.match(r'^(.+?)\s*#\s*(\d+)\s+TO\s+(\d+)',str(s));return (norm(m[1]),int(m[2]),int(m[3])) if m else None
def prepare():
 roads=pd.read_csv(ROADS,sep=';',usecols=['HBLOCK','Geom'],dtype='string')
 street=defaultdict(list)
 for r in roads.itertuples(index=False):
  m=re.match(r'^\s*(\d+)(?:\s*-\s*(\d+))?\s+(.+)$',str(r.HBLOCK))
  if not m:continue
  try:g=shape(json.loads(r.Geom))
  except Exception:continue
  street[norm(m[3])].append((int(m[1]),int(m[2] or m[1]),g))
 print('Loaded road names:',len(street),flush=True)
 d=pd.read_csv(ICBC,low_memory=False)
 d=d[d['Municipality Name'].astype(str).str.upper().eq('VANCOUVER')].copy()
 d['Year']=pd.to_numeric(d['Date Of Loss Year'],errors='coerce')
 d['Crashes']=pd.to_numeric(d['Total Crashes'],errors='coerce').fillna(0)
 d['Location']=d['Road Location Description'].fillna('UNKNOWN').astype(str).str.strip()
 # Sum crash weights, never count rows as individual crashes.
 fields=['Location','Year','Crash Severity','Derived Crash Configuration','Pedestrian Flag','Cyclist Flag','Parked Vehicle Flag','Intersection Crash']
 grouped=d.groupby(fields,dropna=False,as_index=False)['Crashes'].sum()
 locs=grouped['Location'].drop_duplicates().tolist()
 cache={}; audit=[]
 for i,loc in enumerate(locs):
  result=None; kind='Unmatched'; precision='none'
  block=parse_block(loc)
  if block:
   key,lo,hi=block
   choices=[g for a,b,g in street.get(key,[]) if a<=hi and b>=lo]
   if choices:
    p=choices[0].interpolate(.5,normalized=True);result=(p.y,p.x);kind='BlockRange';precision='approximate'
  elif loc!='UNKNOWN':
   parts=[norm(x) for x in loc.split(' & ')];names=[x for x in parts if x in street]
   if len(names)>=2:
    first=street[names[0]]; second=street[names[1]]
    # Spatial tree prevents all-pairs scans. Candidate streets may meet in several places;
    # ambiguous intersections are explicitly excluded rather than assigned arbitrarily.
    gs=[g for _,_,g in second];tree=STRtree(gs);hits=[]
    for _,_,g in first:
     for j in tree.query(g.buffer(.00015)):
      h=gs[int(j)];distance=g.distance(h)
      if distance<=.00015:
       p,q=nearest_points(g,h);hits.append(((p.y+q.y)/2,(p.x+q.x)/2,distance))
    unique=[]
    for hit in sorted(hits,key=lambda x:x[2]):
     if all(abs(hit[0]-old[0])>0.00025 or abs(hit[1]-old[1])>0.00025 for old in unique):unique.append(hit)
    if len(unique)==1:
     result=unique[0][:2];kind='Intersection';precision='approximate'
    elif len(unique)>1:kind='AmbiguousIntersection'
  if result is None:cache[loc]=(None,None,kind,precision)
  else:cache[loc]=(*result,kind,precision)
  audit.append({'Location':loc,'Latitude':cache[loc][0],'Longitude':cache[loc][1],'MatchMethod':kind,'Precision':precision})
  if (i+1)%3000==0:print('Matched locations:',i+1,'/',len(locs),flush=True)
 geo=pd.DataFrame(audit);geo.to_csv(OUT/'matching_audit.csv',index=False)
 grouped=grouped.merge(geo,on='Location',how='left',validate='many_to_one')
 grouped.to_csv(OUT/'collision_locations.csv',index=False)
 print('Collision weights by match:',grouped.groupby('MatchMethod')['Crashes'].sum().sort_values(ascending=False).to_dict(),flush=True)
 print('Output:',OUT,flush=True)
if __name__=='__main__':prepare()
