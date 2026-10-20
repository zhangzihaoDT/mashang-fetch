import unittest
from app.search_pipeline import canonical_url

class URLFusionTests(unittest.TestCase):
    def test_normalization_preserves_semantic_query(self):
        self.assertEqual(canonical_url('https://EXAMPLE.com:443/a?id=2&utm_source=x#frag'), 'https://example.com/a?id=2')
        self.assertNotEqual(canonical_url('https://example.com/a?id=2'), canonical_url('https://example.com/a?id=3'))
