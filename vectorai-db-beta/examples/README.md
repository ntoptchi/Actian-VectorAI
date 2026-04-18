# Actian VectorAI Python Client — Examples

35 self-contained examples covering the full client API surface.
Each file can be run standalone against a local VectorAI DB server (`localhost:50051`).

## Prerequisites

```bash
pip install actian-vectorai
# Start the server:
docker run -d --name vectoraidb -p 50051:50051 -p 50052:50052 actian/vectoraidb:1.0
```

## Example Index

### Getting Started
| # | File | Description |
|---|------|-------------|
| 01 | [01_hello_world.py](01_hello_world.py) | Minimal sync client — connect, create, upsert, search |
| 02 | [02_async_hello_world.py](02_async_hello_world.py) | Async/await version of hello world |

### Collections
| # | File | Description |
|---|------|-------------|
| 03 | [03_collection_management.py](03_collection_management.py) | create, list, get_info, update, delete, exists, recreate, get_or_create |

### Points — CRUD
| # | File | Description |
|---|------|-------------|
| 04 | [04_point_crud.py](04_point_crud.py) | upsert, get, update_vectors, delete |
| 07 | [07_payload_management.py](07_payload_management.py) | set_payload, overwrite_payload, delete_payload, clear_payload |
| 08 | [08_batch_upload.py](08_batch_upload.py) | Bulk ingestion with upload_points() |
| 23 | [23_delete_operations.py](23_delete_operations.py) | Delete by IDs, by filter, strict mode, UUID IDs |
| 28 | [28_uuid_point_ids.py](28_uuid_point_ids.py) | String UUID point identifiers |
| 31 | [31_delete_points.py](31_delete_points.py) | strict=True vs strict=False delete behaviour |

### Search & Query
| # | File | Description |
|---|------|-------------|
| 05 | [05_vector_search.py](05_vector_search.py) | ANN search with various parameters |
| 06 | [06_filtered_search.py](06_filtered_search.py) | Metadata-based filtering with Filter DSL |
| 09 | [09_query_api.py](09_query_api.py) | Universal Query API — query(), query_batch(), PrefetchQuery |
| 12 | [12_search_params.py](12_search_params.py) | SearchParams tuning, WithPayloadSelector, score_threshold, offset |
| 15 | [15_hybrid_fusion.py](15_hybrid_fusion.py) | Dense + sparse hybrid search with fusion |
| 17 | [17_semantic_search.py](17_semantic_search.py) | Simulated embedding search with payload filtering |
| 21 | [21_search_batch.py](21_search_batch.py) | search_batch() and query_batch() parallel multi-query |
| 33 | [33_sparse_vectors.py](33_sparse_vectors.py) | Sparse vector (BM25-style) retrieval |

### Filters & Indexes
| # | File | Description |
|---|------|-------------|
| 10 | [10_field_indexes.py](10_field_indexes.py) | create_field_index with all FieldType variants |
| 11 | [11_advanced_filters.py](11_advanced_filters.py) | Complete Filter DSL — eq, text, range, any_of, is_empty, has_id, boolean combinators |
| 32 | [32_field_indexes.py](32_field_indexes.py) | Field indexes with filtered search verification |

### VDE (Vector Database Engine)
| # | File | Description |
|---|------|-------------|
| 16 | [16_vde_operations.py](16_vde_operations.py) | Lifecycle (open/close), snapshots, stats, flush, rebuild, optimize |
| 26 | [26_advanced_vde.py](26_advanced_vde.py) | trigger_rebuild, get/list/cancel rebuild tasks, compact_collection |

### Vectors
| # | File | Description |
|---|------|-------------|
| 29 | [29_named_vectors.py](29_named_vectors.py) | Multi-vector collections with named vectors |
| 34 | [34_quantization.py](34_quantization.py) | Memory-efficient quantized vector storage |

### Transport & Connectivity
| # | File | Description |
|---|------|-------------|
| 13 | [13_rest_transport.py](13_rest_transport.py) | HTTP/REST transport (standalone, no gRPC) |
| 19 | [19_tls_connection.py](19_tls_connection.py) | Secure gRPC with TLS/SSL |
| 20 | [20_connection_pool.py](20_connection_pool.py) | Multi-channel connection pool for high throughput |
| 22 | [22_interceptors.py](22_interceptors.py) | All 7 interceptor types — Auth, Retry, Tracing, Logging, Metadata, UserAgent, CircuitBreaker |

### Resilience & Error Handling
| # | File | Description |
|---|------|-------------|
| 14 | [14_resilience.py](14_resilience.py) | CircuitBreaker, RetryConfig, BackpressureController |
| 18 | [18_error_handling.py](18_error_handling.py) | Graceful exception management patterns |
| 27 | [27_exception_handling.py](27_exception_handling.py) | Full exception hierarchy, is_retryable, from_grpc_error/from_http_error |

### Batching
| # | File | Description |
|---|------|-------------|
| 30 | [30_smart_batcher.py](30_smart_batcher.py) | SmartBatcher — automatic batching for high-throughput ingestion |

### Async Patterns
| # | File | Description |
|---|------|-------------|
| 24 | [24_async_concurrent.py](24_async_concurrent.py) | Parallel operations with asyncio.gather |

### Reference & Integration
| # | File | Description |
|---|------|-------------|
| 25 | [25_comprehensive_api.py](25_comprehensive_api.py) | ALL 44 API methods demonstrated systematically |
| 35 | [35_rag_integration.py](35_rag_integration.py) | Retrieval-Augmented Generation pattern |

## API Coverage

These examples collectively cover **100%** of the public API:

- **Client**: connect, close, shutdown, health_check, upload_points
- **Collections** (8 methods): create, get_info, list, delete, exists, update, recreate, get_or_create
- **Points** (16 methods): upsert, upsert_single, get, delete, delete_by_ids, update_vectors, set_payload, overwrite_payload, delete_payload, clear_payload, create_field_index, search, search_batch, count, query, query_batch
- **VDE** (16 methods): open_collection, close_collection, save_snapshot, load_snapshot, get_state, get_vector_count, get_stats, get_optimizations, flush, rebuild_index, optimize, trigger_rebuild, get_rebuild_task, list_rebuild_tasks, cancel_rebuild_task, compact_collection
- **Filters**: Field conditions (eq, text, any_of, except_of, range, between, datetime, geo, values_count, is_empty, is_null), FilterBuilder, has_id, operators (&, |, ~)
- **Transport**: RESTTransport, ConnectionPool, TLS/SSL, 7 interceptor types
- **Resilience**: CircuitBreaker, RetryConfig, BackpressureController
- **Batching**: SmartBatcher, BatcherConfig
- **Fusion**: reciprocal_rank_fusion, distribution_based_score_fusion
- **Exceptions**: 18 exception types, from_grpc_error, from_http_error, is_retryable, get_retry_delay
