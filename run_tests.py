"""Non-destructive release QA. Standard library only; never rebuilds or edits source datasets."""
from pathlib import Path
import argparse, ast, csv, datetime, hashlib, html, json, re, sys

from project_paths import ROOT, RAW, QUALITY, COLLISION, MAPS
ROOT = Path(__file__).resolve().parent
SCRIPTS = ['01_add_coordinates.py','02_add_block_info.py','03_audit_and_clean.py','04_local_street_map.py','05_collision_extension.py','06_review_collision_matches.py','04_vancouver_road_safety_dashboard_v12_4.py']
INPUTS = ['parking-tickets-2020-2025.csv','public-streets.csv','block-numbers.csv','Lower Mainland_Full Data_data.csv']
OUTPUTS = ['processed/03_quality_results/parking_tickets_clean_geocoded.csv','processed/05_collision_results/collision_locations.csv']

def run(full=False):
    checks=[]
    def add(group,name,status,detail):checks.append(dict(group=group,name=name,status=status,detail=str(detail)))
    for filename in SCRIPTS:
        p=ROOT/filename
        if not p.exists():add('Code',filename,'FAIL','Missing source file');continue
        try:ast.parse(p.read_text(encoding='utf-8-sig'));add('Code',filename,'PASS','Python syntax valid')
        except (SyntaxError,UnicodeError) as exc:add('Code',filename,'FAIL',str(exc))
    req=ROOT/'requirements.txt'
    if req.exists():
        dependencies={line.strip().split('>')[0].split('=')[0].split('<')[0].lower() for line in req.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')}
        missing={'pandas','numpy','scipy','folium','shapely'}-dependencies
        add('Release','Required Python dependencies','FAIL' if missing else 'PASS',f'Missing: {sorted(missing)}' if missing else 'All five core packages declared')
    else:add('Release','Required Python dependencies','FAIL','Missing requirements.txt')
    for name in ['README.md','Dockerfile','run_dashboard.bat','rebuild_all.bat','docs/RUNBOOK.md','docs/METHODOLOGY.md','docs/DATA_QUALITY.md']:
        add('Release',name,'PASS' if (ROOT/name).is_file() else 'FAIL','File exists' if (ROOT/name).is_file() else 'File missing')
    for name in ['run_dashboard.bat','rebuild_all.bat']:
        p=ROOT/name
        if p.exists():
            txt=p.read_text(errors='replace')
            add('Release',f'{name}: v12.4 target','PASS' if '04_vancouver_road_safety_dashboard_v12_4.py' in txt else 'FAIL','Expected v12.4 entry point')
    add('Release','Central data path configuration','PASS' if (ROOT/'project_paths.py').is_file() else 'FAIL','data_source paths configured')
    for name in INPUTS:
        p=RAW/name
        add('Data',f'Raw input: {name}','PASS' if p.is_file() else ('SKIP' if not full else 'FAIL'), 'Available locally' if p.is_file() else 'Not bundled; supply locally for full rebuild')
    for name in OUTPUTS:
        p=ROOT/'data_source'/name
        add('Data',f'Processed output: {name}','PASS' if p.is_file() else ('SKIP' if not full else 'FAIL'),'Available locally' if p.is_file() else 'Missing; run pipeline on local source data')
    dashboard=ROOT/'site'/'index.html'
    if not dashboard.is_file():add('Dashboard','Published HTML','FAIL','site/index.html is missing')
    else:
        page=dashboard.read_text(encoding='utf-8',errors='replace')
        add('Dashboard','HTML document','PASS' if '<html' in page.lower() and '</html>' in page.lower() else 'FAIL','HTML document boundaries')
        for name, token in [('Layer selector','pk-layer'),('Year selector','pk-year-box'),('Year comparison','pk-compare'),('Road highlights','pk-h-top'),('Infraction ranking','pk-ranking'),('Collision detail','pk-collision'),('Radius selector','pk-radius'),('Map layer','leaflet')]:
            add('Dashboard',name,'PASS' if token in page else 'FAIL','Static HTML token present' if token in page else 'Expected token absent')
        add('Dashboard','Interactive behavior','SKIP','Requires browser testing; static HTML inspection cannot prove functionality')
        add('Dashboard','External JavaScript/CSS','WARN' if 'https://' in page else 'PASS','HTML references remote assets; offline use may be incomplete' if 'https://' in page else 'No HTTPS references found')
        add('Dashboard','HTML size','WARN' if dashboard.stat().st_size>20_000_000 else 'PASS',f'{dashboard.stat().st_size/1e6:.2f} MB')
    # Compare output and published HTML when a local freshly generated file is available.
    generated=MAPS/'vancouver_road_safety_dashboard_v12_4.html'
    if generated.is_file() and dashboard.is_file():
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        same=digest(generated)==digest(dashboard)
        add('Dashboard','Generated vs published HTML','PASS' if same else 'FAIL','SHA256 identical' if same else 'Files differ; republish site/index.html')
    else:add('Dashboard','Generated vs published HTML','SKIP','Generated HTML not present; no byte-for-byte comparison')
    if full:
        try:
            import pandas as pd
            clean=ROOT/'data_source'/OUTPUTS[0]
            if clean.exists():
                years={}; statuses={}; rows=0; bad_coords=0
                for chunk in pd.read_csv(clean,sep=';',usecols=['Year','Status','Latitude','Longitude'],chunksize=150000,low_memory=False):
                    rows+=len(chunk)
                    bad_coords+=int((~(pd.to_numeric(chunk.Latitude,errors='coerce').between(49,49.5)&pd.to_numeric(chunk.Longitude,errors='coerce').between(-123.4,-122.9))).sum())
                    for k,v in chunk.Year.value_counts(dropna=False).items():years[str(k)]=years.get(str(k),0)+int(v)
                    for k,v in chunk.Status.value_counts(dropna=False).items():statuses[str(k)]=statuses.get(str(k),0)+int(v)
                add('Data','Cleaned parking coordinate bounds','PASS' if bad_coords==0 else 'FAIL',f'Rows={rows:,}; invalid={bad_coords:,}; year counts={years}; status counts={statuses}')
            collisions=ROOT/'data_source'/OUTPUTS[1]
            if collisions.exists():
                d=pd.read_csv(collisions,usecols=['Crashes','Year','MatchMethod'],low_memory=False)
                total=pd.to_numeric(d.Crashes,errors='coerce')
                add('Data','Collision crash weights','PASS' if total.notna().all() and (total>=0).all() else 'FAIL',f'Grouped rows={len(d):,}; total weighted crashes={total.sum():,.0f}; match methods={d.MatchMethod.value_counts().to_dict()}')
        except ImportError:add('Data','Full pandas checks','FAIL','Install dependencies: python -m pip install -r requirements.txt')
        except Exception as exc:add('Data','Full data checks','FAIL',f'{type(exc).__name__}: {exc}')
    out=ROOT/'validation_results';out.mkdir(exist_ok=True)
    summary={k:sum(x['status']==k for x in checks) for k in ['PASS','FAIL','WARN','SKIP']}
    report={'version':'v1.0 RC2 / dashboard v12.4','mode':'full' if full else 'quick','timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'summary':summary,'checks':checks}
    (out/'test_results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    with (out/'test_results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=['group','name','status','detail']);writer.writeheader();writer.writerows(checks)
    trs=''.join('<tr><td>'+html.escape(c['group'])+'</td><td>'+html.escape(c['name'])+'</td><td class="'+c['status']+'">'+c['status']+'</td><td>'+html.escape(c['detail'])+'</td></tr>' for c in checks)
    document=f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Release QA</title><style>body{{font:15px system-ui,sans-serif;margin:40px auto;max-width:1200px;padding:0 18px;color:#172033}}table{{border-collapse:collapse;width:100%}}th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top;overflow-wrap:anywhere}}.PASS{{color:#167347;font-weight:bold}}.FAIL{{color:#c62828;font-weight:bold}}.SKIP,.WARN{{color:#a15c00;font-weight:bold}}.stats{{font-size:20px;margin:24px 0}}</style><h1>Vancouver Road Safety Analytics — Release QA</h1><p>Mode: {report['mode']} · {report['timestamp_utc']}</p><div class="stats">PASS {summary['PASS']} · FAIL {summary['FAIL']} · WARN {summary['WARN']} · SKIP {summary['SKIP']}</div><p>Static checks do not prove browser interactivity or end-to-end ETL reproducibility. Missing private data is skipped in quick mode.</p><table><thead><tr><th>Group</th><th>Check</th><th>Result</th><th>Evidence</th></tr></thead><tbody>{trs}</tbody></table></html>"""
    (out/'validation_report.html').write_text(document,encoding='utf-8')
    print('QA results:',summary,'\nReport:',out/'validation_report.html')
    return 1 if summary['FAIL'] else 0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Non-destructive release QA')
    parser.add_argument('--full',action='store_true',help='Require local data and audit full processed CSVs (does not rebuild)')
    args=parser.parse_args()
    sys.exit(run(args.full))
