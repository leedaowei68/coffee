"""数据模型定义"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class BeanProfile:
    """咖啡豆档案"""
    id: str
    name: str                       # 豆子名称
    origin: str                     # 产地（国家/产区）
    farm: str = ""                  # 庄园/处理厂
    variety: str = ""               # 品种（如瑰夏、铁皮卡）
    process: str = ""               # 处理法（水洗/日晒/蜜处理等）
    roast_level: str = ""           # 烘焙度（浅/中浅/中/深）
    roaster: str = ""               # 品牌/烘焙商
    roast_date: str = ""            # 批次（通常填烘焙日期）
    best_before: str = ""           # 赏味期限
    packaging: str = ""             # 包装（花袋/花罐/小包）
    unit_price: float = 0.0         # 单价（元/g）
    total_weight: float = 0.0       # 购入总重量（g）
    total_cups: int = 0             # 购入总杯数
    remaining_weight: float = 0.0   # 剩余重量（g）
    remaining_cups: int = 0         # 剩余杯数
    flavor_desc: str = ""           # 风味描述（豆子标注的参考风味）
    notes: str = ""                 # 备注

    def to_dict(self):
        return asdict(self)


@dataclass
class BrewRecord:
    """冲煮记录"""
    id: str
    bean_id: str                 # 对应豆子 ID
    date: str                    # 冲煮日期时间
    # 研磨参数
    grinder: str = "Timemore S3" # 磨豆机型号
    grind_setting: str = "6.5"   # 研磨刻度
    # 水参数
    water_temp: float = 93.0     # 水温（摄氏度）
    water_amount: int = 225      # 用水量（ml）
    coffee_amount: float = 15.0  # 咖啡粉量（g）
    # 器具
    dripper: str = ""            # 滤杯（V60/Kalita/Chemex等）
    # 冲煮参数
    bloom_time: int = 30         # 焖蒸时间（秒）
    total_time: int = 120        # 总冲煮时间（秒）
    pour_method: str = ""        # 注水方式描述
    # 感受
    aroma: str = ""              # 香气描述（旧数据兼容）
    flavor: str = ""             # 风味描述
    acidity: str = ""            # 酸度描述（旧数据兼容）
    body: str = ""               # 醇厚度描述（旧数据兼容）
    finish: str = ""             # 余韵描述（旧数据兼容）
    aroma_score: float = 0.0     # 香气评分（1-10，0.5 分刻度）
    acidity_score: float = 0.0   # 酸感评分（1-10，0.5 分刻度）
    sweetness_score: float = 0.0 # 甜感评分（1-10，0.5 分刻度）
    bitterness_score: float = 0.0# 苦感评分（1-10，0.5 分刻度）
    body_score: float = 0.0      # 醇厚评分（1-10，0.5 分刻度）
    finish_score: float = 0.0    # 尾韵评分（1-10，0.5 分刻度）
    overall_score: float = 0.0   # 总体喜好（1-10，0.5 分刻度）
    water_temp_adjustment: str = "" # 水温调整意见
    grind_adjustment: str = ""   # 研磨度调整意见
    tasting_notes: str = ""      # 意见

    def to_dict(self):
        return asdict(self)

    @property
    def ratio(self) -> str:
        if self.coffee_amount > 0:
            r = self.water_amount / self.coffee_amount
            return f"1:{r:.1f}"
        return "无数据"
