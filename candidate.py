"""Fixed full-history user topic dossier on exact official 0.32.

Only literal user spans are admitted. No generation, learned reranking, graph,
procedure extraction or query expansion. Native Search runs before augmentation.
"""
from collections import Counter
from datetime import datetime, timezone
import math
import re
import threading

import numpy as np

SETTINGS = dict(max_sources=4, source_chars=1400, supplement_chars=3600,
                native_reference_chars=12000, minimum_topic_coverage=.18,
                cohort_score_ratio=.55, lexical_weight=.70)
PERSONAL = re.compile(r'\b(?:I|me|my|mine|we|our|ours|you|your|user)\b|我|我们|你|用户', re.I)
RULE_QUERY = re.compile(r'\b(?:procedures?|instructions?|rules?|requirements?|steps?|format|polic(?:y|ies))\b|步骤|流程|规则|指令|格式', re.I)
BOUNDARY = re.compile(r'(?<=[.!?。！？])\s+|\n+')
GENERIC = set('user users personal persona preferences preference recommend recommendation recommendations suggest suggestions advice suitable suited best help support based given shared previously previous conversation conversations history historical current latest old new changed change changes updated update reasons reason explain remember recall statement statements tell asked asking want wants need needs would could should me my your you mine us our please considering considering information know knows think thinks consider'.split())


def terms(text, tokenize):
    return tokenize(re.sub(r'^Current date:[^\n]*\n', '', text)) - GENERIC


def sentence_ranges(text):
    start = 0
    result = []
    for match in BOUNDARY.finditer(text):
        if text[start:match.start()].strip():
            result.append((start, match.start()))
        start = match.end()
    if text[start:].strip():
        result.append((start, len(text)))
    return result


def literal_context(row, query_terms, tokenize):
    """One complete utterance or matching sentence with explanatory neighbors."""
    text = row['content']
    ranges = sentence_ranges(text)
    declarative = [(a,b) for a,b in ranges if not text[a:b].rstrip().endswith(('?', '？'))]
    if not declarative:
        return None
    if len(text) <= SETTINGS['source_chars']:
        return dict(row)
    matches = [(len(tokenize(text[a:b]) & query_terms), p, a, b)
               for p,(a,b) in enumerate(ranges)
               if b-a <= SETTINGS['source_chars'] and (a,b) in declarative]
    if not matches:
        return None
    overlap, p, left, right = max(matches, key=lambda x:(x[0], -x[1]))
    if not overlap:
        return None
    # A condition or explanation remains a complete source sentence. Never clip
    # a sentence to manufacture a shorter claim or normalize its negation.
    if p > 0 and right-ranges[p-1][0] <= SETTINGS['source_chars']:
        left = ranges[p-1][0]
    if p+1 < len(ranges) and ranges[p+1][1]-left <= SETTINGS['source_chars']:
        right = ranges[p+1][1]
    while left < right and text[left].isspace():
        left += 1
    while right > left and text[right-1].isspace():
        right -= 1
    return {**row, 'start':row['start']+left, 'end':row['start']+right,
            'content':text[left:right]}


def full_user_sources(index, merge):
    with index.view_lock:
        if hasattr(index, '_history04_sources'):
            return index._history04_sources
        users = [i for i,r in enumerate(index.rows) if r['role'].casefold() == 'user']
        chunks = {}
        for i in users:
            chunks.setdefault(index.rows[i]['source_id'], []).append(i)
        originals = [r for _,r in merge(index, users)]
        index._history04_sources = (originals, chunks)
        return originals, chunks


def dossier(index, originals, chunks, query, query_vector, tokenize, merge, render, native_prefix):
    query_terms = terms(query, tokenize)
    if not query_terms:
        return [], {'reason':'no_specific_query_topic'}
    source_terms = [tokenize(r['content']) for r in originals]
    df = Counter(t for values in source_terms for t in values & query_terms)
    weights = {t:math.log(1+(len(originals)+1)/(1+df[t])) for t in query_terms}
    denom = sum(weights.values()) or 1
    ranked = []
    for row, vocab in zip(originals, source_terms):
        overlap = query_terms & vocab
        coverage = sum(weights[t] for t in overlap)/denom
        if coverage < SETTINGS['minimum_topic_coverage'] or not overlap:
            continue
        span = literal_context(row, query_terms, tokenize)
        if span is None:
            continue
        dense = float((index.matrix[chunks[row['source_id']]] @ query_vector).max())
        score = SETTINGS['lexical_weight']*coverage + (1-SETTINGS['lexical_weight'])*max(0,dense)
        ranked.append(dict(row=span, score=score, overlap=overlap))
    ranked.sort(key=lambda x:(-x['score'], x['row']['id']))
    # A seed must add literal information absent from the native prefix. This
    # eligibility does not receive evidence labels, options or reference answers.
    novel = [x for x in ranked if x['row']['content'] not in native_prefix]
    if not novel:
        return [], {'reason':'no_novel_user_statement', 'matched_sources':len(ranked)}
    seed = novel[0]
    cohort = [x for x in ranked if x['score'] >= seed['score']*SETTINGS['cohort_score_ratio']
              and x['overlap'] & seed['overlap']]
    # Keep the strongest novel statement, strongest other statement, and dated
    # endpoints of the same topic. Undated sources never get invented dates or
    # inferred old/new labels. All versions remain literal statements.
    choices = [seed]
    dated = [x for x in cohort if x['row']['timestamp'] is not None]
    if dated:
        choices += [min(dated,key=lambda x:(x['row']['timestamp'],x['row']['id'])),
                    max(dated,key=lambda x:(x['row']['timestamp'],x['row']['id']))]
    choices += cohort
    selected = []; seen = set(); used = 0
    for choice in choices:
        row = choice['row']; sid = row['source_id']; cost = len(render(row))
        if sid in seen or used+cost > SETTINGS['supplement_chars']:
            continue
        selected.append(row); seen.add(sid); used += cost
        if len(selected) >= SETTINGS['max_sources']:
            break
    # Date order is asserted only when every source has an explicit timestamp.
    if selected and all(r['timestamp'] is not None for r in selected):
        selected.sort(key=lambda r:(r['timestamp'],r['request_id'],r['position'],r['start']))
    return selected, dict(reason='full_history_topic_dossier', user_sources=len(originals),
                          matched_sources=len(ranked), topic_cohort=len(cohort),
                          selected_sources=[r['source_id'] for r in selected],
                          seed_source=seed['row']['source_id'], supplement_chars=used,
                          all_dated=bool(selected) and all(r['timestamp'] is not None for r in selected))


def store_class(base, merge, standing_rule):
    class UserHistoryStore(base.MemoryStore):
        def __init__(self,*args,**kwargs):
            self.local = threading.local()
            super().__init__(*args,**kwargs)

        def ranked(self,*args,**kwargs):
            result = super().ranked(*args,**kwargs)
            if kwargs.get('return_document_prior'):
                self.local.order, self.local.document = result
            return result

        def search(self,*,user_id,query,top_k=100,options=None,mode='hybrid_window'):
            self.local.trace = dict(applied=False,reason='native_mode')
            self.local.document = False
            native = super().search(user_id=user_id,query=query,top_k=top_k,options=options,mode=mode)
            for condition,reason in ((mode!='query_document_evidence','native_mode'),
                                     (not native,'empty_native'),(self.local.document,'native_document'),
                                     (not PERSONAL.search(query),'nonpersonal_query'),
                                     (bool(RULE_QUERY.search(query)),'rule_query'),(top_k<8,'small_top_k')):
                if condition:
                    self.local.trace = dict(applied=False,reason=reason)
                    return native
            index = self.index(user_id)
            originals,chunks = full_user_sources(index,merge)
            prefix = []; used = 0
            for hit in native:
                prefix.append(hit['content']); used += len(hit['content'])
                if used >= SETTINGS['native_reference_chars']:
                    break
            with self.encoder_lock:
                q = np.asarray(self.encoder.encode([query],query=True),np.float32)[0]
            q /= np.linalg.norm(q)
            spans,trace = dossier(index,originals,chunks,query,q,base.content_tokens,merge,self.render,'\n\n'.join(prefix))
            self.local.trace = dict(applied=False,**trace)
            if not spans:
                return native
            supplemental = []
            for row in spans:
                item = dict(id=base.digest([row['source_id'],row['start'],row['end']]),
                            content=self.render(row),score=1.)
                if row['timestamp'] is not None:
                    item['created_at'] = datetime.fromtimestamp(row['timestamp']/1000,timezone.utc).isoformat()
                supplemental.append(item)
            insertion = max([1]+[p+1 for p,h in enumerate(native) if standing_rule.search(h['content'])])
            protected = native[:insertion]
            if sum(len(h['content']) for h in protected+supplemental) > self.config.context_chars:
                self.local.trace.update(reason='protected_context_exhausts_budget')
                return native
            proposal = protected+supplemental+native[insertion:]
            output=[]; used=0; seen=set()
            for hit in proposal:
                if hit['id'] in seen:
                    continue
                if used+len(hit['content']) > self.config.context_chars or len(output)>=top_k:
                    break
                output.append({**hit,'score':1/(len(output)+1)})
                seen.add(hit['id']); used+=len(hit['content'])
            pool_sources={index.rows[i]['source_id'] for i in self.local.order[:128]}
            self.local.trace.update(applied=output!=native,insertion=insertion,
                outside_initial128=[r['source_id'] for r in spans if r['source_id'] not in pool_sources],
                removed_native_ids=[h['id'] for h in native if h['id'] not in seen],
                added_ids=[h['id'] for h in supplemental])
            return output
    return UserHistoryStore
