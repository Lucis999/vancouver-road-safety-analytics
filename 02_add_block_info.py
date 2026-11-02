"""Stage 2: add nearest block-number annotation as a spatial reference, NOT a verified parcel boundary.
Requires scipy, pandas, numpy. Input output from stage 1 and block-numbers.csv.
"""
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
from project_paths import ROOT, RAW, INTERMEDIATE, QUALITY, COLLISION, MAPS, ensure_output_dirs
ensure_output_dirs()
ROOT=Path(__file__).resolve().parent
MAX_DISTANCE_M=150

def main():
    labels=pd.read_csv(RAW/'block-numbers.csv',sep=';',encoding='utf-8-sig',dtype='string')
    xy=labels.geo_point_2d.str.split(',',n=1,expand=True)
    labels['label_lat']=pd.to_numeric(xy[0],errors='coerce');labels['label_lon']=pd.to_numeric(xy[1],errors='coerce')
    labels=labels.dropna(subset=['label_lat','label_lon']).reset_index(drop=True)
    # Local equirectangular projection; suitable for short Vancouver distances.
    lat0=np.deg2rad(49.25)
    def project(lat,lon):
        return np.column_stack((np.asarray(lon,dtype=float)*111320*np.cos(lat0),np.asarray(lat,dtype=float)*111132))
    tree=cKDTree(project(labels.label_lat,labels.label_lon))
    lookup=pd.read_csv(INTERMEDIATE/'01_coordinate_lookup.csv',dtype={'Block':'string','Street':'string'})
    lookup['BlockNumberLabel']=pd.NA;lookup['BlockGeoLocalArea']=pd.NA
    lookup['BlockNumberDistanceMeters']=np.nan;lookup['BlockNumberMatchStatus']='NoCoordinate'
    valid=lookup.Latitude.notna() & lookup.Longitude.notna()
    if valid.any():
        dist,idx=tree.query(project(lookup.loc[valid,'Latitude'],lookup.loc[valid,'Longitude']))
        near=labels.iloc[idx].reset_index(drop=True)
        loc=lookup.index[valid]
        ok=dist<=MAX_DISTANCE_M
        matched_idx=loc[ok]
        lookup.loc[matched_idx,'BlockNumberLabel']=near.loc[ok,'LABEL'].to_numpy()
        lookup.loc[matched_idx,'BlockGeoLocalArea']=near.loc[ok,'Geo Local Area'].to_numpy()
        lookup.loc[loc,'BlockNumberDistanceMeters']=np.round(dist,1)
        lookup.loc[loc,'BlockNumberMatchStatus']=np.where(ok,'NearbyAnnotationCandidate','NoNearbyAnnotation')
    # LABEL is NOT guaranteed to equal parking 100-block number. Do not claim verified block.
    lookup.to_csv(INTERMEDIATE/'02_block_annotation_lookup.csv',index=False,encoding='utf-8-sig')
    cols=['Block','Street','BlockNumberLabel','BlockGeoLocalArea','BlockNumberDistanceMeters','BlockNumberMatchStatus']
    source=INTERMEDIATE/'parking_tickets_with_coordinates.csv';out=INTERMEDIATE/'parking_tickets_with_coordinates_and_blocks.csv'
    n=0
    for chunk in pd.read_csv(source,dtype='string',chunksize=150000):
        chunk=chunk.merge(lookup[cols],on=['Block','Street'],how='left',validate='many_to_one',sort=False)
        chunk.to_csv(out,index=False,mode='w' if n==0 else 'a',header=n==0,encoding='utf-8-sig' if n==0 else 'utf-8')
        n+=len(chunk)
    print('Rows preserved:',n,'| output:',out)
    print(lookup.BlockNumberMatchStatus.value_counts().to_string())
if __name__=='__main__':main()
