"""m06 production adapter: unchanged V3 retrieval with exact32 HTTP/encoder."""
import hashlib
from pathlib import Path

from usertrail import UserTrailStore
from adaptive_evidence import api as native

ROOT = Path(__file__).resolve().parent
CANDIDATE_SHA = hashlib.sha256((ROOT / 'candidate.py').read_bytes()).hexdigest()
EXPECTED_SHA = '7c42aab6055539082b3a0650b83d15d58bb2749f9851e1d4713a80660fdd951d'
if CANDIDATE_SHA != EXPECTED_SHA:
    raise RuntimeError('Frozen V3 candidate identity differs')
if not issubclass(UserTrailStore, native.MemoryStore):
    raise RuntimeError('V3 must inherit unchanged exact32 MemoryStore')

# Native API creates the store in its startup lifespan. Preserve its remote
# encoder factory, configuration, authentication, schemas and response handlers.
native.MemoryStore = UserTrailStore
native.__version__ = '0.69-usertrail-v3-exploratory'
native.app.version = native.__version__
app = native.app


@app.middleware('http')
async def candidate_identity(request, call_next):
    response = await call_next(request)
    if request.url.path == '/health':
        response.headers['X-UserTrail-Candidate-SHA256'] = CANDIDATE_SHA
        response.headers['X-UserTrail-Store'] = type(native.get_store()).__name__
    return response
