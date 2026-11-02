"""Review ICBC geocoding output; retain all raw records and flag map exclusions.
Run after 05_collision_extension.py. No raw rows are deleted.
"""
from pathlib import Path
import pandas as pd
from project_paths import ROOT, RAW, INTERMEDIATE, QUALITY, COLLISION, MAPS, ensure_output_dirs
ensure_output_dirs()
ROOT=Path(__file__).resolve().parent
folder=COLLISION
source=folder/'collision_locations.csv'
if not source.exists(): raise FileNotFoundError(f'Run 05_collision_extension.py first: {source}')
df=pd.read_csv(source,low_memory=False)
for col in ['Latitude','Longitude','Crashes']:
 df[col]=pd.to_numeric(df[col],errors='coerce')
valid=df.Latitude.between(49.0,49.5)&df.Longitude.between(-123.4,-122.9)
method=df.MatchMethod.fillna('Unmatched')
accepted=method.isin(['Intersection','BlockRange'])&valid
df['MapDecision']=accepted.map({True:'IncludeApproximate',False:'ExcludeFromMap'})
df['ReviewReason']=''
df.loc[~accepted,'ReviewReason']='UnmatchedOrAmbiguous'
df.loc[~valid & method.isin(['Intersection','BlockRange']),'ReviewReason']='InvalidOrMissingCoordinates'
df.loc[method.eq('AmbiguousIntersection'),'ReviewReason']='MultiplePossibleIntersections'
df.loc[method.eq('Unmatched'),'ReviewReason']='UnmatchedLocationDescription'
df.loc[accepted,'ReviewReason']='ApproximateLocationReviewRecommended'
cols=['MapDecision','MatchMethod','ReviewReason']
summary=df.groupby(cols,dropna=False).agg(CSVRows=('Crashes','size'),TotalCrashes=('Crashes','sum')).reset_index()
summary['CrashSharePercent']=(summary.TotalCrashes/df.Crashes.sum()*100).round(2)
folder.mkdir(exist_ok=True)
summary.to_csv(folder/'collision_quality_summary.csv',index=False)
df.loc[~accepted].to_csv(folder/'collision_excluded_review.csv',index=False)
df.loc[accepted].to_csv(folder/'collision_mapped_approximate.csv',index=False)
print(summary.to_string(index=False));print('All original grouped records retained in:',source)
