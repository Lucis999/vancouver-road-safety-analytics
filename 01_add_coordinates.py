"""Stage 1: preserve all parking ticket rows, add street-segment coordinates.
Input CSVs are semicolon separated. Run from the folder containing the three CSVs.
"""
from pathlib import Path
import re
import pandas as pd
import numpy as np
from project_paths import ROOT, RAW, INTERMEDIATE, QUALITY, COLLISION, MAPS, ensure_output_dirs
ensure_output_dirs()
ROOT=Path(__file__).resolve().parent
ALIASES={'AVENUE':'AV','AVE':'AV','STREET':'ST','DRIVE':'DR','ROAD':'RD','BOULEVARD':'BLVD','CRESCENT':'CRES','PLACE':'PL','COURT':'CT','LANE':'LN','PARKWAY':'PKWY','TERRACE':'TER','HIGHWAY':'HWY'}
def normalize(x):
    if pd.isna(x): return ''
    return ' '.join(ALIASES.get(w,w) for w in re.sub(r'[^A-Z0-9 ]+',' ',str(x).upper()).split())
def main():
    roads=pd.read_csv(RAW/'public-streets.csv',sep=';',encoding='utf-8-sig',dtype='string')
    m=roads.HBLOCK.str.extract(r'^\s*(\d+)(?:\s*-\s*(\d+))?\s+(.+?)\s*$')
    roads['start']=pd.to_numeric(m[0],errors='coerce');roads['end']=pd.to_numeric(m[1],errors='coerce').fillna(roads.start)
    roads['street_key']=m[2].map(normalize)
    coords=roads.geo_point_2d.str.split(',',n=1,expand=True)
    roads['Latitude']=pd.to_numeric(coords[0],errors='coerce');roads['Longitude']=pd.to_numeric(coords[1],errors='coerce')
    roads=roads.dropna(subset=['start','end','Latitude','Longitude'])
    roads=roads[(roads.start<=roads.end)&roads.street_key.ne('')]
    # Read only unique parking locations to keep matching memory manageable.
    source=RAW/'parking-tickets-2020-2025.csv'
    locs=pd.read_csv(source,sep=';',encoding='utf-8-sig',usecols=['Block','Street'],dtype='string')
    locs=locs.drop_duplicates().reset_index(drop=True)
    locs['block_key']=pd.to_numeric(locs.Block,errors='coerce')
    locs['street_key']=locs.Street.map(normalize)
    locs['id']=np.arange(len(locs))
    cand=locs[['id','block_key','street_key']].merge(roads[['start','end','street_key','Latitude','Longitude','HBLOCK']],on='street_key')
    cand=cand[cand.block_key.between(cand.start,cand.end)].copy()
    cand['priority']=np.where(cand.block_key.eq(cand.start),0,1)
    cand=cand[cand.priority.eq(cand.groupby('id').priority.transform('min'))]
    agg=cand.groupby('id').agg(Latitude=('Latitude','median'),Longitude=('Longitude','median'),CandidateCount=('HBLOCK','size'),priority=('priority','min'),OfficialHBLOCK=('HBLOCK',lambda x:' | '.join(sorted(set(x.astype(str)))[:5]))).reset_index()
    locs=locs.merge(agg,on='id',how='left',validate='one_to_one')
    locs['CoordinateMatchMethod']=np.select([locs.priority.eq(0),locs.priority.eq(1)],['ExactStart','InclusiveRange'],default='Unmatched')
    locs['CoordinateReviewRequired']=locs.CandidateCount.gt(1)
    locs['CoordinateUnmatchedReason']=np.where(locs.CoordinateMatchMethod.ne('Unmatched'),'',np.where(locs.street_key.isin(set(roads.street_key)),'BlockOutsideOfficialRange','StreetNotFoundInOfficialData'))
    lookup=locs.drop(columns=['id','block_key','street_key','priority'])
    lookup.to_csv(INTERMEDIATE/'01_coordinate_lookup.csv',index=False,encoding='utf-8-sig')
    # Stream the 2.47m tickets so the original order, fields, and row count are preserved.
    out=INTERMEDIATE/'parking_tickets_with_coordinates.csv'
    count=0
    for chunk in pd.read_csv(source,sep=';',encoding='utf-8-sig',dtype='string',chunksize=150000):
        enriched=chunk.merge(lookup,on=['Block','Street'],how='left',validate='many_to_one',sort=False)
        enriched.to_csv(out,index=False,encoding='utf-8-sig' if count==0 else 'utf-8',mode='w' if count==0 else 'a',header=count==0)
        count+=len(chunk)
    print('Rows preserved:',count,'| unique locations:',len(lookup),'| output:',out)
    print(lookup.CoordinateMatchMethod.value_counts().to_string())
if __name__=='__main__':main()
