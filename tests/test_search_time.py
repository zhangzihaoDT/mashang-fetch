import unittest
from datetime import date
from unittest.mock import patch
from app.search_time import resolve
from app.research import validate, execute

class SearchTimeTests(unittest.TestCase):
    def test_yesterday_calendar_day_and_normalized_query(self):
        intent = resolve('智己汽车 昨日发布', date(2026,10,20))
        self.assertEqual(intent['start'], '2026-10-19')
        self.assertEqual(intent['end'], '2026-10-19')
        self.assertEqual(intent['after'], '2026-10-18')
        self.assertEqual(intent['before'], '2026-10-20')
        self.assertEqual(intent['normalized_query'], '智己汽车 2026-10-19发布')
        with patch('app.research.today', return_value=date(2026,10,20)):
            jobs = validate('智己汽车 昨日发布', [{'angle':'发布内容','query':'智己汽车 新车发布'}])
        self.assertIn('2026-10-19', jobs[0]['query'])
        self.assertIn('after:2026-10-18 before:2026-10-20', jobs[0]['effective_query'])

    def test_local_midnight_and_unknown_dates(self):
        rows = [{'id':str(i),'url':f'https://example.com/{i}','date':d} for i,d in enumerate([
            '2026-10-18T16:00:00Z', '2026-10-19T15:59:59Z',
            '2026-10-19T16:00:00Z', '2026-10-18T15:59:59Z', None])]
        with patch('app.research.today',return_value=date(2026,10,20)), patch('app.research.search',return_value={'results':rows,'diagnostics':{'provider_count':5}}):
            result = execute('智己汽车 昨日发布',[{'angle':'新闻','query':'智己汽车'}])
        self.assertEqual(len(result['results']),2)
        self.assertEqual(result['diagnostics']['time_intent']['start'],'2026-10-19')

    def test_other_relative_dates_and_conflicts(self):
        reference=date(2026,10,20)
        self.assertEqual(resolve('今天发布',reference)['start'],'2026-10-20')
        self.assertEqual(resolve('最近7天',reference)['start'],'2026-10-14')
        self.assertEqual(resolve('上周消息',reference)['start'],'2026-10-12')
        self.assertEqual(resolve('上月消息',reference)['end'],'2026-09-30')
        self.assertEqual(resolve('2026年10月19日发布',reference)['start'],'2026-10-19')
        with self.assertRaises(ValueError): resolve('昨日',reference,after='2026-10-20')
