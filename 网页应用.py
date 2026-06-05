"""Flask Web 看板"""
import os
import sys
import json
from datetime import date, datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from flask import Flask, render_template, request, redirect, url_for
import 数据存储 as storage
from 数据模型 import BrewRecord, BeanProfile
from 终端界面 import now_str, date_str

app = Flask(__name__)
app.secret_key = "coffee-dashboard-key"
app.config["TEMPLATES_AUTO_RELOAD"] = True

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


@app.after_request
def add_no_cache_headers(response):
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def _load_cfg():
    path = os.path.join(DATA_DIR, "config.json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


def _score_value(value, default: float) -> float:
    try:
        score = float(value if value not in (None, "") else default)
    except (TypeError, ValueError):
        score = float(default)
    score = max(1.0, min(10.0, score))
    return round(score * 2) / 2


def _parse_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _parse_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("/", "-").replace(".", "-")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        return None


def _days_label(days):
    if days is None:
        return "—"
    if days < 0:
        return f"已过{abs(days)}天"
    if days == 0:
        return "今天"
    return f"{days}天"


def _bean_form_data(form) -> dict:
    total_weight = _parse_float(form.get("total_weight"))
    total_cups = _parse_int(form.get("total_cups"))
    return {
        "name":             form.get("name", "").strip(),
        "origin":           form.get("origin", "").strip(),
        "farm":             form.get("farm", "").strip(),
        "variety":          form.get("variety", "").strip(),
        "process":          form.get("process", "").strip(),
        "roast_level":      form.get("roast_level", "").strip(),
        "roaster":          form.get("roaster", "").strip(),
        "roast_date":       form.get("roast_date", "").strip(),
        "best_before":      form.get("best_before", "").strip(),
        "packaging":        form.get("packaging", "").strip(),
        "unit_price":       _parse_float(form.get("unit_price")),
        "total_weight":     total_weight,
        "total_cups":       total_cups,
        "remaining_weight": total_weight,
        "remaining_cups":   total_cups,
        "flavor_desc":      form.get("flavor_desc", "").strip(),
        "notes":            form.get("notes", "").strip(),
    }


def _norm_text(value) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _bean_identity_key(bean: dict) -> tuple:
    return tuple(_norm_text(bean.get(field)) for field in (
        "roaster", "origin", "farm", "variety", "process"
    ))


def _same_coffee_identity(a: dict, b: dict) -> bool:
    key_a = _bean_identity_key(a)
    key_b = _bean_identity_key(b)
    if any(key_a) and key_a == key_b:
        return True
    return (
        _norm_text(a.get("name"))
        and _norm_text(a.get("name")) == _norm_text(b.get("name"))
        and _norm_text(a.get("roaster")) == _norm_text(b.get("roaster"))
    )


def _find_finished_bean_to_restock(new_data: dict) -> dict | None:
    for bean in reversed(storage.get_all_beans()):
        if bean.get("remaining_cups", 0) != 0 or bean.get("total_cups", 0) <= 0:
            continue
        if _same_coffee_identity(bean, new_data):
            return bean
    return None


PROCESS_CATEGORY_ORDER = ("直火", "日晒", "蜜处理", "水洗", "其他")
BASIC_NATURAL_PROCESSES = {"日晒", "精致日晒", "定制日晒"}
BASIC_WASHED_PROCESSES = {"水洗", "精致水洗"}


def _process_category(process: str) -> str:
    text = "".join(str(process or "").split())
    if "直火" in text:
        return "直火"
    if text in BASIC_NATURAL_PROCESSES:
        return "日晒"
    if text in BASIC_WASHED_PROCESSES:
        return "水洗"
    if "蜜" in text:
        return "蜜处理"
    return "其他"


def _record_bean_title(bean: dict) -> str:
    if not bean:
        return "未知"
    parts = [
        str(bean.get("origin", "")).strip(),
        str(bean.get("farm", "")).strip(),
        str(bean.get("process", "")).strip(),
    ]
    return " · ".join(part for part in parts if part) or bean.get("name") or "未知"


def _attach_process_categories(beans: list[dict]) -> list[dict]:
    for bean in beans:
        bean["_process_category"] = _process_category(bean.get("process"))
    return beans


def _available_process_categories(beans: list[dict]) -> list[str]:
    present = {bean.get("_process_category") for bean in beans}
    return [category for category in PROCESS_CATEGORY_ORDER if category in present]


# ── 主看板 ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    from collections import defaultdict
    beans   = list(reversed(storage.get_all_beans()))
    records = list(reversed(storage.get_all_records()))
    beans_map = {b["id"]: b for b in beans}
    for r in records:
        r["_bean_name"] = _record_bean_title(beans_map.get(r["bean_id"], {}))

    # 首页只展示库存豆子（排除博物馆豆子）
    stock_beans = [b for b in beans if b.get("remaining_cups", 0) > 0]
    today = date.today()
    dated_stock_beans = []
    for b in stock_beans:
        best_before = _parse_date(b.get("best_before"))
        if not best_before:
            continue
        days = (best_before - today).days
        b["_best_before_sort"] = best_before.toordinal()
        b["_best_before_days"] = days
        b["_best_before_label"] = _days_label(days)
        dated_stock_beans.append(b)
    soon_best_beans = sorted(
        dated_stock_beans,
        key=lambda b: (b.get("_best_before_sort", 10**9), -b.get("remaining_cups", 0), b.get("name", "")),
    )[:5]
    most_remaining_beans = sorted(
        stock_beans,
        key=lambda b: (-b.get("remaining_cups", 0), -b.get("remaining_weight", 0), b.get("name", "")),
    )[:5]
    soon_best_stat = soon_best_beans[0].get("_best_before_label") if soon_best_beans else "—"
    top_remaining_cups = most_remaining_beans[0].get("remaining_cups", 0) if most_remaining_beans else 0
    groups = defaultdict(list)
    for b in stock_beans:
        groups[_process_category(b.get("process"))].append(b)
    bean_groups = [
        {
            "category": category,
            "beans": group,
            "total_count": len(group),
            "total_cups": sum(b.get("remaining_cups", 0) for b in group),
            "total_weight": sum(b.get("remaining_weight", 0) for b in group),
        }
        for category in PROCESS_CATEGORY_ORDER
        for group in [groups.get(category, [])]
    ]
    museum_count = sum(1 for b in beans if b.get("remaining_cups", 0) == 0 and b.get("total_cups", 0) > 0)
    return render_template("index.html", beans=beans, bean_groups=bean_groups, records=records[:4],
                            record_count=len(records),
                            museum_count=museum_count,
                            soon_best_beans=soon_best_beans,
                            most_remaining_beans=most_remaining_beans,
                            soon_best_stat=soon_best_stat,
                            top_remaining_cups=top_remaining_cups)


@app.route("/records")
def record_list():
    beans = storage.get_all_beans()
    records = list(reversed(storage.get_all_records()))
    beans_map = {b["id"]: b for b in beans}
    for r in records:
        r["_bean_name"] = _record_bean_title(beans_map.get(r["bean_id"], {}))
    return render_template("records.html", records=records)


# ── 冲煮记录：新建 ─────────────────────────────────────────────────────────────

@app.route("/record/new", methods=["GET", "POST"])
def new_record():
    beans = _attach_process_categories([b for b in storage.get_all_beans() if b.get("remaining_cups", 0) > 0])
    cfg = _load_cfg()

    if request.method == "POST":
        f = request.form
        bean_id = f.get("bean_id")
        bean = storage.get_bean(bean_id)
        if not bean:
            return redirect(url_for("new_record"))

        record = BrewRecord(
            id=date_str(),
            bean_id=bean_id,
            date=f.get("date") or now_str(),
            grinder=f.get("grinder") or "Timemore S3",
            grind_setting=f.get("grind_setting") or "6.5",
            water_temp=float(f.get("water_temp") or 93),
            water_amount=int(f.get("water_amount") or 225),
            coffee_amount=float(f.get("coffee_amount") or 15),
            dripper=f.get("dripper", ""),
            bloom_time=int(f.get("bloom_time") or 30),
            total_time=int(f.get("total_time") or 120),
            pour_method=f.get("pour_method", ""),
            aroma=f.get("aroma", ""),
            flavor=f.get("flavor", ""),
            acidity=f.get("acidity", ""),
            body=f.get("body", ""),
            finish=f.get("finish", ""),
            aroma_score=_score_value(f.get("aroma_score"), 5),
            acidity_score=_score_value(f.get("acidity_score"), 5),
            sweetness_score=_score_value(f.get("sweetness_score"), 5),
            bitterness_score=_score_value(f.get("bitterness_score"), 5),
            body_score=_score_value(f.get("body_score"), 5),
            finish_score=_score_value(f.get("finish_score"), 5),
            overall_score=_score_value(f.get("overall_score"), 7),
            water_temp_adjustment=f.get("water_temp_adjustment", ""),
            grind_adjustment=f.get("grind_adjustment", ""),
            tasting_notes=f.get("tasting_notes", ""),
        )
        storage.save_record(record)
        storage.deduct_bean_inventory(bean_id, record.coffee_amount)

        return redirect(url_for("record_detail", record_id=record.id))

    return render_template("record_form.html", beans=beans, cfg=cfg, record=None, title="新建冲煮记录",
                           process_categories=_available_process_categories(beans))


# ── 冲煮记录：编辑 ─────────────────────────────────────────────────────────────

@app.route("/record/<record_id>/edit", methods=["GET", "POST"])
def edit_record(record_id):
    record = storage.get_record(record_id)
    if not record:
        return redirect(url_for("index"))
    current_bean_id = record.get("bean_id")
    beans = _attach_process_categories([b for b in storage.get_all_beans()
             if b.get("remaining_cups", 0) > 0 or b["id"] == current_bean_id])
    cfg = _load_cfg()

    if request.method == "POST":
        f = request.form
        old_coffee = record.get("coffee_amount", 0)
        old_bean_id = record.get("bean_id")
        new_coffee = float(f.get("coffee_amount") or old_coffee)
        new_bean_id = f.get("bean_id") or old_bean_id

        updates = {
            "bean_id":      new_bean_id,
            "date":         f.get("date") or record.get("date"),
            "grinder":      f.get("grinder", ""),
            "grind_setting":f.get("grind_setting", ""),
            "water_temp":   float(f.get("water_temp") or 93),
            "water_amount": int(f.get("water_amount") or 225),
            "coffee_amount":new_coffee,
            "dripper":      f.get("dripper", ""),
            "bloom_time":   int(f.get("bloom_time") or 30),
            "total_time":   int(f.get("total_time") or 120),
            "pour_method":  f.get("pour_method", ""),
            "aroma":        f.get("aroma", record.get("aroma", "")),
            "flavor":       f.get("flavor", record.get("flavor", "")),
            "acidity":      f.get("acidity", record.get("acidity", "")),
            "body":         f.get("body", record.get("body", "")),
            "finish":       f.get("finish", record.get("finish", "")),
            "aroma_score":      _score_value(f.get("aroma_score"), record.get("aroma_score", 5)),
            "acidity_score":    _score_value(f.get("acidity_score"), record.get("acidity_score", 5)),
            "sweetness_score":  _score_value(f.get("sweetness_score"), record.get("sweetness_score", 5)),
            "bitterness_score": _score_value(f.get("bitterness_score"), record.get("bitterness_score", 5)),
            "body_score":       _score_value(f.get("body_score"), record.get("body_score", 5)),
            "finish_score":     _score_value(f.get("finish_score"), record.get("finish_score", 5)),
            "overall_score":    _score_value(f.get("overall_score"), record.get("overall_score", 7)),
            "water_temp_adjustment": f.get("water_temp_adjustment", ""),
            "grind_adjustment":      f.get("grind_adjustment", ""),
            "tasting_notes":         f.get("tasting_notes", ""),
        }
        storage.update_record(record_id, updates)

        # 豆子变更时恢复旧豆、扣减新豆
        if old_bean_id != new_bean_id:
            storage.restore_bean_inventory(old_bean_id, old_coffee)
            storage.deduct_bean_inventory(new_bean_id, new_coffee)
        elif abs(new_coffee - old_coffee) > 0.01:
            diff = new_coffee - old_coffee
            if diff > 0:
                storage.deduct_bean_inventory(new_bean_id, diff)
            else:
                storage.restore_bean_inventory(new_bean_id, -diff)

        return redirect(url_for("record_detail", record_id=record_id))

    return render_template("record_form.html", beans=beans, cfg=cfg, record=record, title="编辑冲煮记录",
                           process_categories=_available_process_categories(beans))


# ── 冲煮记录：删除 ─────────────────────────────────────────────────────────────

@app.route("/record/<record_id>/delete", methods=["POST"])
def delete_record(record_id):
    next_url = request.form.get("next", "")
    deleted = storage.delete_record(record_id)
    if deleted:
        storage.restore_bean_inventory(deleted["bean_id"], deleted.get("coffee_amount", 0))
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(url_for("index"))


# ── 冲煮记录：详情 ─────────────────────────────────────────────────────────────

@app.route("/record/<record_id>")
def record_detail(record_id):
    record = storage.get_record(record_id)
    if not record:
        return redirect(url_for("index"))
    bean = storage.get_bean(record["bean_id"]) or {}
    return render_template("record_detail.html", record=record, bean=bean)


# ── 豆子：详情 ────────────────────────────────────────────────────────────────

@app.route("/bean/<bean_id>")
def bean_detail(bean_id):
    bean = storage.get_bean(bean_id)
    if not bean:
        return redirect(url_for("index"))
    records = list(reversed(storage.get_records_by_bean(bean_id)))
    return render_template("bean_detail.html", bean=bean, records=records)


# ── 豆子：新建 ────────────────────────────────────────────────────────────────

@app.route("/bean/new", methods=["GET", "POST"])
def new_bean():
    if request.method == "POST":
        f = request.form
        data = _bean_form_data(f)
        if not data["name"]:
            return render_template("bean_form.html", bean=None, title="新建咖啡豆", error="名称不能为空")

        finished_bean = _find_finished_bean_to_restock(data)
        if finished_bean:
            storage.update_bean(finished_bean["id"], data)
            return redirect(url_for("bean_detail", bean_id=finished_bean["id"]))

        bean = BeanProfile(
            id=f"custom_{date_str()}",
            **data,
        )
        storage.save_bean(bean)
        return redirect(url_for("bean_detail", bean_id=bean.id))

    return render_template("bean_form.html", bean=None, title="新建咖啡豆", error=None)


# ── 豆子：编辑 ────────────────────────────────────────────────────────────────

@app.route("/bean/<bean_id>/edit", methods=["GET", "POST"])
def edit_bean(bean_id):
    bean = storage.get_bean(bean_id)
    if not bean:
        return redirect(url_for("index"))

    if request.method == "POST":
        f = request.form
        updates = {
            "name":             f.get("name", "").strip(),
            "origin":           f.get("origin", "").strip(),
            "farm":             f.get("farm", "").strip(),
            "variety":          f.get("variety", "").strip(),
            "process":          f.get("process", "").strip(),
            "roast_level":      f.get("roast_level", "").strip(),
            "roaster":          f.get("roaster", "").strip(),
            "roast_date":       f.get("roast_date", "").strip(),
            "best_before":      f.get("best_before", "").strip(),
            "packaging":        f.get("packaging", "").strip(),
            "unit_price":       float(f.get("unit_price") or 0),
            "total_weight":     float(f.get("total_weight") or 0),
            "total_cups":       int(f.get("total_cups") or 0),
            "remaining_weight": float(f.get("remaining_weight") or 0),
            "remaining_cups":   int(f.get("remaining_cups") or 0),
            "flavor_desc":      f.get("flavor_desc", "").strip(),
            "notes":            f.get("notes", "").strip(),
        }
        storage.update_bean(bean_id, updates)
        return redirect(url_for("bean_detail", bean_id=bean_id))

    return render_template("bean_form.html", bean=bean, title="编辑咖啡豆", error=None)


# ── 库存豆子 ─────────────────────────────────────────────────────────────────

@app.route("/beans")
def bean_inventory():
    from collections import defaultdict
    all_beans = storage.get_all_beans()
    beans = list(reversed([b for b in all_beans if b.get("remaining_cups", 0) > 0]))
    groups = defaultdict(list)
    for b in beans:
        groups[_process_category(b.get("process"))].append(b)
    bean_groups = [
        {
            "category": category,
            "beans": group,
            "total_count": len(group),
            "total_cups": sum(b.get("remaining_cups", 0) for b in group),
            "total_weight": sum(b.get("remaining_weight", 0) for b in group),
        }
        for category in PROCESS_CATEGORY_ORDER
        for group in [groups.get(category, [])]
    ]
    return render_template("bean_inventory.html", beans=beans, bean_groups=bean_groups)


# ── 咖啡豆博物馆 ──────────────────────────────────────────────────────────────

@app.route("/beans/museum")
def bean_museum():
    all_beans = storage.get_all_beans()
    museum_beans = [b for b in all_beans
                    if b.get("remaining_cups", 0) == 0 and b.get("total_cups", 0) > 0]
    museum_beans = list(reversed(museum_beans))
    return render_template("bean_museum.html", beans=museum_beans)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
