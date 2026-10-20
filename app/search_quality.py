"""Conservative content evidence and ordinal quality tiers; no raw-score addition."""
import math
import re
from difflib import SequenceMatcher

# A label is granted only when its subject has evidence in the title/snippet.
FACETS = [
    (r'发布|亮相|上市|公告|更新|进展', r'发布|亮相|上市|公告|上线|更新|launch|announce|release|introduc'),
    (r'价格|售价|费用|计费|权益', r'价格|售价|\d+(?:\.\d+)?\s*(?:万|亿)?元|费用|计费|优惠|权益|price|pricing|cost|paid'),
    (r'配置|车型', r'配置|车型|版本|座|configuration|variant|model'),
    (r'技术|细节|能力|性能|架构|续航|动力|电池|智驾|智能驾驶|座舱', r'技术|底盘|电池|续航|动力|功率|智驾|智能驾驶|座舱|线控|推理|训练|架构|性能|能力|传感器|sensors?|architect|technolog|autonomous|system'),
    (r'监管|许可|合规', r'监管|许可|批准|审批|牌照|permit|regulat|licen[sc]e|approv|authority'),
    (r'运营|商业化|交付', r'运营|商业化|交付|收费|车队|乘客|operat|commercial|service|fleet|passenger|paid rides'),
    (r'市场|反响|反馈|评价|评测|实测', r'市场|反响|反馈|评价|评测|实测|体验|用户|销量|订单|market|reaction|feedback|review|sales|orders?'),
    (r'媒体|报道', r'据.{0,12}报道|记者|采访|报道|report|journalist|interview'),
    (r'官方|一手', r'官方|官网|本公司|我们宣布|official|we announce'),
    (r'竞争|对比|比较', r'对比|比较|竞争|相比|compar|compet|versus| vs\.? '),
]
STOP = re.compile(r'研究|关于|昨日|今日|昨天|今天|最近\d*天|商业化进展|进展|发布|搜索|资料|新闻|消息|年|月|日')


def words(text):
    text = re.sub(r'20\d{2}(?:款)?(?:[-年/]\d{1,2})?(?:[-月/]\d{1,2}日?)?', '', text.lower())
    text = STOP.sub(' ', text)
    return set(re.findall(r'[a-z][a-z0-9]{2,}|[\u4e00-\u9fff]{2,}', text))


def relevant(query, row):
    text = (str(row.get('title') or '')+' '+str(row.get('snippet') or '')).lower()
    if not text.strip():
        return True  # Missing metadata is not proof of irrelevance.
    anchors = words(query)
    # Require original named English entities; do not let a query expansion change the subject.
    all_english = re.findall(r'[A-Za-z][A-Za-z0-9]{2,}', query)
    english = all_english if len(all_english) <= 3 else [w for w in all_english if w[0].isupper()]
    english = [w.lower() for w in english if w.lower() not in {'research','about','latest','news','the','and','for'}]
    if english and not all(w in text for w in english):
        return False
    chinese = [w for w in anchors if re.fullmatch(r'[\u4e00-\u9fff]+', w)]
    if chinese and not english and not any(w in text for w in chinese):
        # Long natural-language questions are not safe to reject by literal substring.
        if all(len(w) <= 6 for w in chinese):
            return False
    return True


def number(value, low, high):
    if isinstance(value, (int,float)) and not isinstance(value,bool) and math.isfinite(value) and low <= value <= high:
        return value
    return None


def quality(row):
    score = number(row.get('provider_score'),0,3)
    authority = number(row.get('provider_authority'),0,4)
    # Fixed documented score bands, not a weighted sum of incompatible scales.
    tier = 0 if score is not None and score >= 1.5 else 2 if score is not None and score < 1 else 1
    source = 0 if authority is not None and authority >= 3 else 2 if authority is not None and authority <= 1 else 1
    return tier,source


def low_quality(row):
    return quality(row) == (2,2)


def angle_evidence(row, job):
    text = str(row.get('title') or '')+' '+str(row.get('snippet') or '')
    # Source qualifiers are required as well as a topical facet. A configuration table
    # alone cannot justify an 'official configuration' label. Identity remains unverified.
    if re.search(r'官方|一手', job['angle']) and not re.search(r'官方|官网|本公司|我们宣布|official|we announce', text, re.I):
        return []
    matches = []
    rules = [evidence for label,evidence in FACETS if re.search(label,job['angle'])]
    if rules:
        for rule in rules:
            found = re.search(rule,text,re.I)
            if found:
                matches.append(found[0])
        # Composite labels can have evidence for either explicit facet (产品与价格 etc.).
    else:
        for word in words(job['angle']):
            found = re.search(re.escape(word),text,re.I)
            if found:
                matches.append(found[0])
    return list(dict.fromkeys(matches))


def similar_query(a,b):
    if sorted(a['domains']) != sorted(b['domains']):
        return False
    # Exact duplicate keywords share one request; fuzzy matching stays within a facet.
    x = re.sub(r'\s+','',a['query'].lower())
    y = re.sub(r'\s+','',b['query'].lower())
    if x == y:
        return True
    if a['angle'] != b['angle']:
        return False
    ta,tb = words(a['query']),words(b['query'])
    return (bool(ta) and ta == tb) or SequenceMatcher(None,x,y).ratio() >= .94


def duplicate_content(a,b):
    clean = lambda s: re.sub(r'\W+','',str(s or '').lower())
    at,bt = clean(a.get('title')),clean(b.get('title'))
    ax,bx = clean(a.get('snippet')),clean(b.get('snippet'))
    return len(at) >= 12 and at == bt and min(len(ax),len(bx)) >= 80 and SequenceMatcher(None,ax,bx).ratio() >= .97
