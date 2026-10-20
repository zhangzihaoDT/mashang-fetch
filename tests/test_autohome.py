"""Offline regression for rendered div comparisons and configuration icons."""
import subprocess
import unittest
from pathlib import Path


class AutohomeTests(unittest.TestCase):
    def test_comparison_exports(self):
        root = Path(__file__).resolve().parent.parent
        script = r"""
const assert = require('node:assert/strict');
const fs = require('fs');
const {isComparison, extractComparison} = require('./src/extractor/autohome');
const url = 'https://car.autohome.com.cn/duibi/chexing/#carids=74253%2C78966';
assert(isComparison(url));
assert(!isComparison('https://example.com/duibi/chexing/'));
const html = fs.readFileSync('tests/fixtures/autohome-comparison.html', 'utf8');
const doc = extractComparison(html, url);
assert.equal(doc.tables[0][0].length, 4);
assert.deepEqual(doc.tables[0].find(r => r[1] === 'CLTC纯电续航里程(km)').slice(2), ['650', '782']);
assert.deepEqual(doc.tables[0].find(r => r[1] === 'ABS防抱死').slice(2), ['[标配]', '[标配]']);
assert.match(doc.tables[0].find(r => r[1] === '前轮胎规格')[3], /\[选配\].*9800元/);
assert.match(require('./src/exporter/csv').render(doc), /650,782/);
assert.match(require('./src/exporter/markdown').render({...doc, source:url}), /\| 分类 \| 参数 \|/);
assert.throws(() => extractComparison('', url), /未加载完整/);
assert.throws(() => extractComparison(html, url.replace('78966', '99999')), /未加载完整/);
"""
        subprocess.run(['node', '-e', script], cwd=root, check=True, text=True)
