"""终端交互辅助函数"""
from datetime import datetime


def header(title: str):
    print(f"\n{'═' * 50}")
    print(f"  ☕  {title}")
    print(f"{'═' * 50}")


def section(title: str):
    print(f"\n── {title} ──")


def prompt(label: str, default: str = "") -> str:
    hint = f"（默认：{default}）" if default else ""
    val = input(f"  {label}{hint}：").strip()
    return val if val else default


def prompt_float(label: str, default: float) -> float:
    while True:
        val = input(f"  {label}（默认：{default}）：").strip()
        if not val:
            return default
        try:
            return float(val)
        except ValueError:
            print("  ⚠ 请输入数字")


def prompt_int(label: str, default: int) -> int:
    while True:
        val = input(f"  {label}（默认：{default}）：").strip()
        if not val:
            return default
        try:
            return int(val)
        except ValueError:
            print("  ⚠ 请输入整数")


def prompt_score(label: str, default: float) -> float:
    while True:
        val = input(f"  {label}（1-10，0.5分刻度，默认：{default}）：").strip()
        if not val:
            score = default
        else:
            try:
                score = float(val)
            except ValueError:
                print("  ⚠ 请输入数字")
                continue
        if 1 <= score <= 10:
            return round(score * 2) / 2
        print("  ⚠ 请输入 1 到 10 之间的评分")


def _score_text(value) -> str:
    try:
        score = float(value or 0)
    except (TypeError, ValueError):
        score = 0.0
    return f"{score:g}"


def select_from_list(items: list, label_key: str, title: str = "请选择") -> dict | None:
    if not items:
        print("  （列表为空）")
        return None
    print(f"\n  {title}：")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item.get(label_key, '未知')}")
    while True:
        val = input("  输入序号（0 返回）：").strip()
        try:
            idx = int(val)
            if idx == 0:
                return None
            if 1 <= idx <= len(items):
                return items[idx - 1]
            print("  ⚠ 序号超出范围")
        except ValueError:
            print("  ⚠ 请输入数字")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def date_str() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


def show_bean(bean: dict):
    rw = bean.get("remaining_weight", 0)
    rc = bean.get("remaining_cups", 0)
    tw = bean.get("total_weight", 0)
    tc = bean.get("total_cups", 0)
    price = bean.get("unit_price", 0)
    inv_line = f"{rw}g / {rc}杯  （购入：{tw}g × {tc}杯"
    if price:
        inv_line += f"  单价：{price}元/g"
    inv_line += "）"
    print(f"""
  ┌─ 豆子档案 {'─' * 30}
  │ 名称：{bean.get('name')}
  │ 品牌：{bean.get('roaster')}
  │ 产地：{bean.get('origin')}
  │ 庄园：{bean.get('farm')}
  │ 品种：{bean.get('variety')}
  │ 处理法：{bean.get('process')}  烘焙度：{bean.get('roast_level')}
  │ 批次：{bean.get('roast_date')}  赏味期限：{bean.get('best_before')}
  │ 包装：{bean.get('packaging')}
  │ 剩余库存：{inv_line}
  │ 参考风味：{bean.get('flavor_desc')}
  │ 备注：{bean.get('notes')}
  └{'─' * 40}""")


def show_record(record: dict, bean_name: str = ""):
    ratio = f"1:{record['water_amount']/record['coffee_amount']:.1f}" if record['coffee_amount'] else "无数据"
    overall = _score_text(record.get("overall_score"))
    print(f"""
  ┌─ 冲煮记录 {'─' * 30}
  │ 日期：{record.get('date')}  豆子：{bean_name}
  │ 研磨：{record.get('grinder')} @ {record.get('grind_setting')}
  │ 水温：{record.get('water_temp')}℃  粉水比：{ratio}
  │   ({record.get('coffee_amount')}g 粉 / {record.get('water_amount')}ml 水)
  │ 滤杯：{record.get('dripper')}
  │ 焖蒸：{record.get('bloom_time')}s  总时长：{record.get('total_time')}s
  │ 注水：{record.get('pour_method')}
  ├─ 品饮 {'─' * 33}
  │ 香气：{record.get('aroma')}
  │ 风味：{record.get('flavor')}
  │ 酸度：{record.get('acidity')}  醇厚度：{record.get('body')}
  │ 余韵：{record.get('finish')}
  │ 评分：香气{_score_text(record.get('aroma_score'))} 酸感{_score_text(record.get('acidity_score'))} 甜感{_score_text(record.get('sweetness_score'))}
  │       苦感{_score_text(record.get('bitterness_score'))} 醇厚{_score_text(record.get('body_score'))} 尾韵{_score_text(record.get('finish_score'))}
  │ 总体喜好：{overall}/10
  │ 风味描述：{record.get('flavor')}
  │ 水温调整：{record.get('water_temp_adjustment')}
  │ 研磨度调整：{record.get('grind_adjustment')}
  │ 意见：{record.get('tasting_notes')}
  └{'─' * 40}""")
