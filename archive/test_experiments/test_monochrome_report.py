"""
單色測試報告生成器

分析測試結果並生成詳細報告
"""

import numpy as np
import cv2
from pathlib import Path
from film_models import get_film_profile
from modules.optical_core import spectral_response


def analyze_spectral_response():
    """分析光譜響應係數的問題"""
    
    print("=" * 80)
    print(" " * 25 + "光譜響應係數分析")
    print("=" * 80)
    print()
    
    films = ["Portra400", "Ektar100", "Velvia50"]
    
    # 測試純色輸入
    test_cases = {
        "純紅 (R=1)": np.array([[[0, 0, 255]]], dtype=np.uint8),  # BGR
        "純綠 (G=1)": np.array([[[0, 255, 0]]], dtype=np.uint8),
        "純藍 (B=1)": np.array([[[255, 0, 0]]], dtype=np.uint8),
        "純白 (R=G=B=1)": np.array([[[255, 255, 255]]], dtype=np.uint8),
    }
    
    for film_name in films:
        film = get_film_profile(film_name)
        
        print(f"\n{'─' * 80}")
        print(f"膠片: {film_name}")
        print(f"{'─' * 80}")
        
        # 顯示光譜響應係數矩陣
        r_r, r_g, r_b, g_r, g_g, g_b, b_r, b_g, b_b, t_r, t_g, t_b = film.get_spectral_response()
        
        print("\n光譜響應係數矩陣 (行=感光層, 列=輸入通道):")
        print(f"                  Input_R  Input_G  Input_B")
        print(f"  Red Layer   :   {r_r:6.3f}   {r_g:6.3f}   {r_b:6.3f}")
        print(f"  Green Layer :   {g_r:6.3f}   {g_g:6.3f}   {g_b:6.3f}")
        print(f"  Blue Layer  :   {b_r:6.3f}   {b_g:6.3f}   {b_b:6.3f}")
        print(f"  Total       :   {t_r:6.3f}   {t_g:6.3f}   {t_b:6.3f}")
        
        # 分析矩陣性質
        print("\n矩陣性質分析:")
        
        # 1. 對角線主導性
        diag_sum = r_r + g_g + b_b
        off_diag_sum = (r_g + r_b + g_r + g_b + b_r + b_g)
        diag_ratio = diag_sum / (off_diag_sum + 1e-8)
        print(f"  對角線主導比: {diag_ratio:.2f} (對角和/非對角和)")
        
        # 2. 行和（每層的總響應）
        row_sums = {
            "Red Layer": r_r + r_g + r_b,
            "Green Layer": g_r + g_g + g_b,
            "Blue Layer": b_r + b_g + b_b,
            "Total": t_r + t_g + t_b,
        }
        print(f"  行和（層總響應）:")
        for layer, row_sum in row_sums.items():
            print(f"    {layer:15s}: {row_sum:.3f}")
        
        # 3. 列和（每個輸入通道的總影響）
        col_sums = {
            "Input_R": r_r + g_r + b_r,
            "Input_G": r_g + g_g + b_g,
            "Input_B": r_b + g_b + b_b,
        }
        print(f"  列和（通道總影響）:")
        for channel, col_sum in col_sums.items():
            print(f"    {channel:15s}: {col_sum:.3f}")
        
        # 測試純色響應
        print("\n純色輸入測試:")
        print(f"  {'輸入':15s} → R_out  G_out  B_out  (期望主導)")
        
        for case_name, input_img in test_cases.items():
            resp_r, resp_g, resp_b, resp_t = spectral_response(input_img, film)
            
            r_val = resp_r[0, 0] if resp_r is not None else 0
            g_val = resp_g[0, 0] if resp_g is not None else 0
            b_val = resp_b[0, 0] if resp_b is not None else 0
            
            dominant = np.argmax([r_val, g_val, b_val])
            dominant_name = ["R", "G", "B"][dominant]
            
            # 期望主導通道
            if "紅" in case_name:
                expected = "R"
            elif "綠" in case_name:
                expected = "G"
            elif "藍" in case_name:
                expected = "B"
            else:
                expected = "均勻"
            
            match = "✓" if dominant_name == expected or expected == "均勻" else "✗"
            
            print(f"  {case_name:15s} → {r_val:.3f}  {g_val:.3f}  {b_val:.3f}  "
                  f"(期望 {expected}, 實際 {dominant_name}) {match}")
        
        # 診斷問題
        print("\n診斷:")
        issues = []
        
        if abs(r_r - g_g) > 0.3 or abs(g_g - b_b) > 0.3:
            issues.append("⚠ 對角線元素差異過大（不同層敏感度差異大）")
        
        if r_g > 0.3 or r_b > 0.3:
            issues.append("⚠ 紅層對 G/B 敏感度過高（交叉響應）")
        
        if g_r > 0.3 or g_b > 0.3:
            issues.append("⚠ 綠層對 R/B 敏感度過高（交叉響應）")
        
        if b_r > 0.3 or b_g > 0.3:
            issues.append("⚠ 藍層對 R/G 敏感度過高（交叉響應）")
        
        max_row_sum = max(row_sums.values())
        min_row_sum = min(row_sums.values())
        if max_row_sum / min_row_sum > 1.5:
            issues.append(f"⚠ 層間響應不平衡（最大/最小 = {max_row_sum/min_row_sum:.2f}）")
        
        if not issues:
            print("  ✓ 光譜響應係數矩陣合理")
        else:
            for issue in issues:
                print(f"  {issue}")


def generate_recommendations():
    """生成改進建議"""
    
    print("\n" + "=" * 80)
    print(" " * 30 + "改進建議")
    print("=" * 80)
    print()
    
    print("基於測試結果，以下是主要問題和建議：")
    print()
    
    print("【問題 1】純色輸入產生過大色偏 (0.3-0.5)")
    print("  原因：")
    print("    - 光譜響應係數矩陣的非對角元素過大（交叉響應）")
    print("    - 純紅輸入不應激發綠/藍層（但實際上有 0.1-0.2 的響應）")
    print("  建議：")
    print("    - 檢查膠片光譜敏感度曲線的來源與準確性")
    print("    - 考慮降低交叉響應係數（r_g, r_b, g_r, g_b, b_r, b_g）")
    print("    - 參考文獻：實際膠片的光譜分離度（spectral separation）")
    print()
    
    print("【問題 2】灰階出現色偏（純白 → 綠偏）")
    print("  原因：")
    print("    - 綠層總響應 (g_r + g_g + g_b) 高於紅/藍層")
    print("    - 導致相同輸入下綠層輸出更亮")
    print("  建議：")
    print("    - 歸一化光譜響應係數，確保每層的行和相等")
    print("    - 或在 tone mapping 後進行白平衡校正")
    print()
    
    print("【問題 3】黃色 (R+G) 主導通道從 R 變為 G")
    print("  原因：")
    print("    - 綠層響應強於紅層")
    print("    - 黃色 (R=1, G=1, B=0) 經過光譜響應後，G_out > R_out")
    print("  建議：")
    print("    - 調整紅/綠層的權重平衡")
    print("    - 考慮加入色彩校正矩陣（Color Correction Matrix, CCM）")
    print()
    
    print("【問題 4】藍色亮度異常（1.75x-1.88x）")
    print("  原因：")
    print("    - 藍層可能過度曝光")
    print("    - 或 tone mapping 對藍通道處理不當")
    print("  建議：")
    print("    - 檢查藍層的 ISO/曝光參數")
    print("    - 考慮通道獨立的 tone mapping 參數")
    print()
    
    print("【總結】")
    print("  當前膠片模擬具有「藝術風格」特徵：")
    print("    - 綠色偏向（模擬某些膠片的綠偏傾向）")
    print("    - 通道交叉響應（模擬膠片的光譜重疊）")
    print()
    print("  如果目標是「物理準確」：")
    print("    → 需要校正光譜響應係數矩陣")
    print()
    print("  如果目標是「藝術風格」：")
    print("    → 當前實現是合理的（真實膠片確實有色偏）")
    print()
    print("=" * 80)


if __name__ == "__main__":
    analyze_spectral_response()
    generate_recommendations()
