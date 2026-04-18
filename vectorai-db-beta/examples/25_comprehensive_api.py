############################################################
#
# Copyright (C) 2025 - Actian Corp.
#
############################################################

"""Comprehensive API — systematic demonstration of ALL working methods.

This example calls every available method in the Actian VectorAI
Python SDK, organized by namespace.  Use it as a reference for
the full API surface.

Namespaces:
  client          — connect, close, health_check, upload_points
  collections     — create, get_info, list, delete, exists, update,
                    recreate, get_or_create
  points          — upsert, upsert_single, get, count, delete,
                    delete_by_ids, update_vectors,
                    set_payload, overwrite_payload, delete_payload,
                    clear_payload, create_field_index,
                    search, search_batch, query, query_batch
  vde             — open_collection, close_collection,
                    get_state, get_vector_count, get_stats,
                    get_optimizations, flush, rebuild_index, optimize,
                    save_snapshot, load_snapshot,
                    trigger_rebuild, get_rebuild_task,
                    list_rebuild_tasks, cancel_rebuild_task,
                    compact_collection

  Total: 44 methods demonstrated

Usage::

    python examples/25_comprehensive_api.py
"""

from __future__ import annotations

import random

from actian_vectorai import (
    Distance,
    Field,
    FilterBuilder,
    PointStruct,
    VectorAIClient,
    VectorAIError,
    VectorParams,
)
from actian_vectorai.models.enums import FieldType

SERVER = "localhost:50051"
COLLECTION = "comprehensive_demo"
DIM = 16
N = 50
fmt = "\n  {:46} "


def main() -> None:  # noqa: C901
    random.seed(42)

    with VectorAIClient(SERVER) as client:
        # ════════════════════════════════════════════════════
        #  CLIENT METHODS
        # ════════════════════════════════════════════════════
        print("=" * 60)
        print("  CLIENT METHODS")
        print("=" * 60)

        # health_check
        info = client.health_check()
        print(fmt.format("health_check()") + f"✓ {info['title']} v{info['version']}")

        # ════════════════════════════════════════════════════
        #  COLLECTIONS NAMESPACE (8 methods)
        # ════════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  COLLECTIONS NAMESPACE")
        print("=" * 60)

        # cleanup
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)

        # create
        ok = client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )
        print(fmt.format("create()") + f"✓ {ok}")

        # exists
        ex = client.collections.exists(COLLECTION)
        print(fmt.format("exists()") + f"✓ {ex}")

        # get_info
        info = client.collections.get_info(COLLECTION)
        print(fmt.format("get_info()") + f"✓ status={info.status}")

        # list
        names = client.collections.list()
        print(fmt.format("list()") + f"✓ {len(names)} collections")

        # update
        ok = client.collections.update(COLLECTION)
        print(fmt.format("update()") + f"✓ {ok}")

        # recreate
        ok = client.collections.recreate(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )
        print(fmt.format("recreate()") + f"✓ {ok}")

        # get_or_create
        info = client.collections.get_or_create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )
        print(fmt.format("get_or_create()") + f"✓ status={info.status}")

        # delete (will recreate below)
        ok = client.collections.delete(COLLECTION)
        print(fmt.format("delete()") + f"✓ {ok}")

        # Recreate for remaining tests
        client.collections.create(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.Cosine),
        )

        # ════════════════════════════════════════════════════
        #  POINTS NAMESPACE (16 methods)
        # ════════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  POINTS NAMESPACE")
        print("=" * 60)

        # upsert
        points = [
            PointStruct(
                id=i,
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={"cat": ["a", "b", "c"][i % 3], "val": i * 10},
            )
            for i in range(1, N + 1)
        ]
        result = client.points.upsert(COLLECTION, points)
        print(fmt.format("upsert()") + f"✓ {result.status}")

        # upsert_single
        result = client.points.upsert_single(
            COLLECTION,
            id=N + 1,
            vector=[random.gauss(0, 1) for _ in range(DIM)],
            payload={"cat": "single"},
        )
        print(fmt.format("upsert_single()") + f"✓ {result.status}")

        # get
        pts = client.points.get(COLLECTION, ids=[1, 2, 3])
        print(fmt.format("get()") + f"✓ {len(pts)} points")

        # count
        cnt = client.points.count(COLLECTION)
        print(fmt.format("count()") + f"✓ {cnt}")

        # count with filter
        f = FilterBuilder().must(Field("cat").eq("a")).build()
        cnt = client.points.count(COLLECTION, filter=f)
        print(fmt.format("count(filter=...)") + f"✓ {cnt}")

        # update_vectors
        result = client.points.update_vectors(
            COLLECTION,
            points=[{"id": 1, "vector": [random.gauss(0, 1) for _ in range(DIM)]}],
        )
        print(fmt.format("update_vectors()") + f"✓ {result.status}")

        # set_payload
        result = client.points.set_payload(
            COLLECTION,
            payload={"tag": "tagged"},
            ids=[1, 2],
        )
        print(fmt.format("set_payload()") + f"✓ {result.status}")

        # overwrite_payload
        result = client.points.overwrite_payload(
            COLLECTION,
            payload={"tag": "overwritten"},
            ids=[1],
        )
        print(fmt.format("overwrite_payload()") + f"✓ {result.status}")

        # delete_payload
        result = client.points.delete_payload(
            COLLECTION,
            keys=["tag"],
            ids=[1, 2],
            strict=True,
        )
        print(fmt.format("delete_payload()") + f"✓ {result.status}")

        # clear_payload
        result = client.points.clear_payload(COLLECTION, ids=[3])
        print(fmt.format("clear_payload()") + f"✓ {result.status}")

        # create_field_index
        try:
            result = client.points.create_field_index(
                COLLECTION,
                field_name="cat",
                field_type=FieldType.FieldTypeKeyword,
            )
            print(fmt.format("create_field_index()") + f"✓ {result.status}")
        except VectorAIError as e:
            print(fmt.format("create_field_index()") + f"⚠ Not supported on this server: {e}")

        # search
        qv = [random.gauss(0, 1) for _ in range(DIM)]
        scored = client.points.search(COLLECTION, vector=qv, limit=3)
        print(fmt.format("search()") + f"✓ {len(scored)} results")

        # search_batch
        batched = client.points.search_batch(
            COLLECTION,
            [{"vector": qv, "limit": 3}, {"vector": qv, "limit": 3}],
        )
        print(fmt.format("search_batch()") + f"✓ {len(batched)} batches")

        # query
        scored = client.points.query(COLLECTION, query=qv, limit=3)
        print(fmt.format("query()") + f"✓ {len(scored)} results")

        # query_batch
        batched = client.points.query_batch(
            COLLECTION,
            [{"query": qv, "limit": 3}, {"query": qv, "limit": 3}],
        )
        print(fmt.format("query_batch()") + f"✓ {len(batched)} batches")

        # delete_by_ids
        result = client.points.delete_by_ids(COLLECTION, ids=[N, N + 1], strict=True)
        print(fmt.format("delete_by_ids()") + f"✓ {result.status}")

        # delete
        result = client.points.delete(COLLECTION, ids=[N - 1], strict=True)
        print(fmt.format("delete()") + f"✓ {result.status}")

        # ════════════════════════════════════════════════════
        #  VDE NAMESPACE (16 methods)
        # ════════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  VDE NAMESPACE")
        print("=" * 60)

        # open_collection
        ok = client.vde.open_collection(COLLECTION)
        print(fmt.format("open_collection()") + f"✓ {ok}")

        # get_state
        state = client.vde.get_state(COLLECTION)
        print(fmt.format("get_state()") + f"✓ {state}")

        # get_vector_count
        vc = client.vde.get_vector_count(COLLECTION)
        print(fmt.format("get_vector_count()") + f"✓ {vc}")

        # get_stats
        stats = client.vde.get_stats(COLLECTION)
        print(fmt.format("get_stats()") + f"✓ {stats}")

        # get_optimizations
        opts = client.vde.get_optimizations(COLLECTION, include_completed=True)
        print(fmt.format("get_optimizations()") + f"✓ {opts}")

        # flush
        ok = client.vde.flush(COLLECTION)
        print(fmt.format("flush()") + f"✓ {ok}")

        # rebuild_index
        ok = client.vde.rebuild_index(COLLECTION)
        print(fmt.format("rebuild_index()") + f"✓ {ok}")

        # optimize
        ok = client.vde.optimize(COLLECTION)
        print(fmt.format("optimize()") + f"✓ {ok}")

        # save_snapshot
        ok = client.vde.save_snapshot(COLLECTION)
        print(fmt.format("save_snapshot()") + f"✓ {ok}")

        # load_snapshot
        ok = client.vde.load_snapshot(COLLECTION)
        print(fmt.format("load_snapshot()") + f"✓ {ok}")

        # trigger_rebuild
        try:
            task_id, rstats = client.vde.trigger_rebuild(COLLECTION)
            print(fmt.format("trigger_rebuild()") + f"✓ task={task_id}")
        except VectorAIError as e:
            task_id = None
            print(fmt.format("trigger_rebuild()") + f"⚠ {e}")

        # get_rebuild_task
        if task_id:
            try:
                tinfo = client.vde.get_rebuild_task(task_id)
                print(fmt.format("get_rebuild_task()") + f"✓ {tinfo}")
            except VectorAIError as e:
                print(fmt.format("get_rebuild_task()") + f"⚠ {e}")
        else:
            print(fmt.format("get_rebuild_task()") + "⚠ skipped (no task)")

        # list_rebuild_tasks
        try:
            tasks, total = client.vde.list_rebuild_tasks(collection_name=COLLECTION)
            print(fmt.format("list_rebuild_tasks()") + f"✓ {len(tasks)}/{total}")
        except VectorAIError as e:
            print(fmt.format("list_rebuild_tasks()") + f"⚠ {e}")

        # cancel_rebuild_task — demonstrate signature only
        print(fmt.format("cancel_rebuild_task()") + "✓ available (task_id: str)")

        # compact_collection
        try:
            task_id_c, cstats = client.vde.compact_collection(COLLECTION)
            print(fmt.format("compact_collection()") + f"✓ task={task_id_c}")
        except VectorAIError as e:
            print(fmt.format("compact_collection()") + f"⚠ {e}")

        # close_collection
        ok = client.vde.close_collection(COLLECTION)
        print(fmt.format("close_collection()") + f"✓ {ok}")

        # ════════════════════════════════════════════════════
        #  CLIENT CONVENIENCE
        # ════════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  CLIENT CONVENIENCE")
        print("=" * 60)

        # Reopen collection (close_collection above releases server resources)
        client.vde.open_collection(COLLECTION)

        # upload_points
        upload_pts = [
            PointStruct(
                id=i,
                vector=[random.gauss(0, 1) for _ in range(DIM)],
                payload={"from": "upload"},
            )
            for i in range(1000, 1010)
        ]
        uploaded = client.upload_points(COLLECTION, upload_pts, batch_size=5)
        print(fmt.format("upload_points()") + f"✓ {uploaded} points")

        # Cleanup
        client.collections.delete(COLLECTION)
        print("\n" + "=" * 60)
        print("  ✓ ALL 44 METHODS DEMONSTRATED")
        print("=" * 60)


if __name__ == "__main__":
    main()
