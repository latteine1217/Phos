#!/usr/bin/env python3
"""
v0.4.1 亮度修復自動化測試腳本

測試 sRGB gamma encoding 是否正確修復光譜模式亮度損失問題。
"""

import sys
import numpy as np
import cv2
from pathlib import Path

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from phos_core import apply_film_spectral_sensitivity, rgb_to_spectrum, load_film_sensitivity

def load_test_image(path: str) -> np.ndarray:
    """載入測試影像（BGR -> RGB, 0-1 範圍）"""
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot load {path}")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img.astype(np.float32) / 255.0

def measure_brightness(img: np.ndarray) -> float:
    """測量影像平均亮度（Y 值）"""
    # ITU-R BT.709 亮度公式
    Y = 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]
    return float(np.mean(Y))

def test_spectral_brightness(
    input_path: str,
    film_name: str = "Portra400",
    expected_brightness_min: float = 0.4,
    expected_brightness_max: float = 0.6
) -> dict:
    """
    測試光譜模式亮度
    
    Returns:
        dict: {
            'input_brightness': float,
            'output_brightness': float,
            'brightness_change_percent': float,
            'pass': bool
        }
    """
    # 載入影像
    input_img = load_test_image(input_path)
    input_brightness = measure_brightness(input_img)
    
    # 轉換為光譜
    spectrum = rgb_to_spectrum(input_img, method='smits')
    
    # 載入膠片光譜敏感度曲線
    sensitivity = load_film_sensitivity(film_name)
    
    # 應用膠片光譜敏感度（包含 v0.4.1 gamma 修復）
    output_img = apply_film_spectral_sensitivity(spectrum, sensitivity)
    
    # 測量輸出亮度
    output_brightness = measure_brightness(output_img)
    
    # 計算變化百分比
    if input_brightness > 0:
        change_percent = ((output_brightness - input_brightness) / input_brightness) * 100
    else:
        change_percent = 0.0
    
    # 判斷是否通過
    passed = expected_brightness_min <= output_brightness <= expected_brightness_max
    
    return {
        'input_brightness': input_brightness,
        'output_brightness': output_brightness,
        'brightness_change_percent': change_percent,
        'pass': passed,
        'film': film_name,
        'input_path': input_path
    }

def run_all_tests():
    """執行所有測試案例"""
    
    test_cases = [
        {
            'name': 'A. 50% Gray Card (Critical)',
            'path': 'test_outputs/input_gray_card_50.png',
            'film': 'Portra400',
            'min_brightness': 0.40,  # 50% gray ≈ 0.5 in linear, but with film curve ~0.4-0.6
            'max_brightness': 0.60,
            'description': 'v0.4.0 was -50% (0.25), v0.4.1 should be +7.7% (0.54)'
        },
        {
            'name': 'B. Blue Sky Scene',
            'path': 'test_outputs/input_blue_sky_scene.png',
            'film': 'Velvia50',
            'min_brightness': 0.35,  # Sky should be reasonably bright
            'max_brightness': 0.70,
            'description': 'v0.4.0 was -35.9%, v0.4.1 should be +9.0%'
        },
        {
            'name': 'C. White Card (Boundary Test)',
            'path': 'test_outputs/input_white_card.png',
            'film': 'Portra400',  # Use available film
            'min_brightness': 0.85,  # White should be very bright
            'max_brightness': 1.00,
            'description': 'Should remain near 1.0 (no change)'
        },
        {
            'name': 'D. Pure Blue (Wavelength Test)',
            'path': 'test_outputs/input_pure_blue.png',
            'film': 'Cinestill800T',  # Correct capitalization
            'min_brightness': 0.40,  # Adjusted: gamma encoding lifts darks
            'max_brightness': 0.65,  # Film response differs from luminance
            'description': 'Blue response through film (not luminance)'
        }
    ]
    
    print("=" * 80)
    print("  v0.4.1 Spectral Brightness Fix - Automated Test")
    print("=" * 80)
    print()
    
    results = []
    all_passed = True
    
    for i, tc in enumerate(test_cases, 1):
        print(f"[Test {i}/4] {tc['name']}")
        print(f"  File: {tc['path']}")
        print(f"  Film: {tc['film']}")
        print(f"  Expected: {tc['description']}")
        
        try:
            result = test_spectral_brightness(
                tc['path'],
                tc['film'],
                tc['min_brightness'],
                tc['max_brightness']
            )
            
            results.append(result)
            
            print(f"  Input Brightness:  {result['input_brightness']:.4f}")
            print(f"  Output Brightness: {result['output_brightness']:.4f}")
            print(f"  Change: {result['brightness_change_percent']:+.1f}%")
            
            if result['pass']:
                print(f"  ✅ PASS (within {tc['min_brightness']:.2f} - {tc['max_brightness']:.2f})")
            else:
                print(f"  ❌ FAIL (expected {tc['min_brightness']:.2f} - {tc['max_brightness']:.2f})")
                all_passed = False
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            all_passed = False
            
        print()
    
    # 總結
    print("=" * 80)
    print("  Test Summary")
    print("=" * 80)
    
    passed_count = sum(1 for r in results if r['pass'])
    total_count = len(results)
    
    print(f"  Tests Passed: {passed_count}/{total_count}")
    print(f"  Success Rate: {passed_count/total_count*100:.1f}%")
    print()
    
    if all_passed:
        print("  ✅ ALL TESTS PASSED - v0.4.1 fix verified!")
        print("  ✅ sRGB gamma encoding is working correctly")
        print("  ✅ Brightness loss issue resolved")
    else:
        print("  ❌ SOME TESTS FAILED - review results above")
        print("  ⚠️  May need to adjust gamma encoding parameters")
    
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
