"""Offline replay on explicitly synthetic, hand-labelled candidates, with frozen V0 outputs.
Run: .venv/bin/python scripts/evaluate_search_quality.py
No API calls, no credentials, no scraped factual claims.
"""
import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.research import execute
from app.search_time import resolve


def evaluate():
    fixture=json.loads((ROOT/'tests/fixtures/search_quality_v1.json').read_text())
    baseline=json.loads((ROOT/'tests/fixtures/search_quality_v1_baseline.json').read_text())
    current={'cases':[],'time':[]}
    for c in fixture['cases']:
        def fake(query,effective_query):
            angle=next(e['angle'] for e in c['entries'] if e['angle'] in effective_query)
            rows=[r for r in c['rows'] if angle in r['returned_for']]
            # Ground truth must never enter the actual ranker/classifier.
            rows=[{k:v for k,v in r.items() if k not in ('relevant','gold_angles','returned_for')} for r in rows]
            return {'results':rows,'diagnostics':{'provider_count':len(rows)}}
        with patch('app.research.today',return_value=date(2026,10,20)),patch('app.research.search',side_effect=fake):
            r=execute(c['query'],c['entries'])
        current['cases'].append({'id':c['id'],'results':r['results'],'requests':r['diagnostics']['request_count']})
    for q,start,end in fixture['time_cases']:
        try:
            i=resolve(q,date(2026,10,20)); current['time'].append({'query':q,'start':i['start'],'end':i['end']})
        except ValueError:
            current['time'].append({'query':q,'error':True})
    def metrics(run):
        cases=[]
        correct_labels=total_labels=0
        for c,output in zip(fixture['cases'],run['cases']):
            truth={r['url']:r for r in c['rows']}
            rows=output['results'][:10]
            relevant_count=sum(truth[r['url']]['relevant'] for r in rows)
            good=total=0
            for r in output['results']:
                for angle in r['angles']:
                    total+=1
                    good+=angle in truth[r['url']]['gold_angles']
            total_labels+=total; correct_labels+=good
            cases.append({'id':c['id'],'precision_at_10':relevant_count/10,'returned':len(output['results']),
                          'label_correct':good,'labels':total,'requests':output['requests']})
        temporal=sum(not actual.get('error') and (actual['start'],actual['end'])==(start,end)
                     for (q,start,end),actual in zip(fixture['time_cases'],run['time']))
        # Recall prevents an abstain-everywhere classifier from looking successful.
        expected=sum(len(r['gold_angles']) for c in fixture['cases'] for r in c['rows'])
        return {'precision_at_10':sum(c['precision_at_10'] for c in cases)/len(cases),
                'time_correct':temporal,'time_total':len(fixture['time_cases']),
                'time_accuracy':temporal/len(fixture['time_cases']),
                'angle_precision':correct_labels/total_labels if total_labels else None,
                'angle_correct':correct_labels,'angle_total':total_labels,
                'angle_recall':correct_labels/expected,'cases':cases}
    return {'method':'synthetic fixed candidate replay; not a live retrieval benchmark; P@10 denominator is always 10; angle precision over all returned labels; expected labels=24; date reference=2026-10-20',
            'before':metrics(baseline),'after':metrics(current),'time_before':baseline['time'],'time_after':current['time']}


if __name__=='__main__':
    result=evaluate()
    (ROOT/'docs/search-quality-v1-evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['method','before','after']},ensure_ascii=False,indent=2))
