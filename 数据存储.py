"""JSON 数据存储"""
import json
import os
import tempfile
from datetime import datetime
from typing import List, Optional
from 数据模型 import BeanProfile, BrewRecord

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
BEANS_FILE = os.path.join(DATA_DIR, "beans.json")
RECORDS_FILE = os.path.join(DATA_DIR, "records.json")


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load(path: str) -> list:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        backup = path + ".corrupted"
        try:
            os.replace(path, backup)
        except OSError:
            pass
        return []


def _save(path: str, data: list):
    _ensure_dir()
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ── 豆子档案 ──────────────────────────────────────────────────────────────────

def get_all_beans() -> List[dict]:
    return _load(BEANS_FILE)


def get_bean(bean_id: str) -> Optional[dict]:
    return next((b for b in get_all_beans() if b["id"] == bean_id), None)


def save_bean(bean: BeanProfile):
    beans = get_all_beans()
    idx = next((i for i, b in enumerate(beans) if b["id"] == bean.id), None)
    if idx is not None:
        beans[idx] = bean.to_dict()
    else:
        beans.append(bean.to_dict())
    _save(BEANS_FILE, beans)


def delete_bean(bean_id: str) -> bool:
    beans = get_all_beans()
    new_beans = [b for b in beans if b["id"] != bean_id]
    if len(new_beans) == len(beans):
        return False
    _save(BEANS_FILE, new_beans)
    return True


# ── 冲煮记录 ──────────────────────────────────────────────────────────────────

def get_all_records() -> List[dict]:
    return _load(RECORDS_FILE)


def get_records_by_bean(bean_id: str) -> List[dict]:
    return [r for r in get_all_records() if r["bean_id"] == bean_id]


def get_record(record_id: str) -> Optional[dict]:
    return next((r for r in get_all_records() if r["id"] == record_id), None)


def save_record(record: BrewRecord):
    records = get_all_records()
    idx = next((i for i, r in enumerate(records) if r["id"] == record.id), None)
    if idx is not None:
        records[idx] = record.to_dict()
    else:
        records.append(record.to_dict())
    _save(RECORDS_FILE, records)


def delete_record(record_id: str) -> Optional[dict]:
    """删除冲煮记录，返回被删除的记录（用于调用方恢复库存）"""
    records = get_all_records()
    target = next((r for r in records if r["id"] == record_id), None)
    if not target:
        return None
    _save(RECORDS_FILE, [r for r in records if r["id"] != record_id])
    return target


def update_record(record_id: str, data: dict):
    """直接用 dict 更新记录字段（编辑用）"""
    records = get_all_records()
    for r in records:
        if r["id"] == record_id:
            r.update(data)
            break
    _save(RECORDS_FILE, records)


def update_bean(bean_id: str, data: dict):
    """直接用 dict 更新豆子字段（编辑用）"""
    beans = get_all_beans()
    for b in beans:
        if b["id"] == bean_id:
            b.update(data)
            break
    _save(BEANS_FILE, beans)


def _parse_batch_date(batch: dict):
    text = str(batch.get("roast_date") or batch.get("roastedOn") or "").strip()
    normalized = text.replace("/", "-").replace(".", "-")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            pass
    return datetime.max


def _sync_bean_from_batches(bean: dict):
    batches = bean.get("batches") or []
    if not batches:
        return
    bean["remaining_weight"] = round(sum(float(batch.get("remaining_weight", 0.0)) for batch in batches), 1)
    bean["remaining_cups"] = sum(int(batch.get("remaining_cups", 0)) for batch in batches)


def deduct_bean_inventory(bean_id: str, coffee_amount_g: float):
    """冲煮后扣减豆子库存（重量 + 1杯），多批次豆子优先扣最早批次。"""
    beans = get_all_beans()
    for b in beans:
        if b["id"] == bean_id:
            batches = b.get("batches") or []
            if batches:
                left = float(coffee_amount_g or 0.0)
                cup_pending = 1
                for batch in sorted(batches, key=_parse_batch_date):
                    if left <= 0 and cup_pending <= 0:
                        break
                    available = float(batch.get("remaining_weight", 0.0))
                    used = min(available, left)
                    if used > 0:
                        batch["remaining_weight"] = max(0.0, round(available - used, 1))
                        left = round(left - used, 1)
                    if cup_pending > 0 and int(batch.get("remaining_cups", 0)) > 0:
                        batch["remaining_cups"] = max(0, int(batch.get("remaining_cups", 0)) - 1)
                        cup_pending = 0
                _sync_bean_from_batches(b)
            else:
                b["remaining_weight"] = max(0.0, round(b.get("remaining_weight", 0.0) - coffee_amount_g, 1))
                b["remaining_cups"] = max(0, b.get("remaining_cups", 0) - 1)
            break
    _save(BEANS_FILE, beans)


def restore_bean_inventory(bean_id: str, coffee_amount_g: float):
    """删除记录后归还豆子库存"""
    beans = get_all_beans()
    for b in beans:
        if b["id"] == bean_id:
            batches = b.get("batches") or []
            if batches:
                target = next(
                    (
                        batch for batch in sorted(batches, key=_parse_batch_date)
                        if float(batch.get("remaining_weight", 0.0)) < float(batch.get("total_weight", 0.0))
                    ),
                    sorted(batches, key=_parse_batch_date)[0],
                )
                target["remaining_weight"] = round(float(target.get("remaining_weight", 0.0)) + float(coffee_amount_g or 0.0), 1)
                target["remaining_cups"] = int(target.get("remaining_cups", 0)) + 1
                _sync_bean_from_batches(b)
            else:
                b["remaining_weight"] = round(b.get("remaining_weight", 0.0) + coffee_amount_g, 1)
                b["remaining_cups"] = b.get("remaining_cups", 0) + 1
            break
    _save(BEANS_FILE, beans)
