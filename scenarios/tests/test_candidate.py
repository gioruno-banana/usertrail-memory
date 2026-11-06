from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import tempfile
import threading
from types import SimpleNamespace
import unittest
import numpy as np
from usertrail import candidates as c
from coordination import model_lock


def tokenize(text):
    return set(re.findall(r'[a-z]+',text.lower()))-set('i my the a is it in and me what which for do you'.split())


def row(sid,text,role='user',date=1):
    return dict(id=sid,source_id=sid,start=0,end=len(text),content=text,role=role,
                timestamp=date,request_id='batch',session_id='session',position=0)


class HistoryTests(unittest.TestCase):
    def test_full_original_keeps_negation_condition_and_reason(self):
        text='I do not eat shellfish unless my doctor clears it. Because it caused a reaction.'
        result=c.literal_context(row('a',text),{'shellfish'},tokenize)
        self.assertEqual(result['content'],text)
        self.assertEqual(result['start'],0)

    def test_long_source_uses_literal_complete_context(self):
        text='A quiet preface. '+('Unrelated complete statement. '*60)+'I avoid shellfish unless cleared. Because I had a reaction. Another sentence.'
        result=c.literal_context(row('a',text),{'shellfish'},tokenize)
        self.assertIn('I avoid shellfish unless cleared. Because I had a reaction.',result['content'])
        self.assertEqual(text[result['start']:result['end']],result['content'])
        self.assertLessEqual(len(result['content']),c.SETTINGS['source_chars'])

    def test_questions_are_not_standalone_user_assertions(self):
        self.assertIsNone(c.literal_context(row('a','Should I eat shellfish?'),{'shellfish'},tokenize))

    def test_global_scan_excludes_assistant_without_rank_cutoff(self):
        sources=[row(str(i),'A generic statement.') for i in range(150)]
        sources += [row('far','I prefer shellfish meals.'),row('bot','You should prefer shellfish.','assistant')]
        index=SimpleNamespace(rows=sources,view_lock=threading.RLock())
        def merge(index,ids):return [(p,index.rows[i]) for p,i in enumerate(ids)]
        all_users,chunks=c.full_user_sources(index,merge)
        self.assertIn('far',{r['source_id'] for r in all_users})
        self.assertNotIn('bot',chunks)
        self.assertEqual(len(all_users),151)

    def test_topic_dossier_keeps_dated_conflicts(self):
        sources=[row('old','I eat shellfish meals.',date=100),row('new','I avoid shellfish meals now.',date=200),row('other','I enjoy mountain cycling.',date=150)]
        index=SimpleNamespace(matrix=np.ones((3,2),np.float32)/np.sqrt(2))
        chunks={r['source_id']:[p] for p,r in enumerate(sources)}
        selected,trace=c.dossier(index,sources,chunks,'Which shellfish meals suit my needs?',np.ones(2,np.float32)/np.sqrt(2),tokenize,None,lambda r:r['content'],'')
        self.assertEqual([r['source_id'] for r in selected],['old','new'])
        self.assertTrue(trace['all_dated'])

    def test_no_invented_chronology_for_undated_sources(self):
        sources=[row('one','I avoid shellfish meals.',date=None)]
        index=SimpleNamespace(matrix=np.ones((1,2),np.float32)/np.sqrt(2))
        selected,trace=c.dossier(index,sources,{'one':[0]},'Which shellfish meals suit me?',np.ones(2,np.float32)/np.sqrt(2),tokenize,None,lambda r:r['content'],'')
        self.assertIsNone(selected[0]['timestamp'])
        self.assertFalse(trace['all_dated'])

    def test_no_intervention_when_all_matching_statements_in_prefix(self):
        source=row('one','I avoid shellfish meals.')
        index=SimpleNamespace(matrix=np.ones((1,2),np.float32)/np.sqrt(2))
        selected,trace=c.dossier(index,[source],{'one':[0]},'Which shellfish meals suit me?',np.ones(2,np.float32)/np.sqrt(2),tokenize,None,lambda r:r['content'],source['content'])
        self.assertEqual(selected,[])

    def test_document_and_rule_routes_are_native(self):
        hit={'id':'x','content':'[user] Original rule and document.', 'score':1.}
        class Native:
            def __init__(self):pass
            def ranked(self,*args,**kwargs):return ([0],True)
            def search(self,**kwargs):
                self.ranked(return_document_prior=True)
                return [dict(hit)]
        cls=c.store_class(SimpleNamespace(MemoryStore=Native),None,re.compile('rule'))
        store=cls()
        self.assertEqual(store.search(user_id='u',query='Which meals suit me?',mode='query_document_evidence'),[hit])
        self.assertEqual(store.local.trace['reason'],'native_document')

    def test_lock_never_releases_foreign_owner(self):
        old=model_lock.LOCK
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            model_lock.LOCK=Path(folder)/'public.lock'
            try:
                with model_lock.ModelLock() as owned:
                    before=(model_lock.LOCK/'owner.json').read_bytes()
                    with self.assertRaises(FileExistsError):
                        with model_lock.ModelLock():pass
                    owned.assert_owned()
                    self.assertEqual((model_lock.LOCK/'owner.json').read_bytes(),before)
                self.assertFalse(model_lock.LOCK.exists())
            finally:model_lock.LOCK=old


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(HistoryTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    Path(__file__).with_name('tests.json').write_text(json.dumps(dict(passed=result.wasSuccessful(),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors)),indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
