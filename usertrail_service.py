"""Local-only embedding HTTP adapter; generation/Answer remains external."""
from contextlib import asynccontextmanager
from functools import lru_cache
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from usertrail import create_store, __version__
from adaptive_evidence.api import Add, Search, authenticate
from adaptive_evidence.core import ConflictError


class LocalEncoder:
    def __init__(self, path):
        from adaptive_evidence.encoder import BGEEncoder
        self._encoder = BGEEncoder(path, device='cpu')
        self.identity = self._encoder.identity
        self.model = 'local-bge:' + Path(path).name

    def encode(self, texts, *, query=False):
        return self._encoder.encode(texts, query=query)


@lru_cache(maxsize=1)
def get_store():
    path = os.getenv('USERTRAIL_EMBEDDING_MODEL')
    if not path or not Path(path).is_dir():
        raise RuntimeError('USERTRAIL_EMBEDDING_MODEL must name an existing local BGE directory')
    encoder = LocalEncoder(path)
    return create_store(os.getenv('AE_DATABASE', 'data/usertrail.sqlite3'), encoder)


@asynccontextmanager
async def lifespan(app):
    if not os.getenv('MEMORY_API_KEY') and os.getenv('AE_LOCAL_NO_AUTH') != '1':
        raise RuntimeError('Set MEMORY_API_KEY before starting the service')
    get_store()
    try:
        yield
    finally:
        get_store.cache_clear()


app = FastAPI(title='UserTrail Memory', version=__version__, lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(status_code=422, content={'detail': 'Invalid request schema'})


@app.get('/health')
def health(store=Depends(get_store)):
    return dict(status='ok', system='UserTrail Memory', version=__version__,
        embedding=store.encoder.model, context_chars=24000,
        search_strategy='query_document_evidence+full_history_topic_dossier',
        generative_llm_calls=0, answer_owner='caller', research_candidate=True)


@app.post('/add', dependencies=[Depends(authenticate)])
def add(payload: Add, store=Depends(get_store)):
    try:
        store.add(**payload.model_dump())
    except ConflictError:
        raise HTTPException(409, 'Request ID conflicts with an existing write')
    except (ValueError, OverflowError, OSError):
        raise HTTPException(422, 'Invalid memory data')
    return dict(success=True, request_id=payload.request_id,
                user_id=payload.user_id, session_id=payload.session_id)


@app.post('/search', dependencies=[Depends(authenticate)])
def search(payload: Search, store=Depends(get_store)):
    try:
        return dict(data=store.search(**payload.model_dump(), mode='query_document_evidence'))
    except ValueError:
        raise HTTPException(422, 'Invalid search data')
