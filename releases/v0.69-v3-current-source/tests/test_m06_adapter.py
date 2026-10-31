import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import candidate
from usertrail import DemoEncoder, UserTrailStore
import m06_candidate as service


class M06Adapter(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.test-tmp'
        root.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.database = str(Path(self.temp.name) / 'memory.sqlite3')
        self.env = patch.dict(os.environ, {'AE_DATABASE': self.database,
            'MEMORY_API_KEY': 'synthetic-test-key', 'AE_MODE': 'query_document_evidence',
            'AE_CONTEXT_CHARS': '24000', 'AE_LOCAL_NO_AUTH': '0'})
        self.env.start()
        service.native.get_store.cache_clear()
        self.encoder = patch.object(service.native, 'encoder_from_env', return_value=DemoEncoder())
        self.encoder.start()
        self.client_context = TestClient(service.app)
        self.client = self.client_context.__enter__()
        self.headers = {'X-Api-Key': 'synthetic-test-key'}

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        service.native.get_store.cache_clear()
        self.encoder.stop()
        self.env.stop()
        self.temp.cleanup()

    def test_actual_candidate_identity_and_native_settings(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['version'], '0.69-usertrail-v3-exploratory')
        self.assertEqual(response.headers['X-UserTrail-Candidate-SHA256'], service.EXPECTED_SHA)
        self.assertEqual(response.headers['X-UserTrail-Store'], 'SourceCompetitionStore')
        self.assertIsInstance(service.native.get_store(), UserTrailStore)
        self.assertEqual(response.json()['context_chars'], 24000)
        self.assertEqual(response.json()['generative_llm_calls_in_memory_service'], 0)

    def test_native_authentication_and_namespace(self):
        query = dict(user_id='missing', query='coffee', top_k=10)
        self.assertEqual(self.client.post('/search', json=query).status_code, 401)
        self.assertEqual(self.client.post('/search', json=query,
                         headers={'X-Api-Key':'wrong'}).status_code, 401)
        self.assertEqual(self.client.post('/search', json=query, headers=self.headers).json(), {'data':[]})

    def test_literal_roles_conditions_dates_idempotence_and_candidate_execution(self):
        messages = [{'role':'assistant','content':'You could try regular coffee.','timestamp':1700000000000},
                    {'role':'user','content':'I do not drink regular coffee; I choose decaf only if I have slept enough.',
                     'timestamp':1700000000001}]
        payload = dict(request_id='r1', user_id='u1', session_id='s1', messages=messages)
        for _ in range(2):
            self.assertEqual(self.client.post('/add',json=payload,headers=self.headers).status_code,200)
        changed = {**payload,'messages':[{'role':'user','content':'conflicting synthetic write'}]}
        self.assertEqual(self.client.post('/add',json=changed,headers=self.headers).status_code,409)
        with patch.object(candidate,'compete',wraps=candidate.compete) as competition:
            response=self.client.post('/search',json=dict(user_id='u1',query='Which coffee do I drink?',top_k=10),headers=self.headers)
            self.assertEqual(response.status_code,200)
            self.assertTrue(competition.called)
        db=sqlite3.connect(self.database)
        try:
            rows=db.execute('SELECT role,content,timestamp FROM sources ORDER BY position').fetchall()
            self.assertEqual(rows,[(m['role'],m['content'],m['timestamp']) for m in messages])
        finally:
            db.close()


if __name__=='__main__':
    unittest.main()
