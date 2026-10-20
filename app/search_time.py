"""Conservative calendar intent parsing. Bounds describe publication proxies, not verified events."""
import calendar
import re
from datetime import date, timedelta


def resolve(query, reference, after='', before=''):
    for value in (after, before):
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                raise ValueError('日期格式须为 YYYY-MM-DD') from None
    explicit_after, explicit_before = after, before
    if after and before and date.fromisoformat(after) + timedelta(days=1) >= date.fromisoformat(before):
        raise ValueError('时间条件无交集，请调整日期')
    start = end = None
    normalized = query
    warnings = []
    # Model years and product/version numbers are topic attributes.
    text = re.sub(r'20\d{2}\s*款', lambda m: ' '*len(m[0]), query)
    target = 'publication' if re.search(r'网页|文章|报道|发布时间', text) else 'event' if re.search(r'发布|上市|发生|举办|上线', text) else 'unspecified'
    ambiguous = False
    try:
        # A range may omit the second year or month: 2026年9月30日至10月2日.
        span = re.search(r'(20\d{2})年(\d{1,2})月(?:(\d{1,2})日)?\s*(?:至|到|—|~|～|-)\s*(?:(20\d{2})年)?(?:(\d{1,2})月)?(?:(\d{1,2})日)?', text)
        if span and (span[5] or span[6]):
            y, m = int(span[1]), int(span[2])
            y2, m2 = int(span[4] or y), int(span[5] or m)
            start = date(y, m, int(span[3] or 1))
            end = date(y2, m2, int(span[6] or calendar.monthrange(y2, m2)[1]))
            if end < start:
                start = end = None
                ambiguous = True
        else:
            full = list(re.finditer(r'(20\d{2})[年/-](\d{1,2})[月/-](\d{1,2})日?', text))
            short = [m for m in re.finditer(r'(\d{1,2})月(\d{1,2})日', text) if not any(f.start() <= m.start() < f.end() for f in full)]
            relative = list(re.finditer(r'大前天|前天|昨日|昨天|今日|今天', text))
            days = [date(*map(int, m.groups())) for m in full]
            inherited_year = int(full[0][1]) if full else reference.year
            offsets = {'大前天':3, '前天':2, '昨日':1, '昨天':1, '今日':0, '今天':0}
            days.extend(date(inherited_year, int(m[1]), int(m[2])) for m in short)
            days.extend(reference - timedelta(days=offsets[m[0]]) for m in relative)
            if days:
                # Disjoint dates cannot be represented as one interval without admitting gaps.
                ordered = sorted(set(days))
                if (ordered[-1] - ordered[0]).days + 1 == len(ordered) or re.search(r'至|到|—|~|～', text):
                    start, end = ordered[0], ordered[-1]
                else:
                    ambiguous = True
                for m in reversed(relative):
                    normalized = normalized[:m.start()] + (reference - timedelta(days=offsets[m[0]])).isoformat() + normalized[m.end():]
            else:
                recent = re.search(r'(?:最近|近|过去)\s*(\d{1,3})\s*(?:天|日)', text)
                if recent and 1 <= int(recent[1]) <= 366:
                    start, end = reference - timedelta(days=int(recent[1])-1), reference
                elif '上周' in text:
                    end = reference - timedelta(days=reference.weekday()+1)
                    start = end - timedelta(days=6)
                elif '本周' in text or '这周' in text:
                    start, end = reference-timedelta(days=reference.weekday()), reference
                elif '上月' in text:
                    end = reference.replace(day=1)-timedelta(days=1)
                    start = end.replace(day=1)
                elif '本月' in text or '这个月' in text:
                    start, end = reference.replace(day=1), reference
                else:
                    months = list(re.finditer(r'(20\d{2})年(\d{1,2})月', text))
                    if len(months) == 1:
                        y,m = map(int, months[0].groups())
                        start,end = date(y,m,1),date(y,m,calendar.monthrange(y,m)[1])
                    elif len(months) > 1:
                        ambiguous = True
                    else:
                        years = set(re.findall(r'(?<!\d)(20\d{2})(?!\d)',text))
                        if len(years) == 1:
                            y = int(next(iter(years)))
                            start,end = date(y,1,1), min(date(y,12,31),reference)
                            if start > end:  # Future event intent must not exclude current reporting.
                                start = end = None
                                ambiguous = True
                        elif len(years) > 1:
                            ambiguous = True
    except ValueError:
        start = end = None
        ambiguous = True
    if start:
        inferred_after = (start-timedelta(days=1)).isoformat()
        inferred_before = (end+timedelta(days=1)).isoformat()
        after = max(after,inferred_after) if after else inferred_after
        before = min(before,inferred_before) if before else inferred_before
        # Keep an explicitly contradictory, unambiguous constraint visible as an error.
        if after and before and date.fromisoformat(after)+timedelta(days=1) >= date.fromisoformat(before):
            raise ValueError('时间条件无交集，请调整日期或问题中的时间')
    if ambiguous:
        after,before = explicit_after,explicit_before
        warnings.append('问题中的时间存在歧义，已保留关键词，不据此排除资料。')
    actual_start = date.fromisoformat(after)+timedelta(days=1) if after else None
    actual_end = date.fromisoformat(before)-timedelta(days=1) if before else None
    label = f'{actual_start.isoformat() if actual_start else "不限"} 至 {actual_end.isoformat() if actual_end else "不限"}' if after or before else '不限时间'
    return {'after':after,'before':before,'start':actual_start.isoformat() if actual_start else None,
            'end':actual_end.isoformat() if actual_end else None,'label':label,'timezone':'Asia/Shanghai',
            'reference_date':reference.isoformat(),'normalized_query':normalized,'target':target,
            'ambiguous':ambiguous,'warnings':warnings,
            'basis':'网页发布时间；事件时间仅作检索线索，需核对原文'}
