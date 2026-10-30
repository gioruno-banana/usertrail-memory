"""Atomic public GPU lock; no stale owner takeover."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import socket
import uuid

RUN=Path(__file__).resolve().parent
LOCK=RUN.parent/'local-model.lock'


class ModelLock:
    def __enter__(self):
        self.nonce=uuid.uuid4().hex
        LOCK.mkdir()  # FileExistsError means a foreign owner; never remove it.
        self.owner=dict(owner='04-user-history',nonce=self.nonce,pid=os.getpid(),
                        run=str(RUN),host=socket.gethostname(),started_utc=datetime.now(timezone.utc).isoformat())
        (LOCK/'owner.json').write_text(json.dumps(self.owner,indent=2),encoding='utf-8')
        return self

    def assert_owned(self):
        value=json.loads((LOCK/'owner.json').read_text(encoding='utf-8-sig'))
        if value.get('nonce')!=self.nonce or value.get('pid')!=os.getpid():
            raise RuntimeError('Public GPU lock ownership changed')

    def __exit__(self,*args):
        self.assert_owned()
        (LOCK/'owner.json').unlink()
        LOCK.rmdir()
