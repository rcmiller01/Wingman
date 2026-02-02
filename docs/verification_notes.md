# Verification Notes

## Environment Limitations

### Docker Compose
Command:
```bash
docker compose up -d postgres qdrant backend
```
Output:
```
bash: command not found: docker
```

### Python Dependencies (aiosqlite)
Command:
```bash
python -m pip install -r backend/requirements.txt aiosqlite
```
Output:
```
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProxyError('Cannot connect to proxy.', OSError('Tunnel connection failed: 403 Forbidden'))': /simple/aiosqlite/
WARNING: Retrying (Retry(total=3, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProxyError('Cannot connect to proxy.', OSError('Tunnel connection failed: 403 Forbidden'))': /simple/aiosqlite/
WARNING: Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProxyError('Cannot connect to proxy.', OSError('Tunnel connection failed: 403 Forbidden'))': /simple/aiosqlite/
WARNING: Retrying (Retry(total=1, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProxyError('Cannot connect to proxy.', OSError('Tunnel connection failed: 403 Forbidden'))': /simple/aiosqlite/
WARNING: Retrying (Retry(total=0, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProxyError('Cannot connect to proxy.', OSError('Tunnel connection failed: 403 Forbidden'))': /simple/aiosqlite/
ERROR: Could not find a version that satisfies the requirement aiosqlite (from versions: none)
ERROR: No matching distribution found for aiosqlite
```

## Backend Startup (Local uvicorn)
Command:
```bash
PYTHONPATH=backend timeout 10 python -m uvicorn homelab.main:app --host 127.0.0.1 --port 8000
```
Output:
```
[DockerAdapter] Failed to connect: Error while fetching server API version: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))
/workspace/Wingman/backend/homelab/rag/rag_indexer.py:30: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
  self.client = QdrantClient(url=settings.qdrant_url)
INFO:     Started server process [4706]
INFO:     Waiting for application startup.
ERROR:    Traceback (most recent call last):
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/starlette/routing.py", line 694, in lifespan
    async with self.lifespan_context(app) as maybe_state:
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/contextlib.py", line 199, in __aenter__
    return await anext(self.gen)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/fastapi/routing.py", line 153, in merged_lifespan
    async with original_context(app) as maybe_original_state:
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/contextlib.py", line 199, in __aenter__
    return await anext(self.gen)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/fastapi/routing.py", line 153, in merged_lifespan
    async with original_context(app) as maybe_original_state:
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/contextlib.py", line 199, in __aenter__
    return await anext(self.gen)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/fastapi/routing.py", line 153, in merged_lifespan
    async with original_context(app) as maybe_original_state:
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/contextlib.py", line 199, in __aenter__
    return await anext(self.gen)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/fastapi/routing.py", line 153, in merged_lifespan
    async with original_context(app) as maybe_original_state:
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/contextlib.py", line 199, in __aenter__
    return await anext(self.gen)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/fastapi/routing.py", line 153, in merged_lifespan
    async with original_context(app) as maybe_original_state:
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/contextlib.py", line 199, in __aenter__
    return await anext(self.gen)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/fastapi/routing.py", line 153, in merged_lifespan
    async with original_context(app) as maybe_original_state:
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/contextlib.py", line 199, in __aenter__
    return await anext(self.gen)
  File "/workspace/Wingman/backend/homelab/main.py", line 29, in lifespan
    await init_db()
  File "/workspace/Wingman/backend/homelab/storage/database.py", line 44, in init_db
    async with engine.begin() as conn:
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/contextlib.py", line 199, in __aenter__
    return await anext(self.gen)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/ext/asyncio/engine.py", line 1068, in begin
    async with conn:
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/ext/asyncio/base.py", line 121, in __aenter__
    return await self.start(is_ctxmanager=True)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/ext/asyncio/engine.py", line 275, in start
    await greenlet_spawn(self.sync_engine.connect)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn
    result = context.throw(*sys.exc_info())
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/opentelemetry/instrumentation/sqlalchemy/engine.py", line 120, in _wrap_connect_internal
    return func(*args, **kwargs)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/engine/base.py", line 3285, in connect
    return self._connection_cls(self)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/engine/base.py", line 143, in __init__
    self._dbapi_connection = engine.raw_connection()
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/engine/base.py", line 3309, in raw_connection
    return self.pool.connect()
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/pool/base.py", line 447, in connect
    return _ConnectionFairy._checkout(self)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/pool/base.py", line 1264, in _checkout
    fairy = _ConnectionRecord.checkout(pool)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/pool/base.py", line 711, in checkout
    rec = pool._do_get()
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/pool/impl.py", line 177, in _do_get
    with util.safe_reraise():
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/util/langhelpers.py", line 224, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/pool/impl.py", line 175, in _do_get
    return self._create_connection()
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/pool/base.py", line 388, in _create_connection
    return _ConnectionRecord(self)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/pool/base.py", line 673, in __init__
    self.__connect()
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/pool/base.py", line 899, in __connect
    with util.safe_reraise():
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/util/langhelpers.py", line 224, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/pool/base.py", line 895, in __connect
    self.dbapi_connection = connection = pool._invoke_creator(self)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/engine/create.py", line 661, in connect
    return dialect.connect(*cargs, **cparams)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/engine/default.py", line 630, in connect
    return self.loaded_dbapi.connect(*cargs, **cparams)  # type: ignore[no-any-return]  # NOQA: E501
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 955, in connect
    await_only(creator_fn(*arg, **kw)),
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/asyncpg/connection.py", line 2443, in connect
    return await connect_utils._connect(
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/asyncpg/connect_utils.py", line 1249, in _connect
    raise last_error or exceptions.TargetServerAttributeNotMatched(
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/asyncpg/connect_utils.py", line 1218, in _connect
    conn = await _connect_addr(
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/asyncpg/connect_utils.py", line 1054, in _connect_addr
    return await __connect_addr(params, True, *args)
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/asyncpg/connect_utils.py", line 1099, in __connect_addr
    tr, pr = await connector
  File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/asyncpg/connect_utils.py", line 969, in _create_ssl_connection
    tr, pr = await loop.create_connection(
  File "uvloop/loop.pyx", line 1982, in create_connection
socket.gaierror: [Errno -2] Name or service not known

ERROR:    Application startup failed. Exiting.
WARNING:opentelemetry.exporter.otlp.proto.grpc.exporter:Transient error StatusCode.UNAVAILABLE encountered while exporting traces to localhost:4317, retrying in 1.17s.
```
