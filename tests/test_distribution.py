from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from usertrail import create_store, DemoEncoder
import usertrail_service as service


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = create_store(Path(self.temp.name) / 'memory.sqlite3', DemoEncoder())
        service.app.dependency_overrides[service.get_store] = lambda: self.store
        self.client = TestClient(service.app)

    def tearDown(self):
        self.client.close()
        service.app.dependency_overrides.clear()
        self.temp.cleanup()

    def test_round_trip_role_date_negation_and_user_isolation(self):
        payload = dict(user_id='one', session_id='session', request_id='request', messages=[
            dict(role='user', content='I avoid shellfish unless cleared. Because I had a reaction.', timestamp=1704067200000),
            dict(role='assistant', content='Try shellfish pasta.')])
        with patch.dict('os.environ', {'MEMORY_API_KEY': 'synthetic-test-key'}):
            headers = {'x-api-key': 'synthetic-test-key'}
            self.assertEqual(self.client.post('/add', json=payload, headers=headers).status_code, 200)
            response = self.client.post('/search', headers=headers, json=dict(
                user_id='one', query='Which shellfish meals suit me?', top_k=10))
            self.assertEqual(response.status_code, 200)
            text = '\n'.join(x['content'] for x in response.json()['data'])
            self.assertIn('I avoid shellfish unless cleared. Because I had a reaction.', text)
            self.assertIn('2024-01-01', text)
            self.assertIn('user', text)
            other = self.client.post('/search', headers=headers, json=dict(
                user_id='two', query='Which shellfish meals suit me?', top_k=10))
            self.assertEqual(other.json()['data'], [])

    def test_auth_and_request_id_conflict(self):
        payload = dict(user_id='one', session_id='session', request_id='same',
                       messages=[dict(role='user', content='I prefer rice.')])
        with patch.dict('os.environ', {'MEMORY_API_KEY': 'synthetic-test-key'}):
            self.assertEqual(self.client.post('/add', json=payload).status_code, 401)
            headers = {'x-api-key': 'synthetic-test-key'}
            self.assertEqual(self.client.post('/add', json=payload, headers=headers).status_code, 200)
            self.assertEqual(self.client.post('/add', json=payload, headers=headers).status_code, 200)
            payload['messages'][0]['content'] = 'I prefer pasta.'
            self.assertEqual(self.client.post('/add', json=payload, headers=headers).status_code, 409)

    def test_search_rejects_evaluation_fields(self):
        with patch.dict('os.environ', {'MEMORY_API_KEY': 'synthetic-test-key'}):
            response = self.client.post('/search', headers={'x-api-key': 'synthetic-test-key'},
                json=dict(user_id='one', query='What do I prefer?', top_k=10, answer='forbidden'))
            self.assertEqual(response.status_code, 422)

    def test_health_uses_serializable_local_identity(self):
        data = self.client.get('/health').json()
        self.assertEqual(data['generative_llm_calls'], 0)
        self.assertEqual(data['embedding'], 'synthetic-demo-only')

    def test_model_path_is_explicit_and_no_download(self):
        service.get_store.cache_clear()
        with patch.dict('os.environ', {'USERTRAIL_EMBEDDING_MODEL': ''}):
            with self.assertRaisesRegex(RuntimeError, 'existing local BGE'):
                service.get_store()


if __name__ == '__main__':
    unittest.main()
