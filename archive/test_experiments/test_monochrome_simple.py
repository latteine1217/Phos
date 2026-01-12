"""
簡化單色測試 - 快速診斷顏色問題

直接測試核心處理流程，輸出詳細診斷資訊
"""

import numpy as np
import cv2
from pathlib import Path

from film_models import get_film_profile
from modules.optical_core import spectral_response
from modules.tone_mapping import apply_reinhard


def test_simple():
    """簡化測試：純白圖像"""
    
    print("=" * 70)
    print("Phos 簡化單色測試")
    print("=" * 70)
    
    # 建立純白圖像 (512x512, BGR 格式, uint8)
    test_size = (512, 512)
    white_bgr_uint8 = np.full((test_size[0], test_size[1], 3), 255, dtype=np.uint8)
    
    print(f"\n輸入圖像:")
    print(f"  格式: {white_bgr_uint8.dtype}, 形狀: {white_bgr_uint8.shape}")
    print(f"  範圍: [{white_bgr_uint8.min()}, {white_bgr_uint8.max()}]")
    print(f"  平均值: B={white_bgr_uint8[:,:,0].mean():.1f}, "
          f"G={white_bgr_uint8[:,:,1].mean():.1f}, "
          f"R={white_bgr_uint8[:,:,2].mean():.1f}")
    
    # 載入膠片
    film_name = "Portra400"
    film = get_film_profile(film_name)
    print(f"\n膠片: {film_name}")
    print(f"  類型: {film.color_type}")
    
    # 光譜響應
    print("\n--- 步驟 1: 光譜響應 ---")
    response_r, response_g, response_b, response_total = spectral_response(white_bgr_uint8, film)
    
    if film.color_type == "color":
        print(f"response_r: 範圍 [{response_r.min():.6f}, {response_r.max():.6f}], 平均 {response_r.mean():.6f}")
        print(f"response_g: 範圍 [{response_g.min():.6f}, {response_g.max():.6f}], 平均 {response_g.mean():.6f}")
        print(f"response_b: 範圍 [{response_b.min():.6f}, {response_b.max():.6f}], 平均 {response_b.mean():.6f}")
    print(f"response_total: 範圍 [{response_total.min():.6f}, {response_total.max():.6f}], 平均 {response_total.mean():.6f}")
    
    # 檢查光譜響應係數
    print("\n光譜響應係數:")
    r_r, r_g, r_b, g_r, g_g, g_b, b_r, b_g, b_b, t_r, t_g, t_b = film.get_spectral_response()
    print(f"  Red Layer:   r={r_r:.3f}, g={r_g:.3f}, b={r_b:.3f}")
    print(f"  Green Layer: r={g_r:.3f}, g={g_g:.3f}, b={g_b:.3f}")
    print(f"  Blue Layer:  r={b_r:.3f}, g={b_g:.3f}, b={b_b:.3f}")
    print(f"  Total:       r={t_r:.3f}, g={t_g:.3f}, b={t_b:.3f}")
    
    # Tone mapping
    print("\n--- 步驟 2: Tone Mapping (Reinhard) ---")
    result_r, result_g, result_b, result_total = apply_reinhard(
        response_r, response_g, response_b, response_total, film
    )
    
    if film.color_type == "color":
        print(f"result_r: 範圍 [{result_r.min():.6f}, {result_r.max():.6f}], 平均 {result_r.mean():.6f}")
        print(f"result_g: 範圍 [{result_g.min():.6f}, {result_g.max():.6f}], 平均 {result_g.mean():.6f}")
        print(f"result_b: 範圍 [{result_b.min():.6f}, {result_b.max():.6f}], 平均 {result_b.mean():.6f}")
        
        # 合併 RGB
        output_rgb = np.stack([result_r, result_g, result_b], axis=-1)
    else:
        print(f"result_total: 範圍 [{result_total.min():.6f}, {result_total.max():.6f}], 平均 {result_total.mean():.6f}")
        output_rgb = np.stack([result_total] * 3, axis=-1)
    
    # 轉換回 uint8
    output_uint8 = np.clip(output_rgb * 255, 0, 255).astype(np.uint8)
    output_bgr = cv2.cvtColor(output_uint8, cv2.COLOR_RGB2BGR)
    
    print(f"\n輸出圖像:")
    print(f"  格式: {output_bgr.dtype}, 形狀: {output_bgr.shape}")
    print(f"  範圍: [{output_bgr.min()}, {output_bgr.max()}]")
    print(f"  平均值: B={output_bgr[:,:,0].mean():.1f}, "
          f"G={output_bgr[:,:,1].mean():.1f}, "
          f"R={output_bgr[:,:,2].mean():.1f}")
    
    # 保存結果
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    # 並排比較
    comparison = np.hstack([white_bgr_uint8, output_bgr])
    output_path = output_dir / "simple_test_white.png"
    cv2.imwrite(str(output_path), comparison)
    print(f"\n✓ 保存結果: {output_path}")
    
    # 診斷
    print("\n" + "=" * 70)
    print("診斷結果")
    print("=" * 70)
    
    input_brightness = white_bgr_uint8.mean() / 255.0
    output_brightness = output_bgr.mean() / 255.0
    brightness_ratio = output_brightness / input_brightness
    
    print(f"輸入亮度: {input_brightness:.3f}")
    print(f"輸出亮度: {output_brightness:.3f}")
    print(f"亮度比: {brightness_ratio:.3f}")
    
    if brightness_ratio < 0.1:
        print("\n⚠ 嚴重問題：輸出亮度遠低於輸入（<10%）")
        print("  可能原因：")
        print("  1. 光譜響應係數過小")
        print("  2. Tone mapping 參數不當")
        print("  3. 能量損失（歸一化問題）")
    elif brightness_ratio < 0.5:
        print("\n⚠ 中度問題：輸出亮度偏暗（<50%）")
    elif brightness_ratio > 1.2:
        print("\n⚠ 輕微問題：輸出亮度偏亮（>120%）")
    else:
        print("\n✓ 正常：亮度保持合理")
    
    print("=" * 70)


if __name__ == "__main__":
    test_simple()
