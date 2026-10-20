import threading
import time
import unittest
from datetime import date
from unittest.mock import patch
from app.research import validate, execute, bounds


def entry(angle='官方', query='Tesla Robotaxi', **extra):
    return {'angle': angle, 'query': query, 'purpose': '查找证据', 'domains': [], **extra}


def response(url, **extra):
    return {'results': [{'url': url, 'id': url, 'date': '2026-06-01T00:00:00Z', **extra}], 'diagnostics': {'provider_count': 1}}


class ResearchTests(unittest.TestCase):
    def test_year_defaults_and_constraints(self):
        with patch('app.research.today', return_value=date(2026, 10, 20)):
            self.assertEqual(bounds('研究2026年Tesla', '', ''), ('2025-12-31', '2026-10-21'))
            jobs = validate('2026 Robotaxi', [entry(domains=['tesla.com'])], domains=['gov.cn'], after='2026-06-01')
        self.assertEqual(jobs[0]['domains'], ['gov.cn'])
        self.assertIn('after:2026-06-01', jobs[0]['effective_query'])
        self.assertNotIn('site:tesla.com', jobs[0]['effective_query'])

    def test_invalid_plan_rejected_before_requests(self):
        for rows in [[], [entry()] * 7, [entry(query='Tesla site:evil.com')], [entry(domains=12)], [entry(query=None)]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                validate('Tesla', rows)

    def test_concurrency_is_bounded_and_metadata_fuses(self):
        lock = threading.Lock()
        active = peak = 0
        def fake(*args, **kwargs):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(.02)
            with lock:
                active -= 1
            return response('https://example.com/common?utm_source=x')
        with patch('app.research.search', side_effect=fake):
            result = execute('Tesla', [entry(angle=str(i), query=f'Tesla Robotaxi perspective {i}') for i in range(6)])
        self.assertGreater(peak, 1)
        self.assertLessEqual(peak, 3)
        self.assertEqual(len(result['results']), 1)
        self.assertEqual(len(result['results'][0]['matched_angles']), 6)
        self.assertEqual(result['results'][0]['angles'], [])
        self.assertEqual(result['diagnostics']['duplicates_removed'], 5)

    def test_failures_empty_angles_and_date_filter(self):
        def fake(query, effective_query):
            if 'bad' in effective_query:
                raise ValueError('timeout')
            return response('https://example.com/a', date=None)
        with patch('app.research.search', side_effect=fake):
            result = execute('Tesla', [entry('失败', query='bad'), entry('未知日期')], after='2026-01-01')
        self.assertEqual(len(result['results']), 0)
        self.assertEqual([r['status'] for r in result['diagnostics']['requests']], ['failed', 'empty'])

    def test_angle_representation_and_domain_filter(self):
        def fake(query, effective_query):
            return response('https://tesla.com/a' if 'official' in effective_query else 'https://example.com/b', title='Tesla 官方公告' if 'official' in effective_query else 'Tesla 媒体报道')
        with patch('app.research.search', side_effect=fake):
            result = execute('Tesla', [entry('官方', query='official', domains=['tesla.com']), entry('媒体', query='media')])
        self.assertEqual([r['angles'][0] for r in result['results']], ['官方', '媒体'])
        self.assertTrue(all(r['source_kind'] == '网页 · 来源身份待核验' for r in result['results']))

    def test_search_api_always_uses_planning(self):
        from fastapi.testclient import TestClient
        from server import app
        jobs = [entry()]
        with patch('app.research.generate', return_value={'entries': jobs, 'warning': None}) as planner, patch('app.research.execute', return_value={'results': [], 'diagnostics': {'warnings': []}}) as executor:
            client = TestClient(app)
            response = client.post('/api/search', json={'query': 'Tesla'})
            self.assertEqual(response.status_code, 200)
            planner.assert_called_once()
            self.assertEqual(executor.call_args.args[1], jobs)
            planner.reset_mock()
            response = client.post('/api/search', json={'query': 'Tesla', 'entries': jobs})
            self.assertEqual(response.status_code, 200)
            planner.assert_not_called()
