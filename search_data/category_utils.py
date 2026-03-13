"""
品类工具：构建层级路径（L1/L2/L3）、生成向量化文本与 rerank doc 文本

基于规则：
- 子.parent_code = 父.category_code
- parent_code 为空表示到顶（一级）
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CategoryRow:
    category_id: int
    category_code: str
    category_name: str
    parent_code: str
    category_level: int
    is_deleted: int
    is_enabled: int
    last_modify_time: Optional[datetime]


@dataclass(frozen=True)
class CategoryPath:
    l1_code: str = ""
    l1_name: str = ""
    l2_code: str = ""
    l2_name: str = ""
    l3_code: str = ""
    l3_name: str = ""
    path_name: str = ""


def _norm_str(v: Optional[str]) -> str:
    return (v or "").strip()


def build_code_index(rows: List[dict]) -> Dict[str, CategoryRow]:
    """
    rows: 从 MySQL 拉出来的 dict 列表
    要求包含：id/category_code/category_name/parent_code/category_level/is_deleted/is_enabled/last_modify_time
    """
    out: Dict[str, CategoryRow] = {}
    for r in rows:
        code = _norm_str(r.get("category_code"))
        if not code:
            continue
        out[code] = CategoryRow(
            category_id=int(r.get("id") or 0),
            category_code=code,
            category_name=_norm_str(r.get("category_name")),
            parent_code=_norm_str(r.get("parent_code")),
            category_level=int(r.get("category_level") or 0),
            is_deleted=int(r.get("is_deleted") or 0),
            is_enabled=int(r.get("is_enabled") or 0),
            last_modify_time=r.get("last_modify_time"),
        )
    return out


def compute_path_for_code(code: str, by_code: Dict[str, CategoryRow]) -> CategoryPath:
    """
    根据 parent_code 链路向上回溯，构造 L1/L2/L3 与 path。
    如果链路不完整，尽量返回已有部分。
    """
    code = _norm_str(code)
    if not code or code not in by_code:
        return CategoryPath()

    chain: List[CategoryRow] = []
    seen: set[str] = set()
    cur = by_code[code]
    # 向上回溯直到 parent_code 为空或找不到父节点
    while True:
        if cur.category_code in seen:
            break
        seen.add(cur.category_code)
        chain.append(cur)
        if not cur.parent_code:
            break
        parent = by_code.get(cur.parent_code)
        if parent is None:
            break
        cur = parent

    # chain 当前是从子到父，反转为从父到子
    chain_rev = list(reversed(chain))
    names = [c.category_name for c in chain_rev if c.category_name]

    l1 = chain_rev[0] if len(chain_rev) >= 1 else None
    l2 = chain_rev[1] if len(chain_rev) >= 2 else None
    l3 = chain_rev[2] if len(chain_rev) >= 3 else None

    return CategoryPath(
        l1_code=l1.category_code if l1 else "",
        l1_name=l1.category_name if l1 else "",
        l2_code=l2.category_code if l2 else "",
        l2_name=l2.category_name if l2 else "",
        l3_code=l3.category_code if l3 else "",
        l3_name=l3.category_name if l3 else "",
        path_name="-".join(names),
    )


def embedding_text(row: CategoryRow, path: CategoryPath) -> str:
    """
    用于向量化的文本：让 L1/L2/L3 与 code 同时参与相似度。
    """
    # path_name 为空时退回 name
    path_name = path.path_name or row.category_name
    return f"PATH={path_name}; CODE={row.category_code}; NAME={row.category_name}"


def rerank_doc(row: CategoryRow, path: CategoryPath) -> str:
    """
    用于 rerank 的结构化 doc（不写优先级，只描述字段语义）。
    """
    return (
        f"L1={path.l1_name}; L2={path.l2_name}; L3={path.l3_name}; "
        f"LEVEL={row.category_level}; CODE={row.category_code}; NAME={row.category_name}"
    )


def unix_ts(dt: Optional[datetime]) -> int:
    if dt is None:
        return 0
    return int(dt.timestamp())

