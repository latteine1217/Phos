"""
快速診斷：檢查校正前後的光譜響應係數

直接運行測試，無需導入模組
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from film_models import get_film_profile
from modules.optical_core import spectral_response
from modules.tone_mapping import apply_reinhard


def test_calibration():
    """測試校正效果"""
    
    print("=" * 80)
    print(" " * 25 + "光譜響應係數校正驗證")
    print("=" * 80)
    print()
    
    # 測試純白輸入
    white_bgr = np.full((100, 100, 3), 255, dtype=np.uint8)
    
    # 測試所有彩色膠片（7個）
    color_films = ["Portra400", "Ektar100", "Velvia50", "NC200", "Cinestill800T", "Gold200", "ProImage100", "Superia400"]
    
    for film_name in color_films:
        print(f"\n{'─' * 80}")
        print(f"膠片: {film_name}")
        print(f"{'─' * 80}")
        
        film = get_film_profile(film_name)
        
        # 獲取光譜響應係數
        r_r, r_g, r_b, g_r, g_g, g_b, b_r, b_g, b_b, t_r, t_g, t_b = film.get_spectral_response()
        
        print("\n光譜響應係數矩陣:")
        print(f"  Red Layer  : r={r_r:.3f}, g={r_g:.3f}, b={r_b:.3f}  (行和 = {r_r+r_g+r_b:.3f})")
        print(f"  Green Layer: r={g_r:.3f}, g={g_g:.3f}, b={g_b:.3f}  (行和 = {g_r+g_g+g_b:.3f})")
        print(f"  Blue Layer : r={b_r:.3f}, g={b_g:.3f}, b={b_b:.3f}  (行和 = {b_r+b_g+b_b:.3f})")
        
        # 計算行和差異
        row_sums = [r_r+r_g+r_b, g_r+g_g+g_b, b_r+b_g+b_b]
        max_row = max(row_sums)
        min_row = min(row_sums)
        row_imbalance = (max_row - min_row) / np.mean(row_sums)
        
        print(f"\n行和不平衡: {row_imbalance:.1%}")
        
        # 測試純白響應
        response_r, response_g, response_b, response_total = spectral_response(white_bgr, film)
        
        print(f"\n純白輸入 (255, 255, 255) 經過光譜響應:")
        print(f"  response_r: {response_r.mean():.6f}")
        print(f"  response_g: {response_g.mean():.6f}")
        print(f"  response_b: {response_b.mean():.6f}")
        
        # 檢查是否平衡
        responses = [response_r.mean(), response_g.mean(), response_b.mean()]
        max_resp = max(responses)
        min_resp = min(responses)
        resp_deviation = max_resp - min_resp
        
        print(f"  偏差: {resp_deviation:.6f} ({resp_deviation/np.mean(responses):.1%})")
        
        if resp_deviation < 0.001:
            print(f"  ✓ 優秀：灰階完全中性")
        elif resp_deviation < 0.01:
            print(f"  ✓ 良好：灰階基本中性")
        else:
            print(f"  ✗ 失敗：存在明顯灰階偏差")
        
        # Tone mapping
        result_r, result_g, result_b, result_total = apply_reinhard(
            response_r, response_g, response_b, response_total, film
        )
        
        print(f"\n經過 Reinhard Tone Mapping:")
        print(f"  result_r: {result_r.mean():.6f}")
        print(f"  result_g: {result_g.mean():.6f}")
        print(f"  result_b: {result_b.mean():.6f}")
        
        # 檢查 tone mapping 後的偏差
        tone_responses = [result_r.mean(), result_g.mean(), result_b.mean()]
        tone_deviation = max(tone_responses) - min(tone_responses)
        
        print(f"  偏差: {tone_deviation:.6f} ({tone_deviation/np.mean(tone_responses):.1%})")
        
        if tone_deviation < 0.001:
            print(f"  ✓ 優秀：Tone mapping 保持灰階中性")
        elif tone_deviation < 0.01:
            print(f"  ✓ 良好：Tone mapping 基本保持中性")
        else:
            print(f"  ⚠ 問題：Tone mapping 引入了偏差")


if __name__ == "__main__":
    test_calibration()
