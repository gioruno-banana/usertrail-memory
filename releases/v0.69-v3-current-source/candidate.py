"""All-role source competition, activated only by an outside-pool user rescue."""
from collections import defaultdict
import re
import threading

import numpy as np

RULE_QUERY = re.compile(r'\b(?:procedures?|instructions?|rules?|requirements?|steps?|format|polic(?:y|ies))\b|步骤|流程|规则|指令|格式', re.I)
SETTINGS = dict(rrf_k=60, lexical_weight='native_config.lexical_weight',
                source_competition_roles='all_literal_roles', representatives_per_source=1,
                activate_only_if_user_source_outside_actual_native_pool=True,
                representative_order_then_remaining_native_chunks=True,
                native_first_chunk_preserved=True, native_packing_unchanged=True,
                document_and_rule_query_bypass=True, standing_rule_fallback=True,
                no_personal_trigger=True, no_lexical_threshold=True,
                no_user_role_additive_boost=True)


def source_view(index, merge, base):
    with index.view_lock:
        if not hasattr(index, '_usertrail_v3_sources'):
            chunks = defaultdict(list)
            for i, row in enumerate(index.rows):
                chunks[row['source_id']].append(i)
            sources = [row for _, row in merge(index, list(range(len(index.rows))))]
            index._usertrail_v3_sources = sources, chunks, base.BM25([s['content'] for s in sources])
        return index._usertrail_v3_sources


def compete(index, native, query, vector, merge, base, lexical_weight, pool_size):
    sources, chunks, bm25 = source_view(index, merge, base)
    if not any(s['role'].casefold() == 'user' for s in sources):
        return native, dict(applied=False, reason='no_user_sources')
    cosine = index.matrix @ vector
    representatives = [max(chunks[s['source_id']], key=lambda i: (float(cosine[i]), -i)) for s in sources]
    semantic = np.asarray([cosine[i] for i in representatives])
    scores = np.zeros(len(sources))
    for rank, s in enumerate(np.argsort(-semantic, kind='stable'), 1):
        scores[s] += 1 / (60 + rank)
    lexical = bm25.scores(re.sub(r'^Current date:[^\n]*\n', '', query))
    for rank, s in enumerate(np.argsort(-lexical, kind='stable'), 1):
        if lexical[s] > 0:
            scores[s] += lexical_weight / (60 + rank)
    source_order = list(np.argsort(-scores, kind='stable'))
    # Each role competes under the same score. No user-only additive lane exists.
    order = [representatives[s] for s in source_order]
    included = set(order)
    order += [i for i in native if i not in included]
    order.remove(native[0])
    order.insert(0, native[0])
    old_pool = {index.rows[i]['source_id'] for i in native[:pool_size]}
    old128 = {index.rows[i]['source_id'] for i in native[:128]}
    admitted = list(dict.fromkeys(index.rows[i]['source_id'] for i in order[:pool_size]))
    user_sources = {s['source_id'] for s in sources if s['role'].casefold() == 'user'}
    rescued = [sid for sid in admitted if sid in user_sources and sid not in old_pool]
    if not rescued:
        return native, dict(applied=False, reason='no_outside_pool_user_rescue',
            full_sources=len(sources), native_pool_size=pool_size)
    return order, dict(applied=order != native, reason='all_role_source_competition',
        full_sources=len(sources), native_pool_size=pool_size,
        outside_native_pool=rescued,
        outside_initial128=[sid for sid in admitted if sid in user_sources and sid not in old128],
        selected_sources=[sid for sid in admitted if sid in user_sources],
        lane_sources=[sid for sid in admitted if sid in user_sources],
        all_role_admitted_sources=admitted)


def store_class(base, merge, standing_rule):
    class SourceCompetitionStore(base.MemoryStore):
        def __init__(self, *args, **kwargs):
            self.local = threading.local()
            super().__init__(*args, **kwargs)

        def ranked(self, *args, **kwargs):
            if getattr(self.local, 'rescue', False):
                return (self.local.order, False) if kwargs.get('return_document_prior') else self.local.order
            result = super().ranked(*args, **kwargs)
            if kwargs.get('return_document_prior'):
                self.local.native_order, self.local.document = result
            return result

        def search(self, *, user_id, query, top_k=100, options=None, mode='hybrid_window'):
            self.local.rescue = False
            self.local.document = False
            self.local.trace = dict(applied=False, reason='native_mode')
            native = super().search(user_id=user_id, query=query, top_k=top_k, options=options, mode=mode)
            for condition, reason in ((mode != 'query_document_evidence', 'native_mode'),
                    (not native, 'empty_native'), (self.local.document, 'native_document'),
                    (bool(RULE_QUERY.search(query)), 'rule_query'), (top_k < 8, 'small_top_k')):
                if condition:
                    self.local.trace = dict(applied=False, reason=reason)
                    return native
            index = self.index(user_id)
            with self.encoder_lock:
                vector = np.asarray(self.encoder.encode([query], query=True), dtype=np.float32)[0]
            vector /= np.linalg.norm(vector)
            self.local.order, self.local.trace = compete(index, self.local.native_order, query,
                vector, merge, base, self.config.lexical_weight, max(200, min(512, top_k * 4)))
            if not self.local.trace['applied']:
                return native
            self.local.rescue = True
            try:
                output = super().search(user_id=user_id, query=query, top_k=top_k, options=options, mode=mode)
            finally:
                self.local.rescue = False
            contents = {hit['content'] for hit in output}
            if any(standing_rule.search(hit['content']) and hit['content'] not in contents for hit in native):
                self.local.trace.update(applied=False, reason='native_standing_rule_fallback')
                return native
            self.local.trace['output_changed'] = output != native
            return output
    return SourceCompetitionStore
