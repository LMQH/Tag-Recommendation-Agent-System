"""
Milvus 品牌向量库：
- 建 collection
- 批量写入 (id, brand_name, embedding)
- 相似检索 TopK
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from pymilvus import (  # type: ignore[import-untyped]
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from search_data.config import MILVUS_COLLECTION_BRAND, MILVUS_DB_NAME, MILVUS_HOST, MILVUS_PORT


@dataclass(frozen=True)
class BrandCandidate:
    brand_id: int
    brand_name: str
    vector_score: float
    en_name: Optional[str] = None
    is_deleted: Optional[int] = None
    is_enabled: Optional[int] = None
    last_modify_ts: Optional[int] = None


class MilvusBrandStore:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, db_name: Optional[str] = None):
        self.host = host or MILVUS_HOST
        self.port = port or MILVUS_PORT
        self.db_name = db_name or MILVUS_DB_NAME
        self.collection_name = MILVUS_COLLECTION_BRAND

        connections.connect(alias="default", host=self.host, port=str(self.port))
        # Milvus 多数据库（不同版本支持不同）。尽量兼容：
        try:
            from pymilvus import db  # type: ignore

            db.using_database(self.db_name)
        except Exception:
            pass

    def recreate_collection(self, dim: int) -> Collection:
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)
        return self._create_collection(dim=dim)

    def get_or_create_collection(self, dim: int) -> Collection:
        if utility.has_collection(self.collection_name):
            c = Collection(self.collection_name)
            return c
        return self._create_collection(dim=dim)

    def _create_collection(self, dim: int) -> Collection:
        fields = [
            FieldSchema(name="brand_id", dtype=DataType.INT64, is_primary=True, auto_id=False),
            FieldSchema(name="brand_name", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="en_name", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="is_deleted", dtype=DataType.INT8),
            FieldSchema(name="is_enabled", dtype=DataType.INT8),
            # 用 int64 存 unix 时间戳（秒）
            FieldSchema(name="last_modify_ts", dtype=DataType.INT64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        schema = CollectionSchema(fields=fields, description="brand embedding index")
        c = Collection(name=self.collection_name, schema=schema)

        # 建索引（cosine）
        index_params = {
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 16, "efConstruction": 200},
        }
        c.create_index(field_name="embedding", index_params=index_params)
        c.load()
        return c

    def upsert_brands(self, rows: Sequence[tuple[int, str, str, int, int, int, list[float]]], dim: int) -> int:
        """
        Milvus 目前 insert 不是真正 upsert。
        这里策略：
        - 确保 collection 存在
        - 直接 insert（若主键重复会报错）
        你如果需要增量更新，建议用“先 delete 再 insert”或分区重建。
        """
        c = self.get_or_create_collection(dim=dim)
        if not rows:
            return 0

        ids = [int(r[0]) for r in rows]
        names = [str(r[1]) for r in rows]
        en_names = [str(r[2]) for r in rows]
        is_deleted = [int(r[3]) for r in rows]
        is_enabled = [int(r[4]) for r in rows]
        last_modify_ts = [int(r[5]) for r in rows]
        vecs = [r[6] for r in rows]
        c.insert([ids, names, en_names, is_deleted, is_enabled, last_modify_ts, vecs])
        c.flush()
        return len(rows)

    def search(self, query_vector: list[float], topk: int = 50, expr: Optional[str] = None) -> list[BrandCandidate]:
        c = Collection(self.collection_name)
        c.load()
        search_params = {"metric_type": "COSINE", "params": {"ef": 64}}
        res = c.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=topk,
            expr=expr,
            output_fields=["brand_id", "brand_name", "en_name", "is_deleted", "is_enabled", "last_modify_ts"],
        )

        out: list[BrandCandidate] = []
        hits = res[0] if res else []
        for h in hits:
            # h.entity.get("brand_id") 在不同版本可能不同，尽量兼容：
            entity = getattr(h, "entity", None)
            if entity is not None:
                brand_id = int(entity.get("brand_id"))
                brand_name = str(entity.get("brand_name"))
                en_name = entity.get("en_name")
                is_deleted = entity.get("is_deleted")
                is_enabled = entity.get("is_enabled")
                last_modify_ts = entity.get("last_modify_ts")
            else:
                brand_id = int(h.get("brand_id"))
                brand_name = str(h.get("brand_name"))
                en_name = h.get("en_name")
                is_deleted = h.get("is_deleted")
                is_enabled = h.get("is_enabled")
                last_modify_ts = h.get("last_modify_ts")
            out.append(
                BrandCandidate(
                    brand_id=brand_id,
                    brand_name=brand_name,
                    en_name=str(en_name) if en_name is not None else None,
                    vector_score=float(h.score),
                    is_deleted=int(is_deleted) if is_deleted is not None else None,
                    is_enabled=int(is_enabled) if is_enabled is not None else None,
                    last_modify_ts=int(last_modify_ts) if last_modify_ts is not None else None,
                )
            )
        return out
