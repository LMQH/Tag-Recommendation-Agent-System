"""
Milvus 品类向量库（一个 collection 存全量 1/2/3 级）
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

from search_data.config import MILVUS_COLLECTION_CATEGORY, MILVUS_DB_NAME, MILVUS_HOST, MILVUS_PORT


@dataclass(frozen=True)
class CategoryCandidate:
    category_id: int
    category_code: str
    category_name: str
    category_level: int
    parent_code: str
    l1_code: str
    l1_name: str
    l2_code: str
    l2_name: str
    l3_code: str
    l3_name: str
    path_name: str
    vector_score: float
    is_deleted: Optional[int] = None
    is_enabled: Optional[int] = None
    last_modify_ts: Optional[int] = None


class MilvusCategoryStore:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, db_name: Optional[str] = None):
        self.host = host or MILVUS_HOST
        self.port = port or MILVUS_PORT
        self.db_name = db_name or MILVUS_DB_NAME
        self.collection_name = MILVUS_COLLECTION_CATEGORY

        connections.connect(alias="default", host=self.host, port=str(self.port))
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
            return Collection(self.collection_name)
        return self._create_collection(dim=dim)

    def _create_collection(self, dim: int) -> Collection:
        fields = [
            FieldSchema(name="category_id", dtype=DataType.INT64, is_primary=True, auto_id=False),
            FieldSchema(name="category_code", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="category_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="category_level", dtype=DataType.INT8),
            FieldSchema(name="parent_code", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="l1_code", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="l1_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="l2_code", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="l2_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="l3_code", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="l3_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="path_name", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="is_deleted", dtype=DataType.INT8),
            FieldSchema(name="is_enabled", dtype=DataType.INT8),
            FieldSchema(name="last_modify_ts", dtype=DataType.INT64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        schema = CollectionSchema(fields=fields, description="category embedding index")
        c = Collection(name=self.collection_name, schema=schema)

        index_params = {
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 16, "efConstruction": 200},
        }
        c.create_index(field_name="embedding", index_params=index_params)
        c.load()
        return c

    def delete_by_ids(self, ids: Sequence[int]) -> int:
        if not ids:
            return 0
        c = Collection(self.collection_name)
        expr = f"category_id in [{','.join(str(int(i)) for i in ids)}]"
        res = c.delete(expr)
        c.flush()
        return int(getattr(res, "delete_count", len(ids)))

    def upsert(self, rows: Sequence[tuple], dim: int) -> int:
        """
        rows 顺序必须与 insert fields 对齐（除 embedding 外都为标量字段）
        """
        c = self.get_or_create_collection(dim=dim)
        if not rows:
            return 0

        # 拆列插入（pymilvus insert 需要列式数据）
        cols = list(zip(*rows))
        c.insert([list(col) for col in cols])
        c.flush()
        return len(rows)

    def search(self, query_vector: list[float], topk: int = 200, expr: Optional[str] = None) -> list[CategoryCandidate]:
        c = Collection(self.collection_name)
        c.load()
        # HNSW 约束：ef 需要 >= k（topk），否则会报 “ef should be larger than k”
        ef = max(64, int(topk))
        search_params = {"metric_type": "COSINE", "params": {"ef": ef}}
        output_fields = [
            "category_id",
            "category_code",
            "category_name",
            "category_level",
            "parent_code",
            "l1_code",
            "l1_name",
            "l2_code",
            "l2_name",
            "l3_code",
            "l3_name",
            "path_name",
            "is_deleted",
            "is_enabled",
            "last_modify_ts",
        ]
        res = c.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=topk,
            expr=expr,
            output_fields=output_fields,
        )

        out: list[CategoryCandidate] = []
        hits = res[0] if res else []
        for h in hits:
            entity = getattr(h, "entity", None)
            getv = entity.get if entity is not None else h.get  # type: ignore[attr-defined]

            out.append(
                CategoryCandidate(
                    category_id=int(getv("category_id")),
                    category_code=str(getv("category_code") or ""),
                    category_name=str(getv("category_name") or ""),
                    category_level=int(getv("category_level") or 0),
                    parent_code=str(getv("parent_code") or ""),
                    l1_code=str(getv("l1_code") or ""),
                    l1_name=str(getv("l1_name") or ""),
                    l2_code=str(getv("l2_code") or ""),
                    l2_name=str(getv("l2_name") or ""),
                    l3_code=str(getv("l3_code") or ""),
                    l3_name=str(getv("l3_name") or ""),
                    path_name=str(getv("path_name") or ""),
                    vector_score=float(h.score),
                    is_deleted=int(getv("is_deleted")) if getv("is_deleted") is not None else None,
                    is_enabled=int(getv("is_enabled")) if getv("is_enabled") is not None else None,
                    last_modify_ts=int(getv("last_modify_ts")) if getv("last_modify_ts") is not None else None,
                )
            )
        return out

