# Actian VectorAI DB — Python Client API Reference

> **Package:** `actian_vectorai` v0.1.0b2  
> **Requires:** Python ≥ 3.10  
> **Transport:** gRPC (protobuf)

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Installation](#2-installation)
3. [Client Classes](#3-client-classes)
   - [VectorAIClient (sync)](#vectoraiclient-sync)
   - [AsyncVectorAIClient (async)](#asyncvectoraiclient-async)
4. [Collections Namespace](#4-collections-namespace)
5. [Points Namespace](#5-points-namespace)
   - [CRUD](#crud)
   - [Payload Operations](#payload-operations)
   - [Field Indexes](#field-indexes)
   - [Search](#search)
   - [Count](#count)
   - [Scroll (Pagination)](#scroll-pagination)
   - [Query (Universal)](#query-universal)
   - [Convenience Helpers](#convenience-helpers)
6. [VDE Namespace](#6-vde-namespace)
   - [Lifecycle](#lifecycle)
   - [Persistence](#persistence)
   - [Status & Statistics](#status--statistics)
   - [Maintenance](#maintenance)
   - [Rebuild Management](#rebuild-management)
   - [Advanced Operations](#advanced-operations)
7. [Filter DSL](#7-filter-dsl)
   - [Field Conditions](#field-conditions)
   - [FilterBuilder](#filterbuilder)
   - [Standalone Condition Factories](#standalone-condition-factories)
   - [Operator Overloads](#operator-overloads)
8. [Hybrid Fusion](#8-hybrid-fusion)
9. [SmartBatcher](#9-smartbatcher)
10. [Resilience](#10-resilience)
    - [CircuitBreaker](#circuitbreaker)
    - [RetryConfig](#retryconfig)
    - [BackpressureController](#backpressurecontroller)
11. [Telemetry / Observability](#11-telemetry--observability)
    - [Structured Logging](#structured-logging)
    - [OpenTelemetry Integration](#opentelemetry-integration)
12. [Models Reference](#12-models-reference)
    - [Vector Types](#vector-types)
    - [Point Types](#point-types)
    - [Collection Config](#collection-config)
    - [Search & Query Models](#search--query-models)
    - [VDE Models](#vde-models)
    - [Common / Filter Models](#common--filter-models)
13. [Enums](#13-enums)
14. [Exceptions](#14-exceptions)
15. [Transport](#15-transport)
    - [Connection Pool](#connection-pool)
    - [TLS / SSL](#tls--ssl)
    - [gRPC Channel Options](#grpc-channel-options)
    - [Interceptor Stack](#interceptor-stack)
    - [REST Transport](#rest-transport)

---

## 1. Quick Start

```python
from actian_vectorai import (
    VectorAIClient,
    VectorParams,
    Distance,
    PointStruct,
)

# Connect
with VectorAIClient("localhost:50051") as client:
    info = client.health_check()
    print(f"Server: {info['title']} v{info['version']}")

    # Create a collection
    client.collections.create(
        "my_collection",
        vectors_config=VectorParams(size=128, distance=Distance.Cosine),
    )

    # Insert points
    client.points.upsert("my_collection", [
        PointStruct(id=1, vector=[0.1] * 128, payload={"color": "red"}),
        PointStruct(id=2, vector=[0.2] * 128, payload={"color": "blue"}),
        PointStruct(id=3, vector=[0.3] * 128, payload={"color": "red"}),
    ])

    # Search
    results = client.points.search(
        "my_collection",
        vector=[0.15] * 128,
        limit=5,
    )
    for r in results:
        print(f"  id={r.id}  score={r.score:.4f}  payload={r.payload}")

    # Clean up
    client.collections.delete("my_collection")
```

### Async Quick Start

```python
import asyncio
from actian_vectorai import AsyncVectorAIClient, VectorParams, Distance, PointStruct

async def main():
    async with AsyncVectorAIClient("localhost:50051") as client:
        await client.collections.create(
            "demo",
            vectors_config=VectorParams(size=64, distance=Distance.Cosine),
        )
        await client.points.upsert("demo", [
            PointStruct(id=1, vector=[0.1] * 64),
        ])
        results = await client.points.search("demo", vector=[0.1] * 64, limit=3)
        print(results)
        await client.collections.delete("demo")

asyncio.run(main())
```

---

## 2. Installation

```bash
pip install actian-vectorai
```

**From source:**

```bash
git clone <repo>
cd cortex.client/clients/python
pip install -e ".[dev]"
```

**Optional dependencies:**

| Extra | Purpose |
|-------|---------|
| `numpy` | Accept `numpy.ndarray` as vector input |
| `dev` | Testing tools (`pytest`, `pytest-asyncio`, etc.) |

---

## 3. Client Classes

The library provides two client classes — a synchronous wrapper and a native async client.
Both expose the same three **namespaces**:

| Property | Type | Description |
|----------|------|-------------|
| `client.collections` | `CollectionsNamespace` | Collection CRUD and lifecycle helpers |
| `client.points` | `PointsNamespace` | Point CRUD, payload, search, and query |
| `client.vde` | `VDENamespace` | VDE engine lifecycle, maintenance, rebuilds |

### VectorAIClient (sync)

Synchronous client — wraps `AsyncVectorAIClient` with an internal event loop.
Supports context manager (`with`) for automatic resource cleanup.

```python
from actian_vectorai import VectorAIClient

client = VectorAIClient(
    url="localhost:50051",       # gRPC server address
    *,
    api_key=None,                # API key for authentication
    tls=False,                   # Enable TLS
    tls_ca_cert=None,            # Path to CA certificate
    tls_client_cert=None,        # Path to client certificate
    tls_client_key=None,         # Path to client key
    timeout=30.0,                # Default RPC timeout (seconds)
    max_message_size=268435456,  # Max message size (256 MiB)
    max_retries=3,               # Max retry count
    pool_size=1,                 # Connection pool size
    enable_tracing=True,         # gRPC tracing
    enable_logging=False,        # Request/response logging
    metadata=None,               # Custom gRPC metadata headers
    grpc_options=None,           # Raw gRPC channel options
)
```

> **Config validation:** The constructor validates that `url` is not empty,
> `timeout > 0` (if provided), `max_message_size > 0`, `max_retries >= 0`,
> and `pool_size >= 1`. Invalid values raise `ValueError`.

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `connect()` | `None` | Establish gRPC channel and verify server reachability (eager health check) |
| `close()` | `None` | Close the gRPC channel and release resources |
| `shutdown()` | `None` | Close and tear down the internal event loop |
| `health_check(*, timeout=None)` | `dict` | Server health — returns `{"title", "version", "commit"}` |
| `upload_points(collection_name, points, *, batch_size=256)` | `int` | Bulk upload with auto-batching; returns total uploaded |

**Context manager:**

```python
with VectorAIClient("localhost:50051") as client:
    # client is connected
    ...
# client.close() called automatically
```

> **Eager health check:** `connect()` performs a health check immediately after
> establishing the gRPC channel. If the server is unreachable, a `ConnectionError`
> is raised and the channel is cleaned up automatically.

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `collections` | `CollectionsNamespace` | Collection operations |
| `points` | `PointsNamespace` | Point operations |
| `vde` | `VDENamespace` | VDE engine operations |
| `is_connected` | `bool` | Whether the channel is open |

### AsyncVectorAIClient (async)

Native async client using `asyncio`. All namespace methods are `async`.

```python
from actian_vectorai import AsyncVectorAIClient

client = AsyncVectorAIClient(
    url="localhost:50051",
    # ... same parameters as VectorAIClient
)
```

**Async context manager:**

```python
async with AsyncVectorAIClient("localhost:50051") as client:
    await client.health_check()
```

**Methods** — same as `VectorAIClient` but all `async`:

```python
await client.connect()            # performs eager health check
await client.close()
await client.health_check(timeout=5.0)
await client.upload_points("my_col", points, batch_size=512)
```

---

## 4. Collections Namespace

Accessed via `client.collections`. Manages collection lifecycle and convenience helpers.

### `create()`

Create a new collection.

```python
client.collections.create(
    name,                                    # Collection name
    *,
    vectors_config=None,                     # VectorParams | dict[str, VectorParams]
    hnsw_config=None,                        # HnswConfigDiff
    wal_config=None,                         # WalConfigDiff
    optimizers_config=None,                  # OptimizersConfigDiff
    quantization_config=None,                # QuantizationConfig
    sparse_vectors_config=None,              # dict[str, Any]
    shard_number=None,                       # int — number of shards
    on_disk_payload=None,                    # bool — store payload on disk
    replication_factor=None,                 # int
    write_consistency_factor=None,           # int
    sharding_method=None,                    # ShardingMethod
    timeout=None,                            # float — override default timeout
    index_type=None,                         # IndexType (VDE extension)
    ivf_config=None,                         # IVF index config (VDE extension)
    extra_params_json=None,                  # str — extra JSON params (VDE extension)
) -> bool
```

**Example — single vector:**

```python
from actian_vectorai import VectorParams, Distance

client.collections.create(
    "products",
    vectors_config=VectorParams(size=384, distance=Distance.Cosine),
)
```

**Example — named vectors:**

```python
client.collections.create(
    "multimodal",
    vectors_config={
        "text":  VectorParams(size=768, distance=Distance.Cosine),
        "image": VectorParams(size=512, distance=Distance.Euclid),
    },
)
```

### `get_info()`

Get detailed information about a collection.

```python
info = client.collections.get_info(name, *, timeout=None) -> CollectionInfo
```

Returns a `CollectionInfo` with `status`, `config`, `points_count`, `segments_count`, `payload_schema`, etc.

**Example:**

```python
info = client.collections.get_info("products")
print(f"Status: {info.status}")
print(f"Points: {info.points_count}")
print(f"Segments: {info.segments_count}")
```

### `list()`

List all collection names.

```python
names = client.collections.list(*, timeout=None) -> list[str]
```

**Example:**

```python
for name in client.collections.list():
    print(name)
```

### `delete()`

Delete a collection and all its data.

```python
client.collections.delete(name, *, strict=True, timeout=None) -> bool
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | — | Collection name |
| `strict` | `bool` | `True` | When `True`, raises `CollectionNotFoundError` if the collection does not exist. When `False`, returns `False` silently |

**Example — strict delete (default):**

```python
client.collections.delete("products")  # raises CollectionNotFoundError if missing
```

**Example — lenient delete:**

```python
client.collections.delete("products", strict=False)  # returns False if missing
```

### `exists()`

Check whether a collection exists.

```python
client.collections.exists(name, *, timeout=None) -> bool
```

**Example:**

```python
if not client.collections.exists("products"):
    client.collections.create("products", vectors_config=VectorParams(size=128, distance=Distance.Cosine))
```

### `update()`

Update collection parameters (HNSW, optimizers, quantization, etc.).

```python
client.collections.update(
    name,
    *,
    optimizers_config=None,                  # OptimizersConfigDiff
    hnsw_config=None,                        # HnswConfigDiff
    vectors_config=None,                     # dict[str, VectorParamsDiff]
    quantization_config=None,                # QuantizationConfigDiff
    sparse_vectors_config=None,              # dict[str, Any]
    timeout=None,
    ivf_config=None,                         # VDE extension
    vde_timeout=None,                        # VDE extension
) -> bool
```

**Example:**

```python
from actian_vectorai import HnswConfigDiff, OptimizersConfigDiff

client.collections.update(
    "products",
    hnsw_config=HnswConfigDiff(ef_construct=200, m=32),
    optimizers_config=OptimizersConfigDiff(indexing_threshold=10000),
)
```

### `recreate()`

Drop (if exists) and re-create a collection. Accepts the same keyword arguments as `create()`.

```python
client.collections.recreate(
    name,
    *,
    vectors_config=None,
    timeout=None,
    **kwargs,
) -> bool
```

**Example:**

```python
# Clean slate — drop and recreate
client.collections.recreate(
    "products",
    vectors_config=VectorParams(size=128, distance=Distance.Cosine),
)
```

### `get_or_create()`

Get an existing collection or create it if it doesn't exist.

```python
info = client.collections.get_or_create(
    name,
    *,
    vectors_config=None,
    timeout=None,
    **kwargs,
) -> CollectionInfo
```

**Example:**

```python
# Idempotent setup — safe to call repeatedly
info = client.collections.get_or_create(
    "products",
    vectors_config=VectorParams(size=128, distance=Distance.Cosine),
)
print(f"Points: {info.points_count}")
```

---

## 5. Points Namespace

Accessed via `client.points`. All point-level operations: CRUD, payload updates, search, and query.

### CRUD

#### `upsert()`

Insert or update points. If a point with the same ID exists, it is overwritten.

```python
result = client.points.upsert(
    collection_name,
    points,                     # list[PointStruct]
    *,
    wait=None,                  # bool — wait for indexing
    ordering=None,              # WriteOrdering
    timeout=None,
) -> UpdateResult
```

**Example:**

```python
from actian_vectorai import PointStruct

client.points.upsert("products", [
    PointStruct(id=1, vector=[0.1, 0.2, 0.3], payload={"name": "Widget"}),
    PointStruct(id=2, vector=[0.4, 0.5, 0.6], payload={"name": "Gadget"}),
])
```

#### `get()`

Retrieve points by ID.

```python
points = client.points.get(
    collection_name,
    ids,                         # list[int | str]
    *,
    with_payload=True,           # bool | WithPayloadSelector
    with_vectors=False,          # bool | WithVectorsSelector
    timeout=None,
) -> list[RetrievedPoint]
```

**Example:**

```python
points = client.points.get("products", [1, 2, 3], with_vectors=True)
for p in points:
    print(f"id={p.id}  payload={p.payload}  vector_len={len(p.vectors)}")
```

#### `delete()`

Delete points by IDs or filter.

```python
result = client.points.delete(
    collection_name,
    *,
    ids=None,                   # list[int | str]
    filter=None,                # Filter
    wait=None,
    ordering=None,
    strict=True,                # bool — verify all IDs exist before deleting
    track_ids=False,            # bool — populate deleted_ids / failed_ids on result
    timeout=None,
) -> UpdateResult
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ids` | `list[int \| str] \| None` | `None` | Point IDs to delete |
| `filter` | `Filter \| None` | `None` | Delete points matching filter |
| `strict` | `bool` | `True` | When `True` + `ids`, pre-checks all IDs exist; raises `PointNotFoundError` listing missing IDs without deleting anything. When `False`, non-existent IDs are silently skipped |
| `track_ids` | `bool` | `False` | When `True`, populates `result.deleted_ids` (IDs that existed and were deleted) and `result.failed_ids` (IDs not found). In strict mode this reuses the existing pre-fetch at no extra cost. In non-strict mode it adds one extra `GetPoints` RPC |
| `wait` | `bool \| None` | `None` | Wait for indexing |
| `ordering` | `WriteOrdering \| None` | `None` | Write ordering |

**Example — delete by IDs:**

```python
client.points.delete("products", ids=[1, 2, 3])
```

**Example — strict delete (fail if any ID missing):**

```python
try:
    client.points.delete("products", ids=[1, 2, 999], strict=True)
except PointNotFoundError as e:
    print(f"Missing IDs: {e.ids}")
```

**Example — non-strict delete with ID tracking:**

```python
result = client.points.delete(
    "products", ids=[1, 2, 999], strict=False, track_ids=True
)
print(result.deleted_ids)   # [1, 2]
print(result.failed_ids)    # [999]
```

**Example — delete by filter:**

```python
from actian_vectorai import Field, FilterBuilder

f = FilterBuilder().must(Field("status").eq("archived")).build()
client.points.delete("products", filter=f)
```

> **Note:** `ids` and `filter` are mutually exclusive — providing both raises `ValidationError`.
> `track_ids` only applies when `ids` are provided; it has no effect on filter-based deletes.

#### `update_vectors()`

Update vectors for existing points without replacing the entire point.

```python
result = client.points.update_vectors(
    collection_name,
    points,                      # list[dict] — each has "id" and "vector"/"vectors"
    *,
    wait=None,
    ordering=None,
    timeout=None,
) -> UpdateResult
```

**Example:**

```python
client.points.update_vectors("products", [
    {"id": 1, "vector": [0.11, 0.22, 0.33]},
])
```

### Payload Operations

#### `set_payload()`

Merge payload fields into existing points. Existing fields not in the new payload are preserved.

```python
client.points.set_payload(
    collection_name,
    payload,                     # dict[str, Any]
    *,
    ids=None,                    # list[int | str]
    filter=None,                 # Filter
    wait=None,
    ordering=None,
    key=None,                    # str — nested key path
    timeout=None,
) -> UpdateResult
```

**Example:**

```python
# Add/update fields for specific points
client.points.set_payload("products", {"sale": True, "discount": 0.2}, ids=[1, 2])

# Update by filter
f = FilterBuilder().must(Field("category").eq("electronics")).build()
client.points.set_payload("products", {"featured": True}, filter=f)

# Set nested key
client.points.set_payload("products", {"city": "NYC"}, ids=[1], key="address")
```

#### `overwrite_payload()`

Replace the entire payload for targeted points.

```python
client.points.overwrite_payload(
    collection_name,
    payload,
    *,
    ids=None, filter=None, wait=None, ordering=None, key=None, timeout=None,
) -> UpdateResult
```

**Example:**

```python
# Replace entire payload (removes all existing fields)
client.points.overwrite_payload("products", {"name": "New Widget", "v": 2}, ids=[1])
```

#### `delete_payload()`

Remove specific payload keys.

```python
client.points.delete_payload(
    collection_name,
    keys,                        # list[str] — payload keys to remove
    *,
    ids=None, filter=None, wait=None, ordering=None,
    strict=True,                 # bool — verify all IDs exist before modifying
    timeout=None,
) -> UpdateResult
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `keys` | `list[str]` | — | Payload keys to remove |
| `ids` | `list[int \| str] \| None` | `None` | Target point IDs |
| `filter` | `Filter \| None` | `None` | Target points matching filter |
| `strict` | `bool` | `True` | When `True` + `ids`, pre-checks all IDs exist; raises `PointNotFoundError` listing missing IDs without modifying anything. When `False`, non-existent IDs are silently skipped |
| `wait` | `bool \| None` | `None` | Wait for indexing |
| `ordering` | `WriteOrdering \| None` | `None` | Write ordering |

> **Note:** `ids` and `filter` are mutually exclusive.

**Example:**

```python
client.points.delete_payload("products", ["temporary_flag", "debug_info"], ids=[1, 2, 3])
```

**Example — lenient (skip missing IDs):**

```python
client.points.delete_payload("products", ["tag"], ids=[1, 999], strict=False)
```

#### `clear_payload()`

Remove all payload from targeted points.

```python
client.points.clear_payload(
    collection_name,
    *,
    ids=None, filter=None, wait=None, ordering=None, timeout=None,
) -> UpdateResult
```

**Example:**

```python
client.points.clear_payload("products", ids=[1, 2])
```

### Field Indexes

Create indexes on payload fields for efficient filtering.

> **Live-server status:** dynamic field-index creation currently returns `UNIMPLEMENTED`.
> Define payload schema indexes at collection creation time until server support lands.

```python
# Create index
client.points.create_field_index(
    collection_name,
    field_name,                 # str — payload field to index
    field_type=None,            # FieldType (Keyword, Integer, Float, Geo, Text, etc.)
    *,
    field_index_params=None,    # PayloadIndexParams for advanced config
    wait=None,
    ordering=None,
    timeout=None,
) -> UpdateResult
```

**Example:**

```python
from actian_vectorai import FieldType

client.points.create_field_index("products", "category", FieldType.FieldTypeKeyword)
client.points.create_field_index("products", "price", FieldType.FieldTypeFloat)
```

### Search

#### `search()`

Vector similarity search — find the nearest neighbors to a query vector.

```python
results = client.points.search(
    collection_name,
    vector,                      # list[float] | numpy.ndarray | DenseVector
    *,
    limit=10,                    # max results
    filter=None,                 # Filter
    params=None,                 # SearchParams
    score_threshold=None,        # float — min score cutoff
    offset=None,                 # int — skip N results (pagination)
    using=None,                  # str — named vector to search
    with_payload=True,           # bool | WithPayloadSelector
    with_vectors=False,          # bool | WithVectorsSelector
    sparse_indices=None,         # list[int] — sparse vector indices
    timeout=None,
) -> list[ScoredPoint]
```

**Example:**

```python
results = client.points.search(
    "products",
    vector=[0.1, 0.2, 0.3, ...],
    limit=5,
    score_threshold=0.7,
)
for r in results:
    print(f"id={r.id}  score={r.score:.4f}  payload={r.payload}")
```

**Example — with filter:**

```python
from actian_vectorai import Field, FilterBuilder

f = (
    FilterBuilder()
    .must(Field("category").eq("electronics"))
    .must(Field("price").lte(100.0))
    .build()
)
results = client.points.search("products", vector=query, limit=10, filter=f)
```

**Example — with search params:**

```python
from actian_vectorai import SearchParams

results = client.points.search(
    "products",
    vector=query,
    limit=10,
    params=SearchParams(hnsw_ef=128, exact=False),
)
```

**Example — named vector search:**

```python
# Search the "image" vector in a named-vector collection
results = client.points.search(
    "multimodal",
    vector=image_embedding,
    using="image",
    limit=10,
)
```

**Example — sparse vector search:**

> **Live-server status:** sparse write/search flows are server-limited in the current build
> and may return validation errors depending on collection/vector configuration.

```python
results = client.points.search(
    "products",
    vector=[0.5, 0.8, 0.3],        # non-zero values
    sparse_indices=[10, 42, 99],     # corresponding indices
    using="sparse",
    limit=10,
)
```

#### `search_batch()`

Execute multiple search requests in a single RPC call.
Maximum 100 searches per batch; raises `ValidationError` if empty or exceeds limit.

```python
batch_results = client.points.search_batch(
    collection_name,
    searches,                    # list[dict] — each dict mirrors search() kwargs
    *,
    timeout=None,
) -> list[list[ScoredPoint]]
```

**Example:**

```python
results = client.points.search_batch("products", [
    {"vector": query1, "limit": 5},
    {"vector": query2, "limit": 10, "filter": f},
])
# results[0] → list[ScoredPoint] for query1
# results[1] → list[ScoredPoint] for query2
```

### Count

#### `count()`

Count points, optionally with a filter.

```python
n = client.points.count(
    collection_name,
    *,
    filter=None,
    exact=True,                  # True = exact count; False = approximate
    timeout=None,
) -> int
```

**Example:**

```python
total = client.points.count("products")
print(f"Total points: {total}")

# Count with filter
f = FilterBuilder().must(Field("category").eq("electronics")).build()
electronics = client.points.count("products", filter=f)
print(f"Electronics: {electronics}")
```

### Scroll (Pagination)

Iterate through all points in a collection without specifying an explicit
limit upfront. Scroll is the recommended approach for batch operations, backups,
and point enumeration. Returns a paginated set of `RetrievedPoint` objects along
with a next-page offset for manual or automatic pagination control.

#### `scroll()`

Retrieve a page of points with automatic offset tracking for pagination.

```python
points, next_offset = client.points.scroll(
    collection_name,
    offset=None,                 # int | str — page marker (None = start)
    limit=10,                    # int > 0 — max points per page
    filter=None,                 # Filter — optional filter
    order_by=None,               # OrderBy — optional sort
    with_payload=True,           # bool — include payload data
    with_vectors=False,          # bool — include vector data
    consistency=None,            # ReadConsistency
    shard_key_selector=None,     # ShardKeySelector
    timeout=None,
) -> tuple[list[RetrievedPoint], PointIdValue | None]
```

**Returns:**
- `tuple[list[RetrievedPoint], PointIdValue | None]`:
  - First element: list of points on this page
  - Second element: offset for the next page (None = end of collection)

**Parameters:**
- `limit` (int > 0): Raises `ValidationError` if ≤ 0. Defaults to server limit of 10.
- `offset`: Point ID (int or str/UUID) or None to start from beginning.
- `filter`: Optional `Filter` object (created via `FilterBuilder`).
- `order_by`: Optional sorting order.
- `with_payload`: Include point payload (default: `True`).
- `with_vectors`: Include vector data (default: `False`).
- Additional parameters: `consistency`, `shard_key_selector`, `timeout`.

**Example — basic scroll:**

```python
points, next_offset = client.points.scroll("products", limit=100)
for p in points:
    print(f"id={p.id}, payload={p.payload}")
```

**Example — scroll with filter:**

```python
from actian_vectorai import FilterBuilder, Field

f = FilterBuilder().must(Field("category").eq("electronics")).build()
points, next_offset = client.points.scroll("products", filter=f, limit=50)

while True:
    for p in points:
        process(p)
    if next_offset is None:
        break
    points, next_offset = client.points.scroll(
        "products", offset=next_offset, filter=f, limit=50
    )
```

#### `scroll_all()`

Async generator that automatically handles pagination, yielding complete pages
until the collection is exhausted. Convenient for iterating through all matching
points without manual offset management.

```python
async for points in client.points.scroll_all(
    collection_name,
    limit=10,                    # int > 0 — page size
    filter=None,                 # Filter
    order_by=None,               # OrderBy
    with_payload=True,           # bool
    with_vectors=False,          # bool
    consistency=None,             # ReadConsistency
    shard_key_selector=None,     # ShardKeySelector
    timeout=None,
) -> AsyncGenerator[list[RetrievedPoint], None]
```

**Example — iterate all points:**

```python
async for points_page in client.points.scroll_all("products", limit=100):
    print(f"Received {len(points_page)} points")
    for p in points_page:
        await process_async(p)
```

**Example — collect all matching points:**

```python
f = FilterBuilder().must(Field("in_stock").eq(True)).build()

all_points = []
async for points_page in client.points.scroll_all("products", filter=f):
    all_points.extend(points_page)

print(f"Total in-stock products: {len(all_points)}")
```

**Example — with vectors:**

```python
async for points_page in client.points.scroll_all(
    "products",
    with_vectors=True,
    limit=50
):
    for p in points_page:
        # p.vectors contains the raw vector data (list[float])
        embeddings = p.vectors  # Can use for re-indexing, backups, etc.
        print(f"Point {p.id}: {len(embeddings)} dimensions")
```

### Query (Universal)

The universal query endpoint covers nearest-neighbor queries and hybrid
multi-stage queries with prefetch through one method.

> **Live-server note:** filter-only query bodies are currently rejected by the
> server unless a query/prefetch clause is provided.

#### `query()`

```python
results = client.points.query(
    collection_name,
    *,
    query=None,                  # list[float] | int | str | dict — the query
    prefetch=None,               # list[PrefetchQuery] — multi-stage prefetch
    using=None,                  # str — named vector to use
    filter=None,                 # Filter
    params=None,                 # SearchParams
    score_threshold=None,
    limit=10,
    offset=None,
    with_payload=True,
    with_vectors=False,
    lookup_from=None,            # dict[str, str] — cross-collection lookup
    timeout=None,
) -> list[ScoredPoint]
```

**Example — simple vector query:**

```python
results = client.points.query("products", query=[0.1, 0.2, 0.3])
```

**Example — query with dict (order by payload field):**

```python
results = client.points.query("products", query={"order_by": "price"})
```

**Example — query with fusion (server-side):**

```python
from actian_vectorai import Fusion

results = client.points.query("products", query={"fusion": Fusion.RRF})
```

**Example — query with random sampling:**

```python
from actian_vectorai import Sample

results = client.points.query("products", query={"sample": Sample.Random}, limit=20)
```

**Example — multi-stage prefetch (hybrid):**

```python
from actian_vectorai import PrefetchQuery

results = client.points.query(
    "products",
    prefetch=[
        PrefetchQuery(using="text", limit=50),
        PrefetchQuery(using="image", limit=50),
    ],
    query=[0.1] * 128,   # fusion query
    limit=10,
)
```

#### `query_batch()`

Batch multiple query requests.
Maximum 100 queries per batch; raises `ValidationError` if empty or exceeds limit.

```python
batch_results = client.points.query_batch(
    collection_name,
    queries,                     # list[dict]
    *,
    timeout=None,
) -> list[list[ScoredPoint]]
```

### Convenience Helpers

#### `upsert_single()`

Upsert a single point without wrapping in a list.

```python
result = client.points.upsert_single(
    collection_name,
    id,                          # int | str
    vector,                      # list[float] | numpy.ndarray
    payload=None,                # dict[str, Any]
    *,
    wait=None,
    timeout=None,
) -> UpdateResult
```

**Example:**

```python
client.points.upsert_single(
    "products", id=42, vector=[0.1] * 128, payload={"name": "Widget"}
)
```

#### `delete_by_ids()`

Delete points by a list of IDs (convenience wrapper around `delete()`).

```python
result = client.points.delete_by_ids(
    collection_name,
    ids,                         # list[int | str]
    *,
    wait=None,
    strict=True,                 # bool — verify all IDs exist before deleting
    timeout=None,
) -> UpdateResult
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ids` | `list[int \| str]` | — | Point IDs to delete |
| `strict` | `bool` | `True` | When `True`, pre-checks all IDs exist; raises `PointNotFoundError` listing missing IDs without deleting anything. When `False`, non-existent IDs are silently skipped |
| `wait` | `bool \| None` | `None` | Wait for indexing |

**Example:**

```python
client.points.delete_by_ids("products", [1, 2, 3], wait=True)
```

**Example — lenient (skip missing IDs):**

```python
client.points.delete_by_ids("products", [1, 2, 999], strict=False)
```

---

## 6. VDE Namespace

Accessed via `client.vde`. Provides Actian's proprietary Vector Database Engine operations
for collection lifecycle, persistence, maintenance, and advanced rebuild management.

### Lifecycle

```python
# Open a collection for read/write
client.vde.open_collection(name, *, timeout=None) -> bool

# Close a collection, releasing server resources
client.vde.close_collection(name, *, timeout=None) -> bool
```

**Example:**

```python
client.vde.open_collection("products")
count = client.vde.get_vector_count("products")
print(f"Vectors: {count}")
client.vde.close_collection("products")
```

### Persistence

```python
# Save a snapshot to persistent storage
client.vde.save_snapshot(name, *, timeout=None) -> bool

# Load a collection from its latest snapshot
client.vde.load_snapshot(name, *, timeout=None) -> bool
```

**Example:**

```python
# Persist current state
client.vde.save_snapshot("products")

# Later: restore from snapshot
client.vde.load_snapshot("products")
```

### Status & Statistics

```python
# Get collection state (READY, REBUILDING, STATE_ERROR)
state = client.vde.get_state(name, *, timeout=None) -> CollectionState

# Get total vector count
count = client.vde.get_vector_count(name, *, timeout=None) -> int

# Get detailed statistics
stats = client.vde.get_stats(name, *, timeout=None) -> CollectionStats

# Get optimization status
opts = client.vde.get_optimizations(
    name,
    *,
    include_completed=None,      # bool
    completed_limit=None,        # int
    timeout=None,
) -> OptimizationsResponse
```

`CollectionStats` fields: `total_vectors`, `indexed_vectors`, `deleted_vectors`,
`storage_bytes`, `index_memory_bytes`.

**Example:**

```python
state = client.vde.get_state("products")
print(f"State: {state}")  # CollectionState.READY

stats = client.vde.get_stats("products")
print(f"Vectors: {stats.total_vectors}, Indexed: {stats.indexed_vectors}")
print(f"Storage: {stats.storage_bytes / 1024 / 1024:.1f} MB")

opts = client.vde.get_optimizations("products", include_completed=True, completed_limit=5)
print(f"Ongoing: {len(opts.ongoing)}, Completed: {len(opts.completed)}")
```

### Maintenance

```python
# Flush pending writes to storage
client.vde.flush(name, *, timeout=None) -> bool

# Trigger index rebuild
client.vde.rebuild_index(name, *, timeout=None) -> bool

# Trigger optimization (merge segments, etc.)
client.vde.optimize(name, *, timeout=None) -> bool
```

**Example:**

```python
# After bulk ingestion:
client.vde.flush("products")
client.vde.rebuild_index("products")
client.vde.optimize("products")
```

### Rebuild Management

Advanced rebuild with full configuration and task tracking.

#### `trigger_rebuild()`

```python
task_id, stats = client.vde.trigger_rebuild(
    name,
    *,
    source=None,                 # RebuildDataSourceConfig
    target=None,                 # RebuildTargetConfig
    run_config=None,             # RebuildRunConfig
    wait=None,                   # bool — wait for completion
    wait_timeout=None,           # int — seconds
    priority=None,               # int
    timeout=None,
) -> tuple[str, RebuildStats | None]
```

Returns `(task_id, stats)`. `stats` is populated only when `wait=True`.

**Example:**

```python
from actian_vectorai import RebuildTargetConfig, RebuildRunConfig

task_id, stats = client.vde.trigger_rebuild(
    "products",
    target=RebuildTargetConfig(index_type="TARGET_HNSW"),
    run_config=RebuildRunConfig(batch_size=1000, verify_after_rebuild=True),
    wait=True,
    wait_timeout=300,
)
print(f"Task: {task_id}")
if stats:
    print(f"Processed: {stats.processed_vectors}/{stats.total_vectors}")
```

**Example — monitor rebuild task:**

```python
task_id, _ = client.vde.trigger_rebuild("products")

# Poll task status
info = client.vde.get_rebuild_task(task_id)
print(f"State: {info.state}, Phase: {info.current_phase}")

# List all tasks
tasks, total = client.vde.list_rebuild_tasks(collection_name="products")
print(f"Total tasks: {total}")

# Cancel if needed
client.vde.cancel_rebuild_task(task_id)
```

#### `get_rebuild_task()`

```python
info = client.vde.get_rebuild_task(task_id, *, timeout=None) -> RebuildTaskInfo
```

#### `list_rebuild_tasks()`

```python
tasks, total = client.vde.list_rebuild_tasks(
    *,
    collection_name=None,
    state=None,                  # RebuildTaskState
    limit=None,
    offset=None,
    timeout=None,
) -> tuple[list[RebuildTaskInfo], int]
```

#### `cancel_rebuild_task()`

```python
client.vde.cancel_rebuild_task(task_id, *, timeout=None) -> bool
```

### Advanced Operations

#### `compact_collection()`

Compact a collection — merge segments, purge deleted vectors.

```python
task_id, stats = client.vde.compact_collection(
    name,
    *,
    options=None,                # CompactOptions
    wait=None,
    wait_timeout=None,
    timeout=None,
) -> tuple[str, CompactStats | None]
```

`CompactOptions` fields: `target_segment_count`, `force_merge_all`, `purge_deleted`, `rebuild_index`.

`CompactStats` fields: `segments_before`, `segments_after`, `vectors_removed`, `bytes_reclaimed`, `duration_seconds`.

**Example:**

```python
from actian_vectorai import CompactOptions

task_id, stats = client.vde.compact_collection(
    "products",
    options=CompactOptions(purge_deleted=True, force_merge_all=True),
    wait=True,
)
if stats:
    print(f"Reclaimed: {stats.bytes_reclaimed / 1024 / 1024:.1f} MB")
    print(f"Segments: {stats.segments_before} → {stats.segments_after}")
```

---

## 7. Filter DSL

The Filter DSL provides a Pythonic way to build metadata filters for search,
query, count, delete, and other filtered operations.

### Imports

```python
from actian_vectorai import (
    Field,
    FilterBuilder,
    has_id,
    has_vector,
    is_empty,
    is_null,
    nested,
)
```

### Field Conditions

`Field(key)` creates a field reference. Call methods on it to produce conditions.

#### Equality & Match

```python
Field("category").eq("electronics")       # exact match (keyword)
Field("count").eq(42)                      # exact match (integer)
Field("active").eq(True)                   # exact match (boolean)
Field("description").text("wireless")      # full-text substring match
```

#### Set Membership

```python
Field("color").any_of(["red", "blue"])     # IN semantics
Field("status").except_of(["deleted"])     # NOT IN semantics
```

#### Numeric Range

```python
Field("price").gt(10.0)                    # >
Field("price").gte(10.0)                   # >=
Field("price").lt(100.0)                   # <
Field("price").lte(100.0)                  # <=
Field("price").between(10.0, 100.0)        # [10, 100] (inclusive by default)
Field("price").between(10.0, 100.0, inclusive=False)  # (10, 100)

# Arbitrary range with any combination of bounds
Field("price").range(gte=10.0, lt=100.0)
```

#### Datetime Range

```python
from datetime import datetime

Field("created").datetime_gt(datetime(2024, 1, 1))
Field("created").datetime_gte(datetime(2024, 1, 1))
Field("created").datetime_lt(datetime(2025, 1, 1))
Field("created").datetime_lte(datetime(2025, 1, 1))
Field("created").datetime_between(
    datetime(2024, 1, 1), datetime(2025, 1, 1)
)
```

#### Values Count (array fields)

```python
Field("tags").values_count(gte=1, lte=5)   # 1-5 tags
```

#### Geo-Spatial

```python
# Bounding box — (lat, lon) tuples
Field("location").geo_bounding_box(
    top_left=(52.52, 13.38),
    bottom_right=(52.50, 13.42),
)

# Radius — lat, lon, radius in meters
Field("location").geo_radius(52.52, 13.405, 1000.0)

# Polygon — list of (lat, lon) vertices
Field("location").geo_polygon([
    (52.52, 13.38), (52.53, 13.42),
    (52.50, 13.40), (52.52, 13.38),
])
```

### FilterBuilder

Combine conditions with boolean logic.

```python
from actian_vectorai import Field, FilterBuilder

f = (
    FilterBuilder()
    .must(Field("category").eq("electronics"))       # AND
    .must(Field("price").lte(100.0))                 # AND
    .must_not(Field("status").eq("discontinued"))    # NOT
    .should(Field("brand").eq("alpha"))              # OR
    .should(Field("brand").eq("beta"))               # OR
    .build()                                         # -> Filter
)

results = client.points.search("products", vector=query, filter=f)
```

#### `min_should()`

At least N of the given conditions must match.

```python
f = (
    FilterBuilder()
    .min_should(
        [Field("tag").eq("sale"), Field("tag").eq("new"), Field("tag").eq("popular")],
        min_count=2,
    )
    .build()
)
```

#### Builder Methods

| Method | Effect |
|--------|--------|
| `must(condition)` | Required condition (AND) |
| `must_not(condition)` | Negated condition (NOT) |
| `should(condition)` | Optional condition (OR) |
| `min_should(conditions, min_count)` | At least N conditions must match |
| `build()` | → `Filter` model |
| `to_proto()` | → protobuf `Filter` message (advanced) |
| `copy()` | Shallow copy of the builder |
| `is_empty()` | `True` if no conditions added |

### Standalone Condition Factories

```python
has_id([1, 2, 3])               # Point ID must be in list
has_vector("text")              # Point must have named vector "text"
is_empty("tags")                # Field "tags" is empty or missing
is_null("optional_field")       # Field is explicitly null
nested("address", inner_filter) # Nested object match
```

### Operator Overloads

Conditions and builders support Python operators for concise expressions:

```python
# AND
cond = Field("a").eq(1) & Field("b").eq(2)

# OR
cond = Field("a").eq(1) | Field("a").eq(2)

# NOT
cond = ~Field("status").eq("deleted")

# Combine builders
b1 = FilterBuilder().must(Field("x").gt(0))
b2 = FilterBuilder().must(Field("y").lt(10))
combined = b1 & b2    # AND
either = b1 | b2      # OR
negated = ~b1          # NOT

f = combined.build()
```

---

## 8. Hybrid Fusion

Client-side fusion functions for combining results from multiple search queries
(e.g., dense + sparse, multi-model, multi-field).

```python
from actian_vectorai import (
    reciprocal_rank_fusion,
    distribution_based_score_fusion,
    ScoredPoint,
)
```

### `reciprocal_rank_fusion()`

Fuse ranked lists using Reciprocal Rank Fusion (RRF).

$$\text{RRF}(d) = \sum_{r} \frac{w_r}{k + \text{rank}_r(d)}$$

```python
fused = reciprocal_rank_fusion(
    responses,                   # Sequence[Sequence[ScoredPoint]]
    limit=10,                    # max results
    *,
    ranking_constant_k=60,       # RRF constant k
    weights=None,                # Sequence[float] — per-list weights
) -> list[ScoredPoint]
```

**Example:**

```python
dense_results = client.points.search("col", vector=dense_query, limit=50)
sparse_results = client.points.search("col", vector=sparse_query, limit=50)

fused = reciprocal_rank_fusion(
    [dense_results, sparse_results],
    limit=10,
    weights=[0.7, 0.3],   # favor dense
)
```

### `distribution_based_score_fusion()`

Normalize scores to [0, 1] using mean ± 3σ, then average across lists.

```python
fused = distribution_based_score_fusion(
    responses,                   # Sequence[Sequence[ScoredPoint]]
    limit=10,
) -> list[ScoredPoint]
```

---

## 9. SmartBatcher

Automatic batching for high-throughput ingestion.

```python
from actian_vectorai import SmartBatcher, BatcherConfig
```

### `BatcherConfig`

```python
@dataclass
class BatcherConfig:
    size_limit: int = 100              # Max items before auto-flush
    byte_limit: int = 4_194_304        # Max batch bytes (4 MB)
    time_limit_ms: int = 100           # Max ms before auto-flush
    max_concurrent_flushes: int = 3    # Concurrent flush operations
```

### `SmartBatcher`

```python
batcher = SmartBatcher(
    flush_callback,              # Callable[[str, list[BatchItem]], Awaitable[None]]
    config=None,                 # BatcherConfig (defaults used if None)
)
```

**Methods:**

| Method | Description |
|--------|-------------|
| `await batcher.start()` | Start background flush worker |
| `await batcher.stop(flush_remaining=True)` | Stop and optionally flush remaining |
| `await batcher.add(collection_name, id, vector, payload=None)` | Add item; returns `Future` |
| `await batcher.flush()` | Manually flush all pending items |
| `await batcher.get_stats()` | Monitoring stats dict (async) |

#### `BatchItem`

Dataclass passed to the flush callback.

| Field | Type | Description |
|-------|------|-------------|
| `collection_name` | `str` | Target collection |
| `id` | `int \| str` | Point ID |
| `vector` | `list[float]` | Point vector |
| `payload` | `dict \| None` | Point payload |
| `future` | `asyncio.Future[None]` | Resolved when the flush completes |
| `estimated_bytes` | `int` | Estimated size for byte-limit batching |

**Example:**

```python
import asyncio
from actian_vectorai import AsyncVectorAIClient, SmartBatcher, BatcherConfig

async def main():
    async with AsyncVectorAIClient("localhost:50051") as client:

        async def flush_fn(collection_name, items):
            from actian_vectorai import PointStruct
            points = [
                PointStruct(id=item.id, vector=item.vector, payload=item.payload)
                for item in items
            ]
            await client.points.upsert(collection_name, points)

        batcher = SmartBatcher(
            flush_fn,
            config=BatcherConfig(size_limit=200, time_limit_ms=50),
        )
        await batcher.start()

        # Add items — they batch automatically
        futures = []
        for i in range(1000):
            fut = await batcher.add("my_col", i, [0.1] * 128, {"idx": i})
            futures.append(fut)

        await batcher.stop()  # flushes remaining
        print(await batcher.get_stats())

asyncio.run(main())
```

---

## 10. Resilience

Client-side resilience primitives for circuit breaking, retry, and backpressure.
These are **not** auto-imported from `actian_vectorai` — use direct imports:

```python
from actian_vectorai.resilience import (
    CircuitBreaker,
    CircuitState,
    RetryConfig,
    BackpressureController,
    BackpressureConfig,
)
```

### CircuitBreaker

Thread-safe circuit breaker that prevents cascading failures.

**State machine:**

```
CLOSED → (failure_threshold reached) → OPEN
OPEN → (recovery_timeout elapsed) → HALF_OPEN
HALF_OPEN → (success_threshold met) → CLOSED
HALF_OPEN → (probe fails) → OPEN
```

**Constructor:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `failure_threshold` | `int` | `5` | Consecutive failures to trip OPEN |
| `recovery_timeout` | `float` | `30.0` | Seconds before HALF_OPEN probe |
| `success_threshold` | `int` | `2` | Consecutive successes in HALF_OPEN to close |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `state` | `CircuitState` | Current state (auto-transitions OPEN → HALF_OPEN on timeout) |
| `failure_count` | `int` | Current consecutive failure count |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `record_success()` | `None` | Record a successful operation |
| `record_failure()` | `None` | Record a failed operation |
| `ensure_closed()` | `None` | Raise `CircuitBreakerOpenError` if OPEN |
| `reset()` | `None` | Force-reset to CLOSED |

**Example:**

```python
from actian_vectorai.resilience import CircuitBreaker, CircuitState

cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0, success_threshold=1)

# Record failures until it trips
for _ in range(3):
    cb.record_failure()
assert cb.state == CircuitState.OPEN

# Check before calling
try:
    cb.ensure_closed()
except Exception:
    print(f"Circuit open, wait for recovery timeout")
```

### `CircuitState` Enum

| Value | Description |
|-------|-------------|
| `CLOSED` | Normal operation — requests pass through |
| `OPEN` | Tripped — requests rejected immediately |
| `HALF_OPEN` | Probing — limited requests allowed to test recovery |

### RetryConfig

Immutable (frozen dataclass) retry policy with exponential backoff.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_retries` | `int` | `3` | Maximum retry attempts |
| `initial_backoff_ms` | `int` | `100` | Initial backoff (ms) |
| `max_backoff_ms` | `int` | `5000` | Maximum backoff cap (ms) |
| `backoff_multiplier` | `float` | `2.0` | Exponential multiplier |
| `jitter_factor` | `float` | `0.25` | Random jitter (0.0–1.0) |
| `retryable_status_codes` | `FrozenSet[grpc.StatusCode]` | `{UNAVAILABLE, RESOURCE_EXHAUSTED, ABORTED}` | gRPC codes to retry |
| `retryable_http_codes` | `FrozenSet[int]` | `{429, 502, 503, 504}` | HTTP codes to retry |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `compute_delay(attempt)` | `float` | Delay in seconds for the given attempt (0-based) |

The delay formula:
$\text{delay} = \min(\text{initial\_backoff\_ms} \times \text{multiplier}^{\text{attempt}},\ \text{max\_backoff\_ms}) + \text{jitter}$

**Example:**

```python
from actian_vectorai.resilience import RetryConfig

config = RetryConfig(max_retries=5, initial_backoff_ms=200, max_backoff_ms=10_000)
for attempt in range(config.max_retries):
    delay = config.compute_delay(attempt)
    print(f"  Attempt {attempt}: delay={delay:.3f}s")
```

### BackpressureConfig

Dataclass for tuning concurrency limits.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_concurrent_requests` | `int` | `64` | Maximum in-flight requests |
| `initial_concurrency` | `int` | `16` | Starting concurrency level |
| `min_concurrency` | `int` | `1` | Minimum concurrency floor |
| `max_concurrency` | `int` | `64` | Maximum concurrency ceiling |

### BackpressureController

Async semaphore-based concurrency controller that adjusts dynamically
based on server backpressure signals (`retry-after`, `x-actian-backpressure` headers).

**Constructor:**

```python
controller = BackpressureController(config=BackpressureConfig(initial_concurrency=8))
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `current_limit` | `int` | Current concurrency limit |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `await acquire()` | `None` | Acquire a concurrency slot (blocks if full) |
| `release()` | `None` | Release a concurrency slot |
| `await process_server_signals(metadata)` | `None` | Adjust limits from response metadata |

**Server signals:**

- `retry-after: <seconds>` — explicit delay, controller sleeps before next request.
- `x-actian-backpressure: <0.0-1.0>` — load factor. Above 0.8 reduces concurrency; below 0.3 increases it.

**Example:**

```python
import asyncio
from actian_vectorai.resilience import BackpressureController, BackpressureConfig

controller = BackpressureController(
    config=BackpressureConfig(initial_concurrency=8, max_concurrency=32)
)
print(f"Current limit: {controller.current_limit}")  # 8

# In request loop:
# await controller.acquire()
# try: ... finally: controller.release()
```

---

## 11. Telemetry / Observability

Optional observability utilities for structured logging, OpenTelemetry tracing,
and metrics. Import from the `telemetry` sub-package:

```python
from actian_vectorai.telemetry import (
    StructuredJsonFormatter,
    configure_structured_logging,
    trace_operation,
    record_request,
    build_user_agent,
)
```

### Structured Logging

JSON log formatter compatible with Datadog, Splunk, ELK, and other log aggregators.

```python
import logging
from actian_vectorai.telemetry import configure_structured_logging

logger = configure_structured_logging(level=logging.DEBUG)
logger.info("Connected", extra={"operation": "connect", "transport": "grpc"})
# Output: {"ts": "2026-03-12T...", "level": "INFO", "logger": "actian_vectorai",
#          "msg": "Connected", "operation": "connect", "transport": "grpc"}
```

`StructuredJsonFormatter` extracts these extra fields when present:
`operation`, `collection`, `duration_ms`, `request_id`, `status`, `transport`.

### OpenTelemetry Integration

**Opt-in** — requires `opentelemetry-api` and `opentelemetry-sdk`.
If OTel packages are not installed, all operations are no-ops (zero overhead).

#### `trace_operation()`

Context manager that creates an OTel span for an SDK operation.

```python
from actian_vectorai.telemetry import trace_operation

with trace_operation("search", collection="products", limit=10) as span:
    results = await client.points.search("products", vector=query)
    span.set_attribute("result_count", len(results))
```

Span attributes: `db.system="actian_vectorai"`, `db.operation=<operation>`, `db.collection=<collection>`, plus any `**kwargs`.

#### `record_request()`

Record request metrics (counter + duration histogram + error counter).

```python
from actian_vectorai.telemetry import record_request

record_request(operation="search", duration_ms=12.5, success=True)
```

Metrics emitted:
- `actian.client.requests` — counter (per operation)
- `actian.client.request.duration_ms` — histogram
- `actian.client.errors` — counter (incremented on `success=False`)

### `build_user_agent()`

Builds an RFC 9110 compliant User-Agent string:

```python
from actian_vectorai.telemetry import build_user_agent

ua = build_user_agent()
# "ActianVectorAI-PythonSDK/0.1.0b2 (Linux x86_64; Python 3.12.3) grpcio/1.78.0"
```

---

## 12. Models Reference

All models are Pydantic `BaseModel` subclasses with `to_proto()` and/or `from_proto()` methods.

### Vector Types

| Class | Fields | Description |
|-------|--------|-------------|
| `DenseVector` | `data: list[float]` | Dense float vector |
| `SparseVector` | `values: list[float]`, `indices: list[int]` | Sparse vector |
| `MultiDenseVector` | `vectors: list[DenseVector]` | Multi-vector (e.g., ColBERT) |

### Point Types

#### `PointStruct`

Input point for upsert operations.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int \| str` | Numeric ID or UUID string |
| `vector` | `list[float] \| DenseVector \| SparseVector \| MultiDenseVector \| dict` | Vector data |
| `payload` | `dict[str, Any] \| None` | Arbitrary JSON metadata |

#### `ScoredPoint`

Returned by search and query.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int \| str` | Point ID |
| `score` | `float` | Similarity/relevance score |
| `payload` | `dict[str, Any] \| None` | Payload (if requested) |
| `vectors` | `Any \| None` | Vectors (if requested) |
| `version` | `int` | Point version |

> **Note:** `vectors` is not included in `repr()`/`print()` output to keep logs readable.
> Access it directly via `r.vectors` after passing `with_vectors=True` to the search call.
>
> ```python
> results = client.points.search("col", vector=query, limit=5, with_vectors=True)
> for r in results:
>     print(r.vectors)   # full vector list
> ```

#### `RetrievedPoint`

Returned by get.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int \| str` | Point ID |
| `payload` | `dict[str, Any] \| None` | Payload |
| `vectors` | `Any \| None` | Vectors |

#### `UpdateResult`

Returned by write operations.

| Field | Type | Description |
|-------|------|-------------|
| `operation_id` | `int \| None` | Server operation ID |
| `status` | `UpdateStatus` | `Acknowledged`, `Completed`, `ClockRejected` |
| `deleted_ids` | `list \| None` | IDs that were confirmed to exist and deleted. Only populated when `track_ids=True` is passed to `delete()` |
| `failed_ids` | `list \| None` | IDs that were not found and could not be deleted. Only populated when `track_ids=True` is passed to `delete()` |

### Groups

| Class | Fields |
|-------|--------|
| `GroupId` | `value: int \| str` |
| `PointGroup` | `id: GroupId`, `hits: list[ScoredPoint]`, `lookup: RetrievedPoint \| None` |
| `GroupsResult` | `groups: list[PointGroup]` |

### Collection Config

#### `VectorParams`

Primary model for defining vector configuration.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `size` | `int` | **required** | Vector dimension |
| `distance` | `Distance` | `Cosine` | Distance metric |
| `hnsw_config` | `HnswConfigDiff \| None` | `None` | Custom HNSW parameters |
| `quantization_config` | `QuantizationConfig \| None` | `None` | Quantization settings |
| `on_disk` | `bool \| None` | `None` | Store vectors on disk |
| `datatype` | `Datatype \| None` | `None` | Vector element type |
| `multivector_config` | `MultiVectorConfig \| None` | `None` | Multi-vector settings |

#### `HnswConfigDiff`

| Field | Type | Description |
|-------|------|-------------|
| `m` | `int \| None` | Max connections per node |
| `ef_construct` | `int \| None` | Construction-time search width |
| `full_scan_threshold` | `int \| None` | Below this count, use brute force |
| `max_indexing_threads` | `int \| None` | Parallel indexing threads |
| `on_disk` | `bool \| None` | Store HNSW graph on disk |
| `payload_m` | `int \| None` | Connections for payload index |
| `inline_storage` | `bool \| None` | Inline small vectors |

#### `WalConfigDiff`

| Field | Type | Description |
|-------|------|-------------|
| `wal_capacity_mb` | `int \| None` | WAL capacity in megabytes |
| `wal_segments_ahead` | `int \| None` | Segments ahead for write buffering |
| `wal_retain_closed` | `int \| None` | Retain closed WAL segments |

#### `OptimizersConfigDiff`

| Field | Type | Description |
|-------|------|-------------|
| `deleted_threshold` | `float \| None` | Ratio of deleted vectors to trigger optimization |
| `vacuum_min_vector_number` | `int \| None` | Minimum vectors before vacuum |
| `default_segment_number` | `int \| None` | Default segment count |
| `max_segment_size` | `int \| None` | Max segment size |
| `memmap_threshold` | `int \| None` | Threshold to switch to mmap |
| `indexing_threshold` | `int \| None` | Threshold to start indexing |
| `flush_interval_sec` | `int \| None` | Auto-flush interval |
| `min_interval_seconds` | `int \| None` | Minimum interval between optimizations (VDE extension) |
| `trigger_type` | `str \| None` | Optimization trigger type (VDE extension) |
| `source_type` | `str \| None` | Optimization source type (VDE extension) |
| `target_type` | `str \| None` | Optimization target type (VDE extension) |
| `pipeline_type` | `str \| None` | Optimization pipeline type (VDE extension) |
| `verifier_enabled` | `bool \| None` | Enable optimization verification (VDE extension) |

#### Quantization

| Class | Key Fields |
|-------|------------|
| `ScalarQuantization` | `type: QuantizationType`, `quantile`, `always_ram` |
| `ProductQuantization` | `compression: CompressionRatio`, `always_ram` |
| `BinaryQuantization` | `always_ram`, `encoding: BinaryQuantizationEncoding` |
| `QuantizationConfig` | `scalar`, `product`, `binary` — one-of wrapper |
| `QuantizationConfigDiff` | Same + `disabled: bool` for updates |

#### Other Collection Models

| Class | Key Fields |
|-------|------------|
| `CollectionInfo` | `status`, `optimizer_status`, `segments_count`, `config`, `payload_schema`, `points_count`, `indexed_vectors_count`, `name_ext` *(Optional[str], VDE extension)*, `vectors_count` *(Optional[int])*, `index_type_ext` *(Optional[IndexType], VDE extension)* |

#### `OptimizerStatus`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ok` | `bool` | `True` | Whether optimizer is healthy |
| `error` | `str` | `""` | Error message (empty if OK) |

#### `PayloadSchemaInfo`

Returned in `CollectionInfo.payload_schema` dict (keyed by field name).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `data_type` | `PayloadSchemaType` | `UnknownType` | Field data type |
| `params` | `PayloadIndexParams \| None` | `None` | Index params (if indexed) |
| `points` | `int \| None` | `None` | Number of points with this field |

| `CollectionConfig` | `params`, `hnsw_config`, `optimizer_config`, `wal_config`, `quantization_config` |
| `CollectionParams` | `shard_number`, `on_disk_payload`, `vectors_config`, `vectors_config_map`, `replication_factor`, `write_consistency_factor`, `read_fan_out_factor`, `sharding_method`, `sparse_vectors_config` |
| `AliasDescription` | `alias_name`, `collection_name` |
| `VectorParamsDiff` | `hnsw_config`, `quantization_config`, `on_disk` — for updates |

### Search & Query Models

#### `SearchParams`

| Field | Type | Description |
|-------|------|-------------|
| `hnsw_ef` | `int \| None` | Search-time ef for HNSW |
| `exact` | `bool \| None` | Force exact (brute-force) search |
| `quantization` | `QuantizationSearchParams \| None` | Quantization search config |
| `indexed_only` | `bool \| None` | Only search indexed segments |
| `acorn` | `AcornSearchParams \| None` | ACORN search parameters |
| `ivf_nprobe` | `int \| None` | IVF nprobe (VDE extension) |
| `extra_params_json` | `str \| None` | Extra JSON params (VDE extension) |

#### `QuantizationSearchParams`

| Field | Type | Description |
|-------|------|-------------|
| `ignore` | `bool \| None` | Skip quantization during search |
| `rescore` | `bool \| None` | Rescore with original vectors |
| `oversampling` | `float \| None` | Oversampling factor for rescoring |

#### `AcornSearchParams`

| Field | Type | Description |
|-------|------|-------------|
| `enable` | `bool \| None` | Enable ACORN filtered HNSW search |
| `max_selectivity` | `float \| None` | Maximum filter selectivity threshold |

#### `PrefetchQuery`

For multi-stage queries with the `query()` endpoint.

| Field | Type | Description |
|-------|------|-------------|
| `prefetch` | `list[PrefetchQuery]` | Nested prefetch (recursive) |
| `using` | `str \| None` | Named vector to use |
| `filter` | `Filter \| None` | Filter for this stage |
| `params` | `SearchParams \| None` | Search parameters |
| `score_threshold` | `float \| None` | Score cutoff |
| `limit` | `int \| None` | Max results from this stage |

#### Selectors

| Class | Fields | Description |
|-------|--------|-------------|
| `WithPayloadSelector` | `enable`, `include: list[str]`, `exclude: list[str]` | Control payload fields returned |
| `WithVectorsSelector` | `enable`, `include: list[str]` | Control vectors returned |
| `OrderBy` | `key: str`, `direction: Direction` | Ordering for scroll |
| `WriteOrdering` | `type: WriteOrderingType` | Write consistency (`Weak`, `Medium`, `Strong`) |
| `ReadConsistency` | `type: ReadConsistencyType`, `factor: int` | Read consistency level |

#### Analytics Models

| Class | Fields |
|-------|--------|
| `FacetValue` | `value: str \| int \| bool` |
| `FacetHit` | `value: FacetValue`, `count: int` |
| `SearchMatrixPair` | `a: int \| str`, `b: int \| str`, `score: float` |
| `CountResult` | `count: int` (used internally; `count()` returns `int` directly) |

### VDE Models

| Class | Key Fields | Description |
|-------|------------|-------------|
| `VdeCollectionConfig` | `index_driver`, `index_algorithm`, `dimension`, `distance_metric`, `config_json` *(str)*, `hnsw_config` | VDE collection parameters |
| `HnswConfig` | `m=16`, `ef_construct=200`, `ef_search=50` | VDE HNSW settings |
| `IvfConfigDiff` | `nlist`, `nprobe`, `training_sample_size` | IVF index parameters |
| `CollectionStats` | `total_vectors`, `indexed_vectors`, `deleted_vectors`, `storage_bytes`, `index_memory_bytes` | Collection statistics |
| `OptimizationsResponse` | `ongoing: list`, `completed: list` | Optimization status |
| `OptimizationProgress` | `name`, `started_at`, `finished_at` *(Optional[str])*, `duration_sec`, `done`, `total`, `children` | Individual optimization |
| `RebuildDataSourceConfig` | `type: RebuildDataSourceType`, `snapshot_path`, `external_uri`, `include_deleted` *(Optional[bool])* | Rebuild source config |
| `RebuildTargetConfig` | `index_type: RebuildTargetIndexType`, `target_collection`, `create_new_collection` | Rebuild target config |
| `RebuildRunConfig` | `batch_size`, `max_catchup_rounds`, `catchup_threshold`, `verify_after_rebuild`, `verify_sample_count`, `overwrite_collection_config` | Rebuild execution config |
| `RebuildStats` | `total_vectors`, `processed_vectors`, `skipped_vectors`, `failed_vectors`, `duration_seconds`, `start_time` *(str)*, `end_time` *(str)* | Rebuild result stats |
| `RebuildTaskInfo` | `task_id`, `collection_name`, `state`, `progress`, `stats`, `error_message`, `created_at` *(str)*, `started_at` *(str)*, `finished_at` *(Optional[str])*, `current_phase` *(str)* | Rebuild task status |
| `CompactOptions` | `target_segment_count`, `force_merge_all`, `purge_deleted`, `rebuild_index` | Compaction config |
| `CompactStats` | `segments_before`, `segments_after`, `vectors_removed`, `bytes_reclaimed`, `duration_seconds` *(float, default=0.0)* | Compaction result |

### Common / Filter Models

| Class | Key Fields |
|-------|------------|
| `GeoPoint` | `lon: float`, `lat: float` |
| `GeoBoundingBox` | `top_left: GeoPoint`, `bottom_right: GeoPoint` |
| `GeoRadius` | `center: GeoPoint`, `radius: float` (meters) |
| `GeoPolygon` | `exterior: GeoLineString`, `interiors: list[GeoLineString]` |
| `GeoLineString` | `points: list[GeoPoint]` |
| `Match` | `keyword`, `integer`, `boolean`, `text`, `keywords`, `integers`, etc. |
| `Range` | `lt`, `gt`, `gte`, `lte` — numeric bounds |
| `DatetimeRange` | `lt`, `gt`, `gte`, `lte` — ISO datetime strings |
| `ValuesCount` | `lt`, `gt`, `gte`, `lte` — array length bounds |
| `FieldCondition` | `key`, `match`, `range`, `geo_bounding_box`, `geo_radius`, `values_count`, etc. |
| `Condition` | `field`, `is_empty`, `has_id`, `filter`, `is_null`, `nested`, `has_vector` |
| `Filter` | `must: list[Condition]`, `must_not: list[Condition]`, `should: list[Condition]`, `min_should: MinShould` |

### Payload Index Params

For advanced field index configuration via `create_field_index()`:

| Class | Key Fields |
|-------|------------|
| `KeywordIndexParams` | `is_tenant`, `on_disk` |
| `IntegerIndexParams` | `lookup`, `range`, `is_principal`, `on_disk` |
| `FloatIndexParams` | `on_disk`, `is_principal` |
| `GeoIndexParams` | `on_disk` |
| `TextIndexParams` | `tokenizer: TokenizerType`, `lowercase`, `min_token_len`, `max_token_len`, `on_disk` |
| `BoolIndexParams` | `on_disk` |
| `DatetimeIndexParams` | `on_disk`, `is_principal` |
| `UuidIndexParams` | `is_tenant`, `on_disk` |
| `PayloadIndexParams` | One-of wrapper for all index param types above |

---

## 13. Enums

All enums are `IntEnum`. Import from `actian_vectorai`:

```python
from actian_vectorai import Distance, FieldType, IndexType, CollectionState
```

### Core Enums

| Enum | Values | Description |
|------|--------|-------------|
| `Distance` | `UnknownDistance=0`, `Cosine=1`, `Euclid=2`, `Dot=3`, `Manhattan=4` | Vector distance metric |
| `FieldType` | `FieldTypeKeyword=0`, `FieldTypeInteger=1`, `FieldTypeFloat=2`, `FieldTypeGeo=3`, `FieldTypeText=4`, `FieldTypeBool=5`, `FieldTypeDatetime=6`, `FieldTypeUuid=7` | Payload field types for indexing |
| `IndexType` | `INDEX_TYPE_AUTO=0`, `INDEX_TYPE_FLAT=1`, `INDEX_TYPE_HNSW=2`, `INDEX_TYPE_IVF_FLAT=3`, `INDEX_TYPE_IVF_PQ=4`, `INDEX_TYPE_IVF_SQ=5` | VDE index algorithms |
| `Datatype` | `Default=0`, `Float32=1`, `Uint8=2`, `Float16=3` | Vector element data type |

### Collection Enums

| Enum | Values |
|------|--------|
| `CollectionStatus` | `UnknownCollectionStatus`, `Green`, `Yellow`, `Red`, `Grey` |
| `CollectionState` | `READY=0`, `REBUILDING=1`, `STATE_ERROR=2` |
| `CollectionHealthStatus` | `HEALTH_UNKNOWN`, `HEALTH_GREEN`, `HEALTH_YELLOW`, `HEALTH_GREY`, `HEALTH_RED` |
| `ShardingMethod` | `Auto=0`, `Custom=1` |

### Write & Read

| Enum | Values |
|------|--------|
| `WriteOrderingType` | `Weak=0`, `Medium=1`, `Strong=2` |
| `ReadConsistencyType` | `All=0`, `Majority=1`, `Quorum=2` |
| `UpdateStatus` | `UnknownUpdateStatus`, `Acknowledged`, `Completed`, `ClockRejected` |

### Search & Query

| Enum | Values |
|------|--------|
| `RecommendStrategy` | `AverageVector=0`, `BestScore=1`, `SumScores=2` |
| `Fusion` | `RRF=0`, `DBSF=1` |
| `Sample` | `Random=0` |
| `Direction` | `Asc=0`, `Desc=1` |

### Quantization

| Enum | Values |
|------|--------|
| `QuantizationType` | `UnknownQuantization=0`, `Int8=1` |
| `CompressionRatio` | `x4`, `x8`, `x16`, `x32`, `x64` |
| `BinaryQuantizationEncoding` | `OneBit`, `TwoBits`, `OneAndHalfBits` |

### Text

| Enum | Values |
|------|--------|
| `TokenizerType` | `Unknown`, `Prefix`, `Whitespace`, `Word`, `Multilingual` |
| `PayloadSchemaType` | `UnknownType`, `Keyword`, `Integer`, `Float`, `Geo`, `Text`, `Bool`, `Datetime`, `Uuid` |

### VDE Enums

| Enum | Values |
|------|--------|
| `IndexAlgorithm` | `HNSW=0` |
| `IndexDriver` | `FAISS=0` |
| `DistanceMetric` | `COSINE=0`, `EUCLIDEAN=1`, `DOT=2` |
| `VectorType` | `VECTOR_TYPE_DENSE=0`, `VECTOR_TYPE_SPARSE=1`, `VECTOR_TYPE_MULTI_DENSE=2` |
| `RebuildDataSourceType` | `SOURCE_CURRENT_INDEX`, `SOURCE_STORAGE`, `SOURCE_SNAPSHOT`, `SOURCE_EXTERNAL` |
| `RebuildTargetIndexType` | `TARGET_SAME`, `TARGET_HNSW`, `TARGET_FLAT`, `TARGET_IVF`, `TARGET_IVF_PQ` |
| `RebuildTaskState` | `TASK_PENDING`, `TASK_RUNNING`, `TASK_PAUSED`, `TASK_COMPLETED`, `TASK_FAILED`, `TASK_CANCELLED` |

### Replication

| Enum | Values |
|------|--------|
| `ReplicaState` | `Active`, `Dead`, `Partial`, `Initializing`, `Listener`, `PartialSnapshot`, `Recovery`, `Resharding`, `ReshardingScaleDown`, `ActiveRead` |
| `ReshardingDirection` | `Up`, `Down` |
| `ShardTransferMethod` | `StreamRecords`, `Snapshot`, `WalDelta`, `ReshardingStreamRecords` |
| `Modifier` | `Non=0`, `Idf=1` |
| `MultiVectorComparator` | `MaxSim=0` |

---

## 14. Exceptions

All exceptions inherit from `VectorAIError`. Every exception carries a `code` attribute
of type `ErrorCode` — an `IntEnum` whose values mirror standard HTTP status codes.

```python
from actian_vectorai import (
    VectorAIError,
    VectorAIConnectionError,        # aliased from ConnectionError
    VaiConnectionRefusedError,      # aliased from ConnectionRefusedError
    VaiConnectionTimeoutError,      # aliased from ConnectionTimeoutError
    AuthenticationError,
    InvalidCredentialsError,
    PermissionDeniedError,
    ChannelClosedError,
    CollectionNotFoundError,
    CollectionExistsError,
    CollectionNotReadyError,
    PointNotFoundError,
    DimensionMismatchError,
    ValidationError,
    ServerError,
    UnimplementedError,
    TimeoutError,
    RateLimitError,
    BatchError,
    CircuitBreakerOpenError,
    MaxRetriesExceededError,
    ClientClosedError,
    PayloadError,
    PayloadKeyNotFoundError,
    from_grpc_error,
    from_http_error,
    is_retryable,
    get_retry_delay,
)
from actian_vectorai.exceptions import ErrorCode
```

### ErrorCode

`ErrorCode` is an `IntEnum` whose values are standard HTTP status codes. Because it is
an `IntEnum`, both numeric and named comparisons work:

```python
except ValidationError as e:
    e.code == 422                           # True  (numeric)
    e.code == ErrorCode.UNPROCESSABLE_ENTITY  # True  (named)
    isinstance(e.code, int)                 # True
```

Error messages display both: `code=422 (UNPROCESSABLE_ENTITY)`.

| `ErrorCode` name | Value | Meaning |
|---|---|---|
| `BAD_REQUEST` | `400` | Malformed input / invalid argument |
| `UNAUTHORIZED` | `401` | Invalid or missing credentials |
| `FORBIDDEN` | `403` | Insufficient permissions |
| `NOT_FOUND` | `404` | Resource (collection, point) does not exist |
| `REQUEST_TIMEOUT` | `408` | Operation deadline exceeded |
| `CONFLICT` | `409` | Resource already exists |
| `UNPROCESSABLE_ENTITY` | `422` | Semantic validation failure (dimension, field) |
| `TOO_MANY_REQUESTS` | `429` | Rate limit or resource quota exceeded |
| `INTERNAL_SERVER_ERROR` | `500` | Server-side or index error |
| `NOT_IMPLEMENTED` | `501` | Operation not supported by the server |
| `BAD_GATEWAY` | `502` | Upstream/proxy returned an invalid response |
| `SERVICE_UNAVAILABLE` | `503` | Server unreachable / connection refused / closed |
| `GATEWAY_TIMEOUT` | `504` | Connection attempt timed out |

### Exception Hierarchy

```
VectorAIError
├── ConnectionError                         code=SERVICE_UNAVAILABLE (503)
│   ├── ConnectionRefusedError
│   ├── ConnectionTimeoutError              code=GATEWAY_TIMEOUT (504)
│   └── ChannelClosedError
├── AuthenticationError
│   ├── InvalidCredentialsError             code=UNAUTHORIZED (401)
│   └── PermissionDeniedError               code=FORBIDDEN (403)
├── CollectionError
│   ├── CollectionNotFoundError             code=NOT_FOUND (404)
│   ├── CollectionExistsError               code=CONFLICT (409)
│   └── CollectionNotReadyError             code=SERVICE_UNAVAILABLE (503)
├── PointError
│   ├── PointNotFoundError                  code=NOT_FOUND (404)
│   └── DimensionMismatchError              code=UNPROCESSABLE_ENTITY (422)
├── ValidationError                         code=UNPROCESSABLE_ENTITY (422)
├── IndexError                              code=INTERNAL_SERVER_ERROR (500)
├── ServerError                             code=INTERNAL_SERVER_ERROR (500)
│   └── UnimplementedError                  code=NOT_IMPLEMENTED (501)
├── TimeoutError                            code=REQUEST_TIMEOUT (408)
├── RateLimitError                          code=TOO_MANY_REQUESTS (429)
├── BatchError                              (no code — aggregate)
├── CircuitBreakerOpenError                 code=SERVICE_UNAVAILABLE (503)
├── MaxRetriesExceededError                 code=SERVICE_UNAVAILABLE (503)
├── ClientClosedError                       code=SERVICE_UNAVAILABLE (503)
└── PayloadError
    └── PayloadKeyNotFoundError             code=NOT_FOUND (404)
```

> **Note:** `IndexError` shadows the Python built-in. It is **not** re-exported from
> `actian_vectorai`. Import it directly: `from actian_vectorai.exceptions import IndexError`.
> `CollectionError` and `PointError` are intermediate base classes available via
> `from actian_vectorai.exceptions import CollectionError, PointError`.

### Error Details

| Exception | `ErrorCode` | Key Attributes | Raised When |
|-----------|-------------|----------------|-------------|
| `VectorAIError` | — | `message`, `code`, `details`, `operation` | Base class |
| `ConnectionRefusedError` | `SERVICE_UNAVAILABLE` | `address` | Cannot reach server |
| `ConnectionTimeoutError` | `GATEWAY_TIMEOUT` | `address`, `timeout` | Connection timed out |
| `ChannelClosedError` | `SERVICE_UNAVAILABLE` | — | gRPC channel closed unexpectedly |
| `InvalidCredentialsError` | `UNAUTHORIZED` | — | Bad API key / token |
| `PermissionDeniedError` | `FORBIDDEN` | `operation` | Insufficient permissions |
| `CollectionNotFoundError` | `NOT_FOUND` | `collection_name` | Collection doesn't exist |
| `CollectionExistsError` | `CONFLICT` | `collection_name` | Collection already exists |
| `CollectionNotReadyError` | `SERVICE_UNAVAILABLE` | `collection_name` | Collection still loading/rebuilding |
| `PointNotFoundError` | `NOT_FOUND` | `ids`, `collection_name` | Points not found |
| `DimensionMismatchError` | `UNPROCESSABLE_ENTITY` | `expected`, `actual` | Vector dimension wrong |
| `ValidationError` | `UNPROCESSABLE_ENTITY` | `field` | Invalid input parameter |
| `IndexError` | `INTERNAL_SERVER_ERROR` | `collection_name` | Index operation failure |
| `ServerError` | `INTERNAL_SERVER_ERROR` | — | Internal server error |
| `UnimplementedError` | `NOT_IMPLEMENTED` | `operation` | Server RPC not implemented |
| `TimeoutError` | `REQUEST_TIMEOUT` | `timeout` | RPC deadline exceeded |
| `RateLimitError` | `TOO_MANY_REQUESTS` | `retry_after` | Rate limit exceeded |
| `BatchError` | — | `total`, `failed`, `succeeded`, `errors` | Batch upload partial failure |
| `CircuitBreakerOpenError` | `SERVICE_UNAVAILABLE` | `recovery_time`, `failure_count` | Client circuit breaker is OPEN |
| `MaxRetriesExceededError` | `SERVICE_UNAVAILABLE` | `attempts`, `last_error` | All retry attempts exhausted |
| `ClientClosedError` | `SERVICE_UNAVAILABLE` | — | Operation on a closed client |
| `PayloadKeyNotFoundError` | `NOT_FOUND` | `key`, `collection_name` | Payload key doesn't exist |

### Helper Functions

```python
# Convert gRPC error to typed exception
error = from_grpc_error(grpc_error, operation="search")

# Convert HTTP error to typed exception (for REST transport)
error = from_http_error(status_code=404, body={"message": "Not found"}, operation="search")

# Check if error is transient and worth retrying
if is_retryable(error):
    delay = get_retry_delay(error, attempt=2, base_delay=1.0, max_delay=30.0)
    await asyncio.sleep(delay)
```

**`is_retryable()` returns `True` for these `ErrorCode` values:**

| `ErrorCode` | Value | Exception type |
|---|---|---|
| `SERVICE_UNAVAILABLE` | `503` | `ConnectionError` and subtypes |
| `BAD_GATEWAY` | `502` | `ConnectionError` |
| `GATEWAY_TIMEOUT` | `504` | `ConnectionTimeoutError` |
| `TOO_MANY_REQUESTS` | `429` | `RateLimitError` |
| `REQUEST_TIMEOUT` | `408` | `TimeoutError` |

**`get_retry_delay()` uses exponential backoff with jitter:**
$\text{delay} = \min(\text{base} \times 2^{(\text{attempt}-1)} + \text{jitter}, \text{max\_delay})$

If the error is `RateLimitError` with a `retry_after` value, that value is used instead.

### Error Handling Pattern

```python
from actian_vectorai import (
    VectorAIClient,
    VectorAIError,
    CollectionNotFoundError,
    ValidationError,
    UnimplementedError,
    TimeoutError,
    is_retryable,
    get_retry_delay,
)
from actian_vectorai.exceptions import ErrorCode

with VectorAIClient("localhost:50051") as client:
    try:
        results = client.points.search("products", vector=query, limit=10)
    except CollectionNotFoundError as e:
        print(f"Collection '{e.collection_name}' not found")
    except ValidationError as e:
        # Both numeric and named checks work (ErrorCode is IntEnum)
        print(f"Validation error: {e}")            # code=422 (UNPROCESSABLE_ENTITY)
        print(f"Numeric check: {e.code == 422}")   # True
        print(f"Named check:   {e.code == ErrorCode.UNPROCESSABLE_ENTITY}")  # True
    except UnimplementedError as e:
        print(f"Operation '{e.operation}' not supported by server")
    except TimeoutError:
        print("Request timed out — try increasing timeout")
    except VectorAIError as e:
        if is_retryable(e):
            delay = get_retry_delay(e, attempt=1)
            print(f"Transient error ({e.code}), retry after {delay:.1f}s")
        else:
            raise
```

---

## 15. Transport

Advanced transport configuration for gRPC connection pooling, TLS, interceptors, and REST fallback.

```python
from actian_vectorai.transport import (
    ConnectionPool,
    PoolConfig,
    create_ssl_credentials,
    create_credentials_from_files,
    AuthInterceptor,
    RetryInterceptor,
    TracingInterceptor,
    LoggingInterceptor,
    MetadataInterceptor,
    UserAgentInterceptor,
    CircuitBreakerInterceptor,
    RESTTransport,
)
```

### Connection Pool

Connection pooling is enabled by setting `pool_size > 1` on the client.
Multiple gRPC channels are used with round-robin distribution to bypass
the HTTP/2 `MAX_CONCURRENT_STREAMS` limit.

```python
client = VectorAIClient(
    "localhost:50051",
    pool_size=4,                 # 4 gRPC channels, round-robin
)
```

#### `PoolConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pool_size` | `int` | `3` | Number of gRPC channels |
| `keepalive_time_ms` | `int` | `30000` | Interval between keepalive pings (ms) |
| `keepalive_timeout_ms` | `int` | `10000` | Timeout for keepalive response (ms) |
| `max_message_length` | `int` | `104857600` | Max send/receive message size (100 MiB) |
| `enable_retries` | `bool` | `True` | Enable gRPC-level retry policy |
| `connect_timeout` | `float` | `30.0` | Seconds to wait for initial connectivity |

#### `ConnectionPool` Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `await pool.connect()` | `None` | Create all channels (idempotent) |
| `await pool.close()` | `None` | Close all channels (idempotent) |
| `pool.get_channel()` | `grpc.aio.Channel` | Next channel (round-robin, thread-safe) |
| `await pool.wait_for_ready(timeout=None)` | `bool` | Wait for at least one channel READY |
| `await pool.health_check(timeout=5.0)` | `bool` | Probe all channels, update health flags |
| `pool.get_stats()` | `dict` | Pool stats for monitoring |
| `pool.is_connected` | `bool` | Whether pool has open channels |
| `pool.size` | `int` | Number of channels |

**Example — direct pool usage:**

```python
from actian_vectorai.transport import ConnectionPool, PoolConfig

async with ConnectionPool("localhost:50051", config=PoolConfig(pool_size=4)) as pool:
    channel = pool.get_channel()
    stats = pool.get_stats()
    print(stats)
    # {"address": "localhost:50051", "pool_size": 4, "is_connected": True,
    #  "channels": [{"index": 0, "requests": 1, "healthy": True}, ...]}
```

### TLS / SSL

#### File-based credentials (recommended)

```python
client = VectorAIClient(
    "vectorai.example.com:443",
    tls=True,
    tls_ca_cert="/path/to/ca.pem",
    tls_client_cert="/path/to/client.pem",   # mutual TLS
    tls_client_key="/path/to/client-key.pem", # mutual TLS
)
```

#### Programmatic credentials

```python
from actian_vectorai.transport import create_ssl_credentials, create_credentials_from_files

# From PEM bytes
creds = create_ssl_credentials(
    root_certificates=ca_bytes,        # Optional[bytes] — CA cert
    private_key=key_bytes,             # Optional[bytes] — client key (mTLS)
    certificate_chain=cert_bytes,      # Optional[bytes] — client cert (mTLS)
)

# From file paths (convenience)
creds = create_credentials_from_files(
    ca_cert_path="/path/to/ca.pem",
    client_key_path="/path/to/key.pem",
    client_cert_path="/path/to/cert.pem",
)
```

### gRPC Channel Options

Default channel options set by `connect()` in single-channel mode:

| Option | Default | Description |
|--------|---------|-------------|
| `grpc.max_receive_message_length` | `268435456` (256 MiB) | Max inbound message size |
| `grpc.max_send_message_length` | `268435456` (256 MiB) | Max outbound message size |
| `grpc.keepalive_time_ms` | `30000` | Keepalive ping interval |
| `grpc.keepalive_timeout_ms` | `10000` | Keepalive response timeout |
| `grpc.keepalive_permit_without_calls` | `True` | Send pings even without active RPCs |
| `grpc.http2.max_pings_without_data` | `0` | Unlimited pings without data |

Override with `grpc_options`:

```python
client = VectorAIClient(
    "localhost:50051",
    grpc_options=[
        ("grpc.max_receive_message_length", 512 * 1024 * 1024),  # 512 MiB
        ("grpc.keepalive_time_ms", 60_000),
    ],
)
```

### Interceptor Stack

The client automatically builds an interceptor chain during `connect()`.
Interceptors are added in the following order (each is optional based on config):

| Interceptor | Condition | Description |
|-------------|-----------|-------------|
| `AuthInterceptor` | `api_key` is set | Injects `authorization: Bearer <key>` metadata |
| `RetryInterceptor` | `max_retries > 0` | Automatic retry with backoff for transient gRPC errors |
| `TracingInterceptor` | `enable_tracing=True` (default) | Injects `x-request-id` (UUID) and `x-request-timestamp` |
| `LoggingInterceptor` | `enable_logging=True` | Logs RPC method, duration, and status |
| `MetadataInterceptor` | `metadata` dict is non-empty | Injects static key-value metadata into every RPC |
| `UserAgentInterceptor` | Always | Injects `user-agent: actian-vectorai-python/<version>` |
| `CircuitBreakerInterceptor` | `CircuitBreaker` passed to client | Checks breaker state before each call; records success/failure |

### REST Transport

An alternative HTTP/JSON transport for environments where gRPC is unavailable.
RESTTransport uses `httpx` for async HTTP/1.1 communication.

```python
from actian_vectorai.transport import RESTTransport

rest = RESTTransport(
    base_url="http://localhost:50052",  # REST API port
    timeout=30.0,                       # Request timeout (seconds)
    headers={"Authorization": "Bearer <key>"},
    max_connections=10,
    max_keepalive_connections=5,
)
```

#### Supported REST Endpoints

| Method | REST Endpoint | Description |
|--------|--------------|-------------|
| `health_check()` | `GET /healthz` | Server health |
| `collections_list()` | `GET /collections` | List collections |
| `collections_create(name, config)` | `PUT /collections/{name}` | Create collection |
| `collections_get(name)` | `GET /collections/{name}` | Get collection info |
| `collections_delete(name)` | `DELETE /collections/{name}` | Delete collection |
| `collections_exists(name)` | `GET /collections/{name}/exists` | Check existence |
| `collections_update(name, config)` | `PATCH /collections/{name}` | Update collection |
| `points_upsert(name, points)` | `PUT /collections/{name}/points` | Upsert points |
| `points_get(name, ids)` | `POST /collections/{name}/points` | Get points by ID |
| `points_delete(name, selector)` | `POST /collections/{name}/points/delete` | Delete points |
| `points_search(name, params)` | `POST /collections/{name}/points/search` | Vector search |
| `points_query(name, params)` | `POST /collections/{name}/points/query` | Universal query |
| `points_search_batch(name, searches)` | `POST /collections/{name}/points/search/batch` | Batch search |
| `points_query_batch(name, queries)` | `POST /collections/{name}/points/query/batch` | Batch query |
| `points_count(name, params)` | `POST /collections/{name}/points/count` | Count points |
| `points_set_payload(name, params)` | `POST /collections/{name}/points/payload` | Set payload |
| `points_overwrite_payload(name, params)` | `PUT /collections/{name}/points/payload` | Overwrite payload |
| `points_delete_payload(name, params)` | `POST /collections/{name}/points/payload/delete` | Delete payload keys |
| `points_clear_payload(name, params)` | `POST /collections/{name}/points/payload/clear` | Clear all payload |
| `points_update_vectors(name, params)` | `PUT /collections/{name}/points/vectors` | Update vectors |
| `points_create_field_index(name, params)` | `PUT /collections/{name}/index` | Create field index |

**Example — direct REST usage:**

```python
import asyncio
from actian_vectorai.transport import RESTTransport

async def main():
    rest = RESTTransport("http://localhost:50052")
    try:
        health = await rest.health_check()
        print(health)

        names = await rest.collections_list()
        print(names)

        results = await rest.points_search("my_col", {
            "vector": [0.1] * 128,
            "limit": 5,
        })
        print(results)
    finally:
        await rest.close()

asyncio.run(main())
```

---

## Appendix: Method Quick Reference

### Client

| Method | Signature |
|--------|-----------|
| `health_check` | `(*, timeout=None) -> dict` |
| `upload_points` | `(collection_name, points, *, batch_size=256) -> int` |

### Collections (`client.collections`)

| Method | Returns | Brief |
|--------|---------|-------|
| `create` | `bool` | Create collection |
| `get_info` | `CollectionInfo` | Get collection details |
| `list` | `list[str]` | List all collections |
| `delete` | `bool` | Delete collection |
| `exists` | `bool` | Check existence |
| `update` | `bool` | Update parameters |
| `recreate` | `bool` | Drop + create |
| `get_or_create` | `CollectionInfo` | Get or create |

### Points (`client.points`)

| Method | Returns | Brief |
|--------|---------|-------|
| `upsert` | `UpdateResult` | Insert/update points |
| `get` | `list[RetrievedPoint]` | Get by IDs |
| `delete` | `UpdateResult` | Delete by IDs/filter (with optional `strict` mode) |
| `update_vectors` | `UpdateResult` | Update vectors only |
| `set_payload` | `UpdateResult` | Merge payload |
| `overwrite_payload` | `UpdateResult` | Replace payload |
| `delete_payload` | `UpdateResult` | Remove payload keys |
| `clear_payload` | `UpdateResult` | Clear all payload |
| `create_field_index` | `UpdateResult` | Create payload index |
| `search` | `list[ScoredPoint]` | Vector similarity search |
| `search_batch` | `list[list[ScoredPoint]]` | Batch search (max 100) |
| `count` | `int` | Count points |
| `query` | `list[ScoredPoint]` | Universal query |
| `query_batch` | `list[list[ScoredPoint]]` | Batch query (max 100) |
| `upsert_single` | `UpdateResult` | Upsert one point |
| `delete_by_ids` | `UpdateResult` | Delete by ID list |

### VDE (`client.vde`)

| Method | Returns | Brief |
|--------|---------|-------|
| `open_collection` | `bool` | Open for read/write |
| `close_collection` | `bool` | Close and release |
| `save_snapshot` | `bool` | Save snapshot |
| `load_snapshot` | `bool` | Load from snapshot |
| `get_state` | `CollectionState` | Collection state |
| `get_vector_count` | `int` | Total vectors |
| `get_stats` | `CollectionStats` | Detailed statistics |
| `get_optimizations` | `OptimizationsResponse` | Optimization status |
| `flush` | `bool` | Flush to storage |
| `rebuild_index` | `bool` | Simple rebuild |
| `optimize` | `bool` | Trigger optimization |
| `trigger_rebuild` | `(str, RebuildStats \| None)` | Advanced rebuild |
| `get_rebuild_task` | `RebuildTaskInfo` | Rebuild task status |
| `list_rebuild_tasks` | `(list[RebuildTaskInfo], int)` | List rebuild tasks |
| `cancel_rebuild_task` | `bool` | Cancel rebuild |
| `compact_collection` | `(str, CompactStats \| None)` | Compact collection |

### Resilience (`actian_vectorai.resilience`)

| Class / Config | Brief |
|----------------|-------|
| `CircuitBreaker` | Prevents cascading failures with CLOSED → OPEN → HALF-OPEN state machine |
| `CircuitState` | Enum: `CLOSED`, `OPEN`, `HALF_OPEN` |
| `RetryConfig` | Frozen dataclass — exponential backoff with jitter |
| `BackpressureConfig` | Dataclass — adaptive concurrency limits |
| `BackpressureController` | Async semaphore with server-signal adaptation |

### Telemetry (`actian_vectorai.telemetry`)

| Function / Class | Brief |
|-------------------|-------|
| `configure_structured_logging` | Set up JSON-formatted logging |
| `StructuredJsonFormatter` | Custom `logging.Formatter` emitting JSON |
| `trace_operation` | Context manager creating OpenTelemetry spans |
| `record_request` | Record request metrics (histogram + counter) |
| `build_user_agent` | Build RFC 9110 User-Agent string |

---

## Server Availability Status

> **Last verified:** v0.1.0b2 against Actian VectorAI DB v1.0.0 / VDE v1.0.0
>
> Method availability below reflects current live-server validation. Some features
> are implemented in the client SDK but remain server-limited in this build.

### Validation notes (live server)

- `has_id` filtering is validated for both numeric IDs and UUID IDs.
- Named vectors are validated end-to-end.
- Sparse-vector writes and multi-dense writes are still server-limited.
- Dynamic field index creation remains server-side `UNIMPLEMENTED`.

### Collections (`client.collections`)

| Method | Status | Notes |
|--------|--------|-------|
| `create` | ✅ Available | |
| `get_info` | ✅ Available | |
| `list` | ✅ Available | |
| `delete` | ✅ Available | |
| `exists` | ✅ Available | |
| `update` | ✅ Available | |
| `recreate` | ✅ Available | Convenience (delete + create) |
| `get_or_create` | ✅ Available | Convenience (exists + create) |

### Points (`client.points`)

| Method | Status | Notes |
|--------|--------|-------|
| `upsert` | ✅ Available | |
| `upsert_single` | ✅ Available | Convenience wrapper |
| `get` | ✅ Available | |
| `delete` | ✅ Available | Supports `strict` mode |
| `delete_by_ids` | ✅ Available | Convenience wrapper |
| `count` | ✅ Available | |
| `update_vectors` | ✅ Available | |
| `set_payload` | ✅ Available | |
| `overwrite_payload` | ✅ Available | |
| `delete_payload` | ✅ Available | |
| `clear_payload` | ✅ Available | |
| `create_field_index` | ⚠️ Limited | Dynamic creation currently returns `UNIMPLEMENTED`; define payload schema indexes at collection creation time |
| `search` | ✅ Available | Incl. filtered search |
| `search_batch` | ✅ Available | Max 100 per batch |
| `query` | ✅ Available | Nearest-neighbor mode |
| `query_batch` | ✅ Available | Max 100 per batch |

### VDE (`client.vde`)

| Method | Status | Notes |
|--------|--------|-------|
| `open_collection` | ✅ Available | |
| `close_collection` | ✅ Available | |
| `save_snapshot` | ✅ Available | |
| `load_snapshot` | ✅ Available | |
| `get_state` | ✅ Available | |
| `get_vector_count` | ✅ Available | |
| `get_stats` | ✅ Available | |
| `get_optimizations` | ✅ Available | |
| `flush` | ✅ Available | |
| `rebuild_index` | ✅ Available | |
| `optimize` | ✅ Available | |
| `trigger_rebuild` | ✅ Available | |
| `get_rebuild_task` | ✅ Available | |
| `list_rebuild_tasks` | ✅ Available | |
| `cancel_rebuild_task` | ✅ Available | |
| `compact_collection` | ✅ Available | |

### Client-Level

| Method | Status | Notes |
|--------|--------|-------|
| `health_check` | ✅ Available | Returns server info dict |
| `upload_points` | ✅ Available | Auto-batched bulk upload |
| `reciprocal_rank_fusion` | ✅ Available | Client-side fusion |
| `distribution_based_score_fusion` | ✅ Available | Client-side fusion |

### Summary

| Category | Available | Limited | Total |
|----------|-----------|---------|-------|
| Collections | 8 | 0 | 8 |
| Points | 15 | 1 | 16 |
| VDE | 16 | 0 | 16 |
| Client-Level | 4 | 0 | 4 |
| **Total** | **43** | **1** | **44** |

### Current server-side limitations (validated)

| Area | Behavior |
|------|----------|
| Dynamic field index creation | Returns `UNIMPLEMENTED` |
| Sparse vector upserts | Returns validation error (unknown sparse vector name) |
| Multi-dense vector upserts | Returns validation error (expects non-multi-dense type) |

---

## Examples

36 runnable example scripts are provided in [`examples/`](../examples/). See the
[examples README](../examples/README.md) for a full index organized by topic.

| Category | Examples |
|----------|----------|
| Getting Started | 01–02 |
| Collections | 03 |
| Points CRUD | 04, 07, 08, 23, 28, 31 |
| Search & Query | 05, 06, 09, 12, 15, 17, 21, 33 |
| Filters & Indexes | 10, 11, 32 |
| VDE | 16, 26 |
| Vectors | 29, 34 |
| Transport | 13, 19, 20, 22 |
| Resilience & Errors | 14, 18, 27 |
| Batching | 30 |
| Async Patterns | 24 |
| Reference | 25, 35 |
