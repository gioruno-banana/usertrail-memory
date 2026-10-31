from pathlib import Path
import importlib.util
import re
import threading
from types import SimpleNamespace
import unittest

import numpy as np

spec = importlib.util.spec_from_file_location('v3_candidate', Path(__file__).resolve().parents[1] / 'candidate.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class BM25:
    def __init__(self, texts):
        self.texts = texts

    def scores(self, query):
        terms = set(re.findall(r'\w+', query.lower()))
        return np.asarray([len(terms & set(re.findall(r'\w+', t.lower()))) for t in self.texts])


def fixture(remote_role='user'):
    rows = [dict(source_id='s'+str(i), role='assistant', content='unrelated', start=0, end=9) for i in range(500)]
    rows.append(dict(source_id='remote', role=remote_role,
        content='I avoid shellfish unless cleared. Because I had a reaction.', start=0, end=58))
    rows[1]['content'] = 'shellfish reaction context from another speaker'
    matrix = np.zeros((501, 2), np.float32)
    matrix[:, 1] = 1
    matrix[500] = [1, 0]
    matrix[1] = [.9, .1]
    index = SimpleNamespace(rows=rows, matrix=matrix, view_lock=threading.RLock())
    merge = lambda index, ids: [(p, index.rows[i]) for p,i in enumerate(ids)]
    return index, merge, SimpleNamespace(BM25=BM25)


class SourceCompetitionTests(unittest.TestCase):
    def test_outside_actual_pool_user_can_enter_with_other_role_context(self):
        index, merge, base = fixture()
        order, trace = c.compete(index, list(range(501)), 'shellfish reaction',
            np.asarray([1., 0.]), merge, base, .7, 400)
        self.assertEqual(order[0], 0)
        self.assertIn(500, order[:400])
        self.assertIn(1, order[:400])
        self.assertEqual(trace['outside_native_pool'], ['remote'])

    def test_no_activation_without_outside_pool_user(self):
        index, merge, base = fixture()
        native = [500] + list(range(500))
        order, trace = c.compete(index, native, 'shellfish', np.asarray([1., 0.]), merge, base, .7, 400)
        self.assertEqual(order, native)
        self.assertEqual(trace['reason'], 'no_outside_pool_user_rescue')

    def test_assistant_source_is_not_admitted_as_user_rescue(self):
        index, merge, base = fixture(remote_role='assistant')
        native = list(range(501))
        order, trace = c.compete(index, native, 'shellfish', np.asarray([1., 0.]), merge, base, .7, 400)
        self.assertEqual(order, native)
        self.assertEqual(trace['reason'], 'no_user_sources')

    def test_original_metadata_and_text_are_unchanged(self):
        index, merge, base = fixture()
        before = [dict(row) for row in index.rows]
        c.compete(index, list(range(501)), 'dietary restrictions', np.asarray([1., 0.]), merge, base, .7, 400)
        self.assertEqual(index.rows, before)


if __name__ == '__main__':
    unittest.main()
