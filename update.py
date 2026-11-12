#!/usr/bin/env python3
"""Public ADL Insights catalogue archive. Run with --backfill or --update."""
import argparse, csv, datetime as dt, html, json, logging, os, random, re, time
from pathlib import Path
from urllib.parse import urlencode, urljoin
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.table import Table, TableStyleInfo

BASE='https://www.adlittle.com/en/insights_rest'
TYPES=['reports','viewpoints','in_the_press','book','blue_shift_report','insights_hubspot']
HEAD=['Drupal NID','Title','Subtitle','Publication period','Created timestamp','Content type','Industries','Capabilities','Challenges','Excerpt','URL','ENUR relevance','First seen','Last seen','Source API page']

def clean(s): return BeautifulSoup(html.unescape(str(s or '')),'html.parser').get_text(' ',strip=True)
def classify(x):
    ind=clean(x.get('industries',''))
    text=' '.join(clean(x.get(k,'')) for k in ['title','subtitle','body','services','challenges']).lower()
    if 'energy, utilities' in ind: return 'Direct ENUR'
    if re.search(r'energy|electric|hydrogen|decarbon|climat|water|grid|nuclear|mining|chemical|utility|renewable|carbon|battery|industrial',text):return 'Cross-sector review'
    return 'Other / review'
def normalize(x,page,old=None):
    nid=str(x.get('nid','')).strip()
    if not nid: return None
    stamp=dt.datetime.now(dt.timezone.utc).date().isoformat()
    parsed=BeautifulSoup(x.get('created','') or '', 'html.parser').find('time')
    return {'Drupal NID':nid,'Title':clean(x.get('title')),'Subtitle':clean(x.get('subtitle')),
    'Publication period':clean(x.get('field_date_publication')),'Created timestamp':parsed.get('datetime','') if parsed else '',
    'Content type':clean(x.get('field_insight_type') or x.get('type')),'Industries':clean(x.get('industries')),
    'Capabilities':clean(x.get('services')),'Challenges':clean(x.get('challenges')),'Excerpt':clean(x.get('body')),
    'URL':urljoin('https://www.adlittle.com',x.get('node_url') or x.get('node_url_old') or ''),
    'ENUR relevance':classify(x),'First seen':(old or {}).get('First seen',stamp),'Last seen':stamp,'Source API page':page}
def get_page(session,page,attempts=3):
    params=[('type[]',x) for x in TYPES]+[('page',page)]
    for attempt in range(attempts):
        try:
            r=session.get(BASE,params=params,timeout=25)
            if r.status_code in (403,429):raise RuntimeError(f'Access blocked or rate limited: HTTP {r.status_code}')
            r.raise_for_status();obj=r.json()
            if not isinstance(obj.get('results'),list) or not isinstance(obj.get('pager'),dict):raise ValueError('Unexpected JSON schema')
            return obj
        except (requests.RequestException,ValueError) as e:
            if attempt==attempts-1:raise
            time.sleep(2**attempt+random.uniform(0,1))

def write_outputs(folder,rows,status):
    folder.mkdir(parents=True,exist_ok=True)
    ordered=sorted(rows.values(),key=lambda x:(x['Publication period'],x['Drupal NID']),reverse=True)
    with (folder/'ADL_Insights_Database.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=HEAD);writer.writeheader();writer.writerows(ordered)
    wb=Workbook();ws=wb.active;ws.title='Publications';ws.append(HEAD)
    for row in ordered:ws.append([row.get(k,'') for k in HEAD])
    ws.freeze_panes='C2';ws.sheet_view.showGridLines=False;ws.auto_filter.ref=f'A1:O{max(1,ws.max_row)}'
    widths=[15,54,54,21,27,25,35,27,25,85,70,23,17,17,17]
    for i,w in enumerate(widths,1):ws.column_dimensions[__import__('openpyxl').utils.get_column_letter(i)].width=w
    for c in ws[1]:c.fill=PatternFill('solid',fgColor='193454');c.font=Font(color='FFFFFF',bold=True);c.alignment=Alignment(wrap_text=True)
    ws.row_dimensions[1].height=32
    for row in ws.iter_rows(min_row=2):
        for c in row:c.alignment=Alignment(vertical='top');c.font=Font(color='00805D',size=10)
        if row[10].value:row[10].hyperlink=row[10].value;row[10].font=Font(color='0563C1',underline='single')
        row[11].fill=PatternFill('solid',fgColor='DFF2E8' if row[11].value=='Direct ENUR' else 'FFF0D8' if row[11].value=='Cross-sector review' else 'F1F3F5')
    summary=wb.create_sheet('Coverage & QA');summary.sheet_view.showGridLines=False
    for k,v in status.items():summary.append([k,v])
    summary.column_dimensions['A'].width=36;summary.column_dimensions['B'].width=95
    for c in summary[1]:c.fill=PatternFill('solid',fgColor='193454');c.font=Font(color='FFFFFF',bold=True)
    wb.save(folder/'ADL_Insights_Database.xlsx')
    (folder/'coverage.json').write_text(json.dumps(status,indent=2,ensure_ascii=False),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--backfill',action='store_true');g.add_argument('--update',action='store_true');g.add_argument('--import-json',type=Path)
    ap.add_argument('--output-dir',type=Path,default=Path('data'));ap.add_argument('--max-pages',type=int,default=300)
    ap.add_argument('--delay',type=float,default=1.5);args=ap.parse_args()
    folder=args.output_dir;rows={};prior=folder/'ADL_Insights_Database.csv'
    if prior.exists():
        with prior.open(encoding='utf-8-sig',newline='') as f:rows={r['Drupal NID']:r for r in csv.DictReader(f)}
    seen=set();count=0;expected=None;pages=None;complete=False;errors=[]
    session=requests.Session();session.headers.update({'User-Agent':'ADL-Insights-Internal-Archive/1.0 (respectful catalogue polling)','Accept':'application/json'})
    try:
        for page in range(1,args.max_pages+1):
            if args.import_json:
                if page>1:break
                obj=json.loads(args.import_json.read_text(encoding='utf-8-sig'))
            else:obj=get_page(session,page)
            pager=obj['pager'];expected=pager.get('count',expected);pages=pager.get('pages',pages)
            results=obj['results'];count+=1
            for x in results:
                n=normalize(x,page,rows.get(str(x.get('nid',''))))
                if n:rows[n['Drupal NID']]=n;seen.add(n['Drupal NID'])
            print(f'Page {page}/{pages or "?"}: {len(results)} items, total unique {len(rows)}',flush=True)
            if args.import_json:break
            if page>=int(pages or 0) or not results:complete=True;break
            if args.update and page>=2:break # new items may span 2 pages; full backfill for deep reconciliation
            time.sleep(max(args.delay,0.5))
    except Exception as e:
        errors.append(str(e));logging.error('Collection interrupted: %s',e)
    status={'Run UTC':dt.datetime.now(dt.timezone.utc).isoformat(),'Mode':'import-json' if args.import_json else ('backfill' if args.backfill else 'update'),
            'Unique records in archive':len(rows),'Records seen this run':len(seen),'Pages processed':count,
            'API reported count':expected,'API reported pages':pages,'Full pagination completed this run':complete,
            'Coverage complete': bool(complete and expected is not None and len(seen)>=int(expected)),
            'Errors':'; '.join(errors) if errors else 'None',
            'Method':'Public metadata catalogue; no article full text; nid deduplication; ENUR relevance heuristic requires review',
            'Note':'Update checks first 2 pages only; schedule periodic backfill to reconcile older/edited entries.'}
    write_outputs(folder,rows,status)
    print(json.dumps(status,indent=2))
    if errors:raise SystemExit(1)
if __name__=='__main__':main()
