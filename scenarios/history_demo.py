"""Synthetic, offline demo. No model, account, network or real history needed."""
import json
from pathlib import Path
import tempfile

from usertrail import create_store, DemoEncoder


def main():
    with tempfile.TemporaryDirectory() as folder:
        store = create_store(Path(folder) / 'demo.sqlite3', DemoEncoder())
        store.add(user_id='demo', request_id='synthetic-1', session_id='example', messages=[
            dict(role='user', timestamp=1704067200000,
                 content='I used to enjoy shellfish meals on holidays.'),
            dict(role='assistant', timestamp=1704067260000,
                 content='You could try shellfish pasta.'),
            dict(role='user', timestamp=1735689600000,
                 content='I do not eat shellfish unless my doctor clears it. Because it caused a reaction.'),
            dict(role='user', timestamp=1735689660000,
                 content='For dinner I prefer simple rice and vegetable meals.')])
        hits = store.search(user_id='demo', query='Which shellfish meals suit my needs?',
                            top_k=10, mode='query_document_evidence')
        print(json.dumps(dict(demo_only=True, evidence=hits,
                              trace=store.local.trace), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
