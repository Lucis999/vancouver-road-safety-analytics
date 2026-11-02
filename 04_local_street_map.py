"""Offline-basemap Vancouver parking map: public-streets.csv + cleaned parking CSV.
Run: python 04_local_street_map.py
No map tile requests. Leaflet JavaScript still loads from CDN on first opening.
"""
from pathlib import Path
import json, re, math, html
import pandas as pd
import folium
from folium.plugins import Fullscreen

from project_paths import ROOT, RAW, INTERMEDIATE, QUALITY, COLLISION, MAPS, ensure_output_dirs
ensure_output_dirs()
ROOT=Path(__file__).resolve().parent
CLEAN=QUALITY/'parking_tickets_clean_geocoded.csv'
FALLBACK=INTERMEDIATE/'parking_matching_v2_results'/'block_geographic_lookup.csv'
STREETS=RAW/'public-streets.csv'
OUT=MAPS
OUT.mkdir(exist_ok=True)

def norm(v):
    s=re.sub(r'\s+',' ',str(v).upper().replace('.',' ').strip())
    for old,new in [('AVENUE','AV'),('AVE','AV'),('STREET','ST'),('DRIVE','DR'),('ROAD','RD'),('BOULEVARD','BLVD'),('CRESCENT','CRES'),('PLACE','PL'),('LANE','LN')]:
        s=re.sub(r'\b'+old+r'\b',new,s)
    return s

def aggregate():
    if CLEAN.exists():
        pieces=[]
        for c in pd.read_csv(CLEAN,sep=';',encoding='utf-8-sig',usecols=['Block','Street'],chunksize=200000):
            pieces.append(c.groupby(['Block','Street'],dropna=False).size().rename('Tickets').reset_index())
        a=pd.concat(pieces).groupby(['Block','Street'],as_index=False)['Tickets'].sum()
        print('Source: CLEAN CSV')
    elif FALLBACK.exists():
        a=pd.read_csv(FALLBACK,usecols=['Block','Street','TicketCount','MatchMethod'])
        a=a[a.MatchMethod!='Unmatched'][['Block','Street','TicketCount']].rename(columns={'TicketCount':'Tickets'})
        print('Source: preview lookup (local clean CSV not present)')
    else:
        raise FileNotFoundError(f'Place {CLEAN} next to script (or use preview lookup)')
    a['blocknum']=pd.to_numeric(a.Block,errors='coerce')
    a['streetkey']=a.Street.map(norm)
    a=a.dropna(subset=['blocknum'])
    a['blocknum']=a.blocknum.astype(int)
    return a

def road_parse(s):
    m=re.match(r'^\s*(\d+)(?:\s*-\s*(\d+))?\s+(.+?)\s*$',str(s))
    if not m:return None
    return int(m[1]),int(m[2] or m[1]),norm(m[3])

def main():
    a=aggregate()
    roads=pd.read_csv(STREETS,sep=';',encoding='utf-8-sig',usecols=['HBLOCK','Geom'],dtype='string')
    # Exact starts preferred, otherwise inclusive-range. Build a street-level lookup.
    from collections import defaultdict
    bystreet=defaultdict(list)
    for r in a.itertuples(index=False):
        bystreet[r.streetkey].append((r.blocknum,int(r.Tickets),str(r.Street)))
    features=[]; assigned=0
    for r in roads.itertuples(index=False):
        parsed=road_parse(r.HBLOCK)
        if not parsed:continue
        lo,hi,key=parsed
        try:
            geom=json.loads(r.Geom)
            if geom.get('type') not in ('LineString','MultiLineString'):continue
            # Trim coordinate precision to reduce browser load.
            if geom['type']=='LineString':
                coords=[[round(float(x),6),round(float(y),6)] for x,y,*_ in geom['coordinates']]
            else:
                coords=[[[round(float(x),6),round(float(y),6)] for x,y,*_ in line] for line in geom['coordinates']]
        except (ValueError,TypeError,KeyError):continue
        candidates=bystreet.get(key,[])
        exact=[(n,t,s) for n,t,s in candidates if n==lo]
        eligible=exact if exact else [(n,t,s) for n,t,s in candidates if lo<=n<=hi]
        # This is a road-segment visualization, NOT a deduplicated ticket total.
        count=sum(t for _,t,_ in eligible)
        if count:assigned+=1
        features.append({'type':'Feature','geometry':{'type':geom['type'],'coordinates':coords},'properties':{'name':str(r.HBLOCK),'tickets':count,'method':'ExactStart' if exact else ('InclusiveRange' if eligible else 'NoMatchedTickets')}})
    positive=[f['properties']['tickets'] for f in features if f['properties']['tickets']>0]
    print('Official road geometries:',len(features),'| colored segments:',assigned)
    # Quantile boundaries for more informative colors than fixed thresholds.
    import numpy as np
    bounds=np.unique(np.quantile(positive,[0,.2,.4,.6,.8,1]).astype(int)).tolist() if positive else [0,1]
    palette=['#fee2e2','#fecaca','#fca5a5','#ef4444','#7f1d1d']
    def col(v):
        if v<=0:return '#b7c0c9'
        idx=sum(v>b for b in bounds[1:-1])
        return palette[min(idx,4)]
    for f in features:f['properties']['color']=col(f['properties']['tickets'])
    m=folium.Map(location=[49.255,-123.12],zoom_start=12,tiles=None,control_scale=True,prefer_canvas=True)
    # Offline street network replaces remote basemap tiles.
    network=folium.FeatureGroup(name='All official streets · grey',show=True)
    colored=folium.FeatureGroup(name='Tickets by street segment · red',show=True)
    base_feats=[f for f in features if not f['properties']['tickets']]
    hot_feats=[f for f in features if f['properties']['tickets']]
    folium.GeoJson({'type':'FeatureCollection','features':base_feats},name='Roads',style_function=lambda f:{'color':'#bdc5ce','weight':1,'opacity':.65},smooth_factor=1).add_to(network)
    folium.GeoJson({'type':'FeatureCollection','features':hot_feats},name='Colored road segments',
        style_function=lambda f:{'color':f['properties']['color'],'weight':4,'opacity':.88},
        highlight_function=lambda f:{'color':'#2563eb','weight':8,'opacity':1},
        tooltip=folium.GeoJsonTooltip(fields=['name','tickets','method'],aliases=['Road block:','Segment ticket count:','Join rule:'],localize=True,sticky=True),
        popup=folium.GeoJsonPopup(fields=['name','tickets','method'],aliases=['Road block','Tickets (segment display)','Join rule'],localize=True)
    ).add_to(colored)
    network.add_to(m);colored.add_to(m)
    Fullscreen().add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    labels=['Low','20%','40%','60%','80%','High']
    legend=''.join(f'<span style="display:inline-block;background:{c};width:25px;height:12px"></span>' for c in palette)
    panel=f'''<div style="position:fixed;bottom:20px;left:20px;z-index:9999;background:white;padding:12px;border:1px solid #ccc;border-radius:6px;font:13px Arial;box-shadow:0 2px 8px #8885"><b>Vancouver parking tickets · Local street network</b><div style="margin:8px 0">{legend}</div>Light = fewer tickets; dark = more tickets<br>Quantile breaks: {html.escape(str(bounds))}<br><small>Road lines, not property polygons. Multiple street<br>segments can display the same block ticket count.<br>Do not sum segment tooltips citywide.</small></div>'''
    m.get_root().html.add_child(folium.Element(panel))
    output=OUT/'vancouver_local_street_map.html';m.save(str(output))
    print('Saved:',output,'| size MB:',round(output.stat().st_size/1e6,2))
    print('IMPORTANT: Map tiles are offline; Leaflet JS/CSS still require internet unless bundled locally.')
if __name__=='__main__':main()
