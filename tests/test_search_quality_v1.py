import io
import json
import threading
import time
import unittest
import urllib.error
from datetime import date
from unittest.mock import patch
from app.search_time import resolve
from app.research import execute, prepare, generate
from app.search_quality import angle_evidence, duplicate_content, quality, relevant
from app.search_http import request_json, budget

REF = date(2026,10,20)


def entry(angle='产品价格', query='智己汽车 售价', **extra):
    return {'angle':angle,'query':query,'domains':[],**extra}


def payload(rows):
    return {'results':rows,'diagnostics':{'provider_count':len(rows)}}


class TimeV1Tests(unittest.TestCase):
    def test_model_year_is_topic_attribute(self):
        for q in ['2027款智己LS6配置','2026款车型','2027款智己 昨日发布']:
            i=resolve(q,REF)
            self.assertEqual(i['start'], '2026-10-19' if '昨日' in q else None)
        self.assertIn('2027款智己 2026-10-19发布',resolve('2027款智己 昨日发布',REF)['normalized_query'])

    def test_month_and_month_range(self):
        for q,start,end in [('2026年10月 智己','2026-10-01','2026-10-31'),('2026年1月至3月 Tesla','2026-01-01','2026-03-31'),('2026年9月至10月','2026-09-01','2026-10-31'),('2025年12月至2026年2月','2025-12-01','2026-02-28')]:
            with self.subTest(q=q):
                i=resolve(q,REF); self.assertEqual((i['start'],i['end']),(start,end))

    def test_cross_month_and_multiple_dates(self):
        for q in ['2026年9月30日至10月2日 新闻','2026-09-30至2026-10-02 新闻']:
            i=resolve(q,REF); self.assertEqual((i['start'],i['end']),('2026-09-30','2026-10-02'))
        i=resolve('昨天和今天的发布',REF)
        self.assertEqual((i['start'],i['end']),('2026-10-19','2026-10-20'))
        for q in ['2026年9月30日和10月2日','2026年13月新闻','2027年发布计划']:
            i=resolve(q,REF); self.assertTrue(i['ambiguous']); self.assertEqual(i['after'],'')

    def test_ambiguous_keeps_explicit_filters_and_candidates(self):
        i=resolve('2026年13月消息',REF,after='2026-09-01')
        self.assertEqual(i['after'],'2026-09-01'); self.assertTrue(i['warnings'])
        rows=[{'url':'https://example.com/a','title':'智己汽车发布消息','date':None}]
        with patch('app.research.today',return_value=REF),patch('app.research.search',return_value=payload(rows)):
            r=execute('智己汽车 2026年13月',[entry()])
        self.assertEqual(len(r['results']),1)
        self.assertEqual(resolve('2027款车型',REF)['target'],'unspecified')
        self.assertEqual(resolve('昨日上市',REF)['target'],'event')
        self.assertEqual(resolve('昨日发表的报道',REF)['target'],'publication')


class QualityV1Tests(unittest.TestCase):
    def test_hit_angles_are_not_content_labels(self):
        row={'url':'https://example.com/a','title':'智己汽车新车售价','snippet':'售价23万元。'}
        entries=[entry(),entry('技术细节','智己汽车 技术')]
        with patch('app.research.search',return_value=payload([row])):
            r=execute('智己汽车',entries)
        item=r['results'][0]
        self.assertEqual(item['matched_angles'],['产品价格','技术细节'])
        self.assertEqual(item['angles'],['产品价格'])
        self.assertEqual(item['angle_evidence']['产品价格'],['售价'])
        self.assertEqual(angle_evidence({'title':'电池单元配置'}, entry('产品价格')),[])
        self.assertEqual(angle_evidence({'title':'配置参数介绍'}, entry('官方配置')),[])

    def test_quality_tiers_not_score_sums_and_missing_is_retained(self):
        rows=[{'url':'https://example.com/noise','title':'智己汽车广告','provider_score':.7,'provider_authority':0},
              {'url':'https://example.com/missing','title':'智己汽车介绍'},
              {'url':'https://example.com/strong','title':'智己汽车售价','provider_score':2,'provider_authority':3}]
        with patch('app.research.search',return_value=payload(rows)):
            r=execute('智己汽车',[entry()])
        self.assertEqual([x['url'].rsplit('/',1)[-1] for x in r['results']],['strong','missing'])
        self.assertEqual(r['diagnostics']['filter_reasons'],{'low_relevance_and_authority':1})
        self.assertEqual(quality({'provider_score':float('nan'),'provider_authority':-1}),(1,1))
        self.assertFalse(relevant('2027款智己LS6配置',{'title':'智己LS8配置'}))
        self.assertTrue(relevant('2027款智己LS6配置',{'title':'智己LS6技术配置'}))
        self.assertFalse(relevant('Tesla Robotaxi',{'title':'Waymo Robotaxi'}))
        self.assertTrue(relevant('Research Tesla Robotaxi commercialization progress',{'title':'Tesla Robotaxi commercial service'}))

    def test_conservative_duplicate_content_preserves_source_links(self):
        row={'url':'https://a.example/a','title':'智己汽车发布全新车型详细参数公告','snippet':'智己汽车新车技术配置与价格详细说明。'*10}
        second={**row,'url':'https://b.example/a'}
        self.assertTrue(duplicate_content(row,second))
        self.assertFalse(duplicate_content({**row,'snippet':'短摘要'},{**second,'snippet':'短摘要'}))
        with patch('app.research.search',return_value=payload([row,second])):
            r=execute('智己汽车',[entry()])
        self.assertEqual(len(r['results']),1)
        self.assertEqual(r['diagnostics']['content_duplicates_removed'],1)
        self.assertEqual(r['results'][0]['duplicate_sources'][0]['url'],second['url'])

    def test_partial_invalid_plan_and_duplicates(self):
        jobs,issues=prepare('智己汽车',[entry(),entry(query=None),entry(),entry(query='智己汽车 技术',angle='技术')])
        self.assertEqual(len(jobs),2)
        self.assertEqual([x['reason'] for x in issues],['invalid_plan','duplicate_plan'])
        jobs,issues=prepare('Tesla',[entry(query='Tesla Robotaxi price',angle='价格'),entry(query='Robotaxi Tesla price',angle='价格')])
        self.assertEqual(len(jobs),1)
        self.assertEqual(issues[0]['reason'],'duplicate_plan')
        with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'fake'}),patch('app.research.request_json',return_value={'choices':[{'message':{'content':json.dumps({'entries':[entry(),entry(query=None)]})}}]}):
            result=generate('智己汽车')
        self.assertEqual(len(result['entries']),1)
        self.assertIsNone(result['warning'])
        self.assertEqual(result['plan_issues'][0]['reason'],'invalid_plan')

    def test_filter_reason_accounting(self):
        rows=[{'url':'https://other.example/a','date':'2026-10-19'}, {'url':'https://ok.example/a','date':None}, {'url':'https://ok.example/b','date':'2026-10-01'}]
        with patch('app.research.today',return_value=REF),patch('app.research.search',return_value=payload(rows)):
            r=execute('昨日',[entry(domains=['ok.example'])])
        self.assertEqual(r['diagnostics']['filter_reasons'],{'source_mismatch':1,'unknown_publication_date':1,'publication_out_of_range':1})


class ReliabilityV1Tests(unittest.TestCase):
    def test_retry_only_transient_errors(self):
        for code,attempts in [(429,3),(500,3),(408,3),(401,1),(402,1),(400,1)]:
            error=urllib.error.HTTPError('https://example.com',code,'error',{},None)
            with self.subTest(code=code),patch('urllib.request.urlopen',side_effect=error) as call,patch('app.search_http.time.sleep'):
                with self.assertRaises(urllib.error.HTTPError): request_json(object())
                self.assertEqual(call.call_count,attempts)

    def test_retry_recovers_and_budget_stops_requests(self):
        data=io.BytesIO(b'{"results":[]}')
        with patch('urllib.request.urlopen',side_effect=[TimeoutError(),data]) as call,patch('app.search_http.time.sleep'):
            self.assertEqual(request_json(object()),{'results':[]})
            self.assertEqual(call.call_count,2)
        with budget(0),patch('urllib.request.urlopen') as call:
            with self.assertRaisesRegex(ValueError,'总耗时'): request_json(object())
            call.assert_not_called()

    def test_whole_execution_deadline_does_not_wait_for_worker(self):
        release=threading.Event()
        def blocked(*args,**kwargs):
            release.wait(.5)
            return payload([])
        started=time.monotonic()
        try:
            with budget(.02),patch('app.research.search',side_effect=blocked):
                with self.assertRaisesRegex(ValueError,'总耗时'): execute('智己汽车',[entry()])
            self.assertLess(time.monotonic()-started,.2)
        finally:
            release.set()


class EvaluationV1Tests(unittest.TestCase):
    def test_fixed_replay_metrics_and_query_budget(self):
        from scripts.evaluate_search_quality import evaluate
        report=evaluate()
        self.assertGreater(report['after']['precision_at_10'],report['before']['precision_at_10'])
        self.assertEqual(report['after']['time_correct'],8)
        self.assertGreater(report['after']['angle_precision'],report['before']['angle_precision'])
        self.assertEqual(report['after']['angle_recall'],1)
        self.assertEqual([c['requests'] for c in report['before']['cases']],[c['requests'] for c in report['after']['cases']])

    def test_all_failed_api_retains_diagnostics(self):
        from fastapi.testclient import TestClient
        from server import app
        error=ValueError('搜索凭据无效')
        error.reason='authentication'
        with patch('app.research.search',side_effect=error):
            response=TestClient(app).post('/api/search',json={'query':'智己汽车','entries':[entry()]})
        self.assertEqual(response.status_code,400)
        self.assertEqual(response.json()['diagnostics']['failure_reasons'],{'authentication':1})
        self.assertEqual(response.json()['detail'],'搜索凭据无效')
