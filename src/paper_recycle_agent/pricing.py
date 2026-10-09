"""回收估价：根据类别与重量估算回收价值。"""

from typing import Dict

from .classifier import classify


def estimate(text: str, weight_kg: float) -> Dict[str, object]:
    """估算指定废纸物品在给定重量下的回收价值。

    weight_kg 为负时按 0 处理。
    """
    result = classify(text)
    if not result["matched"]:
        return {
            **result,
            "weight_kg": weight_kg,
            "estimated_value": 0.0,
        }

    value_per_kg = float(result["value_per_kg"])  # type: ignore
    if not result["recyclable"]:
        return {
            "matched": True,
            "category": result["category"],
            "recyclable": False,
            "weight_kg": weight_kg,
            "estimated_value": 0.0,
            "message": (
                f"【{result['category']}】不可回收，无回收价值。"
                f"{result.get('tips', '')}"
            ),
        }

    value = round(value_per_kg * max(weight_kg, 0.0), 2)
    return {
        "matched": True,
        "category": result["category"],
        "recyclable": True,
        "weight_kg": weight_kg,
        "value_per_kg": value_per_kg,
        "estimated_value": value,
        "message": (
            f"【{result['category']}】{weight_kg} kg，"
            f"预计回收价值约 {value} 元。"
        ),
    }
