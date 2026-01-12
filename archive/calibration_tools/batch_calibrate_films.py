"""
批量校正所有膠片的光譜響應係數

讀取 film_models.py 中的所有彩色膠片配置，
應用校正策略，並生成更新後的代碼。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class FilmCoefficients:
    """膠片係數"""
    name: str
    r_r: float
    r_g: float
    r_b: float
    g_r: float
    g_g: float
    g_b: float
    b_r: float
    b_g: float
    b_b: float
    t_r: float
    t_g: float
    t_b: float
    
    def row_sums(self) -> Tuple[float, float, float]:
        """計算RGB層行和"""
        return (
            self.r_r + self.r_g + self.r_b,
            self.g_r + self.g_g + self.g_b,
            self.b_r + self.b_g + self.b_b
        )
    
    def is_balanced(self, tolerance: float = 0.01) -> bool:
        """檢查是否已平衡"""
        row_sums = self.row_sums()
        max_sum = max(row_sums)
        min_sum = min(row_sums)
        return (max_sum - min_sum) < tolerance


def calibrate_coefficients(coef: FilmCoefficients, 
                           normalize: bool = True,
                           enhance_diagonal: float = 0.15,
                           target_sum: float = 1.0) -> FilmCoefficients:
    """
    校正係數（混合策略）
    
    Args:
        coef: 原始係數
        normalize: 是否行歸一化
        enhance_diagonal: 對角線增強強度
        target_sum: 目標行和
    
    Returns:
        校正後的係數
    """
    # 步驟 1: 行歸一化
    r_sum = coef.r_r + coef.r_g + coef.r_b
    g_sum = coef.g_r + coef.g_g + coef.g_b
    b_sum = coef.b_r + coef.b_g + coef.b_b
    
    if normalize:
        r_scale = target_sum / r_sum
        g_scale = target_sum / g_sum
        b_scale = target_sum / b_sum
        
        r_r_new = coef.r_r * r_scale
        r_g_new = coef.r_g * r_scale
        r_b_new = coef.r_b * r_scale
        
        g_r_new = coef.g_r * g_scale
        g_g_new = coef.g_g * g_scale
        g_b_new = coef.g_b * g_scale
        
        b_r_new = coef.b_r * b_scale
        b_g_new = coef.b_g * b_scale
        b_b_new = coef.b_b * b_scale
    else:
        r_r_new, r_g_new, r_b_new = coef.r_r, coef.r_g, coef.r_b
        g_r_new, g_g_new, g_b_new = coef.g_r, coef.g_g, coef.g_b
        b_r_new, b_g_new, b_b_new = coef.b_r, coef.b_g, coef.b_b
    
    # 步驟 2: 增強對角線
    if enhance_diagonal > 0:
        # 紅層
        r_r_enhanced = r_r_new + (target_sum - r_r_new) * enhance_diagonal
        r_off_scale = (target_sum - r_r_enhanced) / (r_g_new + r_b_new + 1e-8)
        r_g_new = r_g_new * r_off_scale
        r_b_new = r_b_new * r_off_scale
        r_r_new = r_r_enhanced
        
        # 綠層
        g_g_enhanced = g_g_new + (target_sum - g_g_new) * enhance_diagonal
        g_off_scale = (target_sum - g_g_enhanced) / (g_r_new + g_b_new + 1e-8)
        g_r_new = g_r_new * g_off_scale
        g_b_new = g_b_new * g_off_scale
        g_g_new = g_g_enhanced
        
        # 藍層
        b_b_enhanced = b_b_new + (target_sum - b_b_new) * enhance_diagonal
        b_off_scale = (target_sum - b_b_enhanced) / (b_r_new + b_g_new + 1e-8)
        b_r_new = b_r_new * b_off_scale
        b_g_new = b_g_new * b_off_scale
        b_b_new = b_b_enhanced
    
    return FilmCoefficients(
        name=coef.name + "_calibrated",
        r_r=r_r_new, r_g=r_g_new, r_b=r_b_new,
        g_r=g_r_new, g_g=g_g_new, g_b=g_b_new,
        b_r=b_r_new, b_g=b_g_new, b_b=b_b_new,
        t_r=coef.t_r, t_g=coef.t_g, t_b=coef.t_b  # Total 層不變
    )


# ==================== 從 film_models.py 提取的係數 ====================

FILM_COEFFICIENTS = {
    # 已校正的膠片（v0.4.2）
    "Portra400": FilmCoefficients(
        name="Portra400", 
        r_r=0.801, r_g=0.079, r_b=0.119,
        g_r=0.045, g_g=0.806, g_b=0.149,
        b_r=0.041, b_g=0.066, b_b=0.893,
        t_r=0.286, t_g=0.408, t_b=0.306
    ),
    "Ektar100": FilmCoefficients(
        name="Ektar100",
        r_r=0.838, r_g=0.065, r_b=0.097,
        g_r=0.038, g_g=0.827, g_b=0.135,
        b_r=0.032, b_g=0.049, b_b=0.919,
        t_r=0.300, t_g=0.380, t_b=0.320
    ),
    "Velvia50": FilmCoefficients(
        name="Velvia50",
        r_r=0.876, r_g=0.041, r_b=0.083,
        g_r=0.023, g_g=0.861, g_b=0.116,
        b_r=0.016, b_g=0.033, b_b=0.951,
        t_r=0.250, t_g=0.400, t_b=0.350
    ),
    
    # 待校正的膠片（從 film_models.py Line 1874-2410 提取）
    "NC200": FilmCoefficients(
        name="NC200",
        r_r=0.77, r_g=0.12, r_b=0.18,
        g_r=0.08, g_g=0.85, g_b=0.23,
        b_r=0.08, b_g=0.09, b_b=0.92,
        t_r=0.25, t_g=0.35, t_b=0.35
    ),
    "FS200": FilmCoefficients(
        name="FS200",
        r_r=0.15, r_g=0.35, r_b=0.45,
        g_r=0.28, g_g=0.60, g_b=0.32,
        b_r=0.32, b_g=0.28, b_b=0.50,
        t_r=0.30, t_g=0.32, t_b=0.35
    ),
    "AS100": FilmCoefficients(
        name="AS100",
        r_r=0.80, r_g=0.12, r_b=0.15,
        g_r=0.06, g_g=0.88, g_b=0.18,
        b_r=0.05, b_g=0.08, b_b=0.95,
        t_r=0.28, t_g=0.40, t_b=0.30
    ),
    "Cinestill800T": FilmCoefficients(
        name="Cinestill800T",
        r_r=0.78, r_g=0.12, r_b=0.20,
        g_r=0.08, g_g=0.82, g_b=0.25,
        b_r=0.06, b_g=0.10, b_b=0.88,
        t_r=0.26, t_g=0.38, t_b=0.32
    ),
    "Gold200": FilmCoefficients(
        name="Gold200",
        r_r=0.80, r_g=0.10, r_b=0.18,
        g_r=0.07, g_g=0.85, g_b=0.22,
        b_r=0.06, b_g=0.09, b_b=0.90,
        t_r=0.27, t_g=0.38, t_b=0.32
    ),
    "TriX400": FilmCoefficients(
        name="TriX400",
        r_r=0.0, r_g=0.0, r_b=0.0,  # 黑白膠片
        g_r=0.0, g_g=0.0, g_b=0.0,
        b_r=0.0, b_g=0.0, b_b=0.0,
        t_r=0.30, t_g=0.35, t_b=0.32
    ),
    "ProImage100": FilmCoefficients(
        name="ProImage100",
        r_r=0.82, r_g=0.09, r_b=0.14,
        g_r=0.05, g_g=0.88, g_b=0.19,
        b_r=0.04, b_g=0.07, b_b=0.92,
        t_r=0.29, t_g=0.39, t_b=0.30
    ),
    "Superia400": FilmCoefficients(
        name="Superia400",
        r_r=0.79, r_g=0.11, r_b=0.17,
        g_r=0.07, g_g=0.84, g_b=0.21,
        b_r=0.05, b_g=0.08, b_b=0.91,
        t_r=0.27, t_g=0.37, t_b=0.33
    ),
    "FP4Plus125": FilmCoefficients(
        name="FP4Plus125",
        r_r=0.0, r_g=0.0, r_b=0.0,  # 黑白膠片
        g_r=0.0, g_g=0.0, g_b=0.0,
        b_r=0.0, b_g=0.0, b_b=0.0,
        t_r=0.26, t_g=0.30, t_b=0.40
    ),
    "HP5Plus400": FilmCoefficients(
        name="HP5Plus400",
        r_r=0.0, r_g=0.0, r_b=0.0,  # 黑白膠片
        g_r=0.0, g_g=0.0, g_b=0.0,
        b_r=0.0, b_g=0.0, b_b=0.0,
        t_r=0.28, t_g=0.32, t_b=0.38
    ),
}


def analyze_and_calibrate_all():
    """分析並校正所有膠片"""
    
    print("=" * 90)
    print(" " * 30 + "批量膠片係數校正")
    print("=" * 90)
    print()
    
    results = {}
    
    for film_name, coef in FILM_COEFFICIENTS.items():
        print(f"\n{'─' * 90}")
        print(f"膠片: {film_name}")
        print(f"{'─' * 90}")
        
        # 檢查是否為黑白膠片
        is_bw = (coef.r_r == 0 and coef.g_g == 0 and coef.b_b == 0)
        
        if is_bw:
            print("  類型: 黑白膠片")
            print("  狀態: ✓ 黑白膠片無需校正RGB層係數")
            results[film_name] = {
                "original": coef,
                "calibrated": coef,
                "needs_calibration": False
            }
            continue
        
        # 檢查是否已校正
        if coef.is_balanced(tolerance=0.01):
            print("  狀態: ✓ 已校正（行和平衡）")
            row_sums = coef.row_sums()
            print(f"  行和: R={row_sums[0]:.3f}, G={row_sums[1]:.3f}, B={row_sums[2]:.3f}")
            results[film_name] = {
                "original": coef,
                "calibrated": coef,
                "needs_calibration": False
            }
            continue
        
        # 需要校正
        print("  狀態: ⚠ 需要校正")
        
        # 顯示原始係數
        row_sums_orig = coef.row_sums()
        print(f"\n  原始係數:")
        print(f"    Red Layer  : r={coef.r_r:.3f}, g={coef.r_g:.3f}, b={coef.r_b:.3f}  (行和={row_sums_orig[0]:.3f})")
        print(f"    Green Layer: r={coef.g_r:.3f}, g={coef.g_g:.3f}, b={coef.g_b:.3f}  (行和={row_sums_orig[1]:.3f})")
        print(f"    Blue Layer : r={coef.b_r:.3f}, g={coef.b_g:.3f}, b={coef.b_b:.3f}  (行和={row_sums_orig[2]:.3f})")
        
        # 計算不平衡度
        max_sum = max(row_sums_orig)
        min_sum = min(row_sums_orig)
        imbalance = (max_sum - min_sum) / np.mean(row_sums_orig)
        print(f"    行和不平衡: {imbalance:.1%}")
        
        # 校正
        calibrated = calibrate_coefficients(coef)
        
        # 顯示校正後係數
        row_sums_cal = calibrated.row_sums()
        print(f"\n  校正後係數:")
        print(f"    Red Layer  : r={calibrated.r_r:.3f}, g={calibrated.r_g:.3f}, b={calibrated.r_b:.3f}  (行和={row_sums_cal[0]:.3f})")
        print(f"    Green Layer: r={calibrated.g_r:.3f}, g={calibrated.g_g:.3f}, b={calibrated.g_b:.3f}  (行和={row_sums_cal[1]:.3f})")
        print(f"    Blue Layer : r={calibrated.b_r:.3f}, g={calibrated.b_g:.3f}, b={calibrated.b_b:.3f}  (行和={row_sums_cal[2]:.3f})")
        
        # 計算改善
        max_sum_cal = max(row_sums_cal)
        min_sum_cal = min(row_sums_cal)
        imbalance_cal = (max_sum_cal - min_sum_cal) / np.mean(row_sums_cal)
        print(f"    行和不平衡: {imbalance_cal:.1%} (改善 {(imbalance - imbalance_cal)*100:.1f}%)")
        
        results[film_name] = {
            "original": coef,
            "calibrated": calibrated,
            "needs_calibration": True
        }
    
    return results


def generate_update_code(results: Dict):
    """生成更新代碼"""
    
    print("\n\n" + "=" * 90)
    print(" " * 30 + "生成更新代碼")
    print("=" * 90)
    print()
    print("將以下代碼應用到 film_models.py 中對應的膠片配置：")
    print()
    
    for film_name, result in results.items():
        if not result["needs_calibration"]:
            continue
        
        cal = result["calibrated"]
        
        print(f"# {film_name} - v0.4.2 校正")
        print(f"red_layer = EmulsionLayer(")
        print(f"    r_response_weight={cal.r_r:.3f}, g_response_weight={cal.r_g:.3f}, b_response_weight={cal.r_b:.3f},")
        print(f"    # ... (其他參數保持不變)")
        print(f")")
        print(f"green_layer = EmulsionLayer(")
        print(f"    r_response_weight={cal.g_r:.3f}, g_response_weight={cal.g_g:.3f}, b_response_weight={cal.g_b:.3f},")
        print(f"    # ...")
        print(f")")
        print(f"blue_layer = EmulsionLayer(")
        print(f"    r_response_weight={cal.b_r:.3f}, g_response_weight={cal.b_g:.3f}, b_response_weight={cal.b_b:.3f},")
        print(f"    # ...")
        print(f")")
        print()


def generate_summary(results: Dict):
    """生成總結"""
    
    print("\n" + "=" * 90)
    print(" " * 35 + "校正總結")
    print("=" * 90)
    print()
    
    calibrated_count = sum(1 for r in results.values() if r["needs_calibration"])
    skipped_count = sum(1 for r in results.values() if not r["needs_calibration"])
    
    print(f"總膠片數: {len(results)}")
    print(f"已校正: {calibrated_count}")
    print(f"無需校正: {skipped_count}")
    print()
    
    if calibrated_count > 0:
        print("需要校正的膠片:")
        for film_name, result in results.items():
            if result["needs_calibration"]:
                orig = result["original"]
                cal = result["calibrated"]
                
                orig_sums = orig.row_sums()
                cal_sums = cal.row_sums()
                
                orig_imb = (max(orig_sums) - min(orig_sums)) / np.mean(orig_sums)
                cal_imb = (max(cal_sums) - min(cal_sums)) / np.mean(cal_sums)
                
                print(f"  ✓ {film_name:20s} - 不平衡度: {orig_imb:5.1%} → {cal_imb:5.1%}")
    
    print("\n" + "=" * 90)


if __name__ == "__main__":
    results = analyze_and_calibrate_all()
    generate_update_code(results)
    generate_summary(results)
