"""UserTrail: the frozen research candidate on unchanged exact32 source."""
import hashlib
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'exact32-source'))
from adaptive_evidence import core
from adaptive_evidence.evidence_windows import merged_rows
from adaptive_evidence.focused_packing import STANDING_RULE
import candidate

__version__ = '0.1.0-research'
UserTrailStore = candidate.store_class(core, merged_rows, STANDING_RULE)


def create_store(database, encoder):
    """Use a separate database and explicitly supplied local encoder."""
    return UserTrailStore(database, encoder, core.Config(context_chars=24000))


class DemoEncoder:
    """Deterministic synthetic-demo hashing, not the evaluated BGE model."""
    identity = 'usertrail-synthetic-hash-256-v1'
    model = 'synthetic-demo-only'

    def encode(self, texts, *, query=False):
        vectors = np.zeros((len(texts), 256), dtype=np.float32)
        for p, text in enumerate(texts):
            for word in re.findall(r'\w+', text.casefold()):
                index = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], 'little') % 256
                vectors[p, index] += 1
            if not np.any(vectors[p]):
                vectors[p, 0] = 1
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.maximum(norms, 1e-12)
