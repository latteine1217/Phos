"""
完整單色測試 - 修正版

使用正確的輸入格式（BGR uint8）測試所有顏色
"""

import numpy as np
import cv2
from pathlib import Path
from typing import Dict, Tuple, List

from film_models import get_film_profile
from modules.optical_core import spectral_response
from modules.tone_mapping import apply_reinhard


# ==================== 測試配置 ====================

TEST_SIZE = (256, 256)

# 測試顏色（BGR 格式，因為 OpenCV）
TEST_COLORS = {
    "純紅": (0, 0, 255),
    "純綠": (0, 255, 0),
    "純藍": (255, 0, 0),
    "純白": (255, 255, 255),
    "中灰": (128, 128, 128),
    "暗灰": (64, 64, 64),
    "純黑": (0, 0, 0),
    "黃色": (0, 255, 255),
    "青色": (255, 255, 0),
    "品紅": (255, 0, 255),
}

TEST_FILMS = ["Portra400", "Ektar100", "Velvia50"]


# ==================== 測試函數 ====================

def create_test_image(color_bgr: Tuple[int, int, int]) -> np.ndarray:
    """建立純色測試圖像"""
    image = np.full((TEST_SIZE[0], TEST_SIZE[1], 3), color_bgr, dtype=np.uint8)
    return image


def process_test_image(image_bgr: np.ndarray, film_name: str) -> np.ndarray:
    """
    處理測試圖像
    
    Returns:
        output_bgr: 處理後的圖像 (BGR uint8)
    """
    film = get_film_profile(film_name)
    
    # 光譜響應
    response_r, response_g, response_b, response_total = spectral_response(image_bgr, film)
    
    # Tone mapping
    result_r, result_g, result_b, result_total = apply_reinhard(
        response_r, response_g, response_b, response_total, film
    )
    
    # 合併結果
    if film.color_type == "color":
        output_rgb = np.stack([result_r, result_g, result_b], axis=-1)
    else:
        output_rgb = np.stack([result_total] * 3, axis=-1)
    
    # 轉換回 BGR uint8
    output_uint8 = np.clip(output_rgb * 255, 0, 255).astype(np.uint8)
    output_bgr = cv2.cvtColor(output_uint8, cv2.COLOR_RGB2BGR)
    
    return output_bgr


def analyze_color_shift(input_bgr: np.ndarray, output_bgr: np.ndarray, 
                        color_name: str) -> Dict:
    """
    分析色偏
    
    Returns:
        分析結果字典
    """
    # 轉換到 RGB 以便分析
    input_rgb = cv2.cvtColor(input_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    output_rgb = cv2.cvtColor(output_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    
    # 平均顏色
    input_mean = input_rgb.mean(axis=(0, 1))
    output_mean = output_rgb.mean(axis=(0, 1))
    
    # 色偏向量
    shift = output_mean - input_mean
    shift_magnitude = np.linalg.norm(shift)
    
    # 主導通道
    input_dominant = np.argmax(input_mean)
    output_dominant = np.argmax(output_mean)
    dominant_channels = ["R", "G", "B"]
    
    # 亮度
    input_lum = 0.299 * input_mean[0] + 0.587 * input_mean[1] + 0.114 * input_mean[2]
    output_lum = 0.299 * output_mean[0] + 0.587 * output_mean[1] + 0.114 * output_mean[2]
    lum_ratio = output_lum / (input_lum + 1e-8)
    
    # 色相保持（檢查灰階）
    is_input_gray = np.allclose(input_mean[0], input_mean[1], atol=0.01) and \
                    np.allclose(input_mean[1], input_mean[2], atol=0.01)
    
    if is_input_gray:
        # 檢查輸出是否仍為灰階
        max_channel_diff = output_mean.max() - output_mean.min()
        hue_preserved = max_channel_diff < 0.05
    else:
        # 檢查主導通道是否改變
        hue_preserved = (input_dominant == output_dominant)
    
    # 判定是否通過
    passed = True
    issues = []
    
    # 標準 1: 色偏不能太大
    if shift_magnitude > 0.20:
        passed = False
        issues.append(f"色偏過大 ({shift_magnitude:.3f})")
    
    # 標準 2: 灰階必須保持
    if is_input_gray and not hue_preserved:
        passed = False
        issues.append("灰階出現色偏")
    
    # 標準 3: 主導通道不應改變（純色）
    if not is_input_gray and input_mean.max() > 0.9 and not hue_preserved:
        passed = False
        issues.append(f"主導通道改變 ({dominant_channels[input_dominant]}→{dominant_channels[output_dominant]})")
    
    # 標準 4: 亮度不能損失太多
    if lum_ratio < 0.3:
        passed = False
        issues.append(f"亮度損失過大 ({lum_ratio:.2f})")
    
    return {
        "color_name": color_name,
        "input_mean": input_mean,
        "output_mean": output_mean,
        "shift": shift,
        "shift_magnitude": shift_magnitude,
        "input_dominant": dominant_channels[input_dominant],
        "output_dominant": dominant_channels[output_dominant],
        "lum_ratio": lum_ratio,
        "is_input_gray": is_input_gray,
        "hue_preserved": hue_preserved,
        "passed": passed,
        "issues": issues,
    }


def create_visualization(results: List[Tuple[np.ndarray, np.ndarray, str]], 
                        film_name: str, output_dir: Path):
    """
    建立視覺化網格
    
    Args:
        results: [(input_bgr, output_bgr, color_name), ...]
        film_name: 膠片名稱
        output_dir: 輸出目錄
    """
    n_colors = len(results)
    grid_cols = 5
    grid_rows = (n_colors + grid_cols - 1) // grid_cols
    
    cell_width = TEST_SIZE[1] * 2  # input + output
    cell_height = TEST_SIZE[0] + 40  # 額外空間放文字
    
    grid = np.zeros((grid_rows * cell_height, grid_cols * cell_width, 3), dtype=np.uint8)
    
    for idx, (input_bgr, output_bgr, color_name) in enumerate(results):
        row = idx // grid_cols
        col = idx % grid_cols
        
        y = row * cell_height
        x = col * cell_width
        
        # 放置輸入（左）
        grid[y:y+TEST_SIZE[0], x:x+TEST_SIZE[1]] = input_bgr
        
        # 放置輸出（右）
        grid[y:y+TEST_SIZE[0], x+TEST_SIZE[1]:x+cell_width] = output_bgr
        
        # 添加分隔線
        cv2.line(grid, (x + TEST_SIZE[1], y), (x + TEST_SIZE[1], y + TEST_SIZE[0]), 
                (128, 128, 128), 2)
        
        # 添加文字標籤
        text_y = y + TEST_SIZE[0] + 25
        cv2.putText(grid, color_name, (x + 10, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(grid, "Before", (x + 10, y + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(grid, "After", (x + TEST_SIZE[1] + 10, y + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
    # 保存
    output_path = output_dir / f"color_test_{film_name}.png"
    cv2.imwrite(str(output_path), grid)
    print(f"✓ 保存視覺化: {output_path}")


def run_all_tests():
    """執行所有測試"""
    
    print("=" * 80)
    print(" " * 20 + "Phos 單色測試 - 顏色輸出驗證")
    print("=" * 80)
    print()
    
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    total_passed = 0
    total_failed = 0
    
    for film_name in TEST_FILMS:
        print(f"\n{'─' * 80}")
        print(f"膠片: {film_name}")
        print(f"{'─' * 80}\n")
        
        film_results = []
        
        for color_name, color_bgr in TEST_COLORS.items():
            # 建立測試圖像
            input_bgr = create_test_image(color_bgr)
            
            # 處理
            output_bgr = process_test_image(input_bgr, film_name)
            
            # 分析
            analysis = analyze_color_shift(input_bgr, output_bgr, color_name)
            
            # 記錄結果
            film_results.append((input_bgr, output_bgr, color_name))
            
            # 顯示結果
            status = "✓ PASS" if analysis["passed"] else "✗ FAIL"
            if analysis["passed"]:
                total_passed += 1
            else:
                total_failed += 1
            
            # 格式化輸出
            print(f"{status} | {color_name:8s} | "
                  f"色偏: {analysis['shift_magnitude']:5.3f} | "
                  f"主導: {analysis['input_dominant']}→{analysis['output_dominant']} | "
                  f"亮度: {analysis['lum_ratio']:4.2f}x", end="")
            
            if not analysis["passed"]:
                print(f" | 問題: {', '.join(analysis['issues'])}")
            else:
                print()
        
        # 建立視覺化
        create_visualization(film_results, film_name, output_dir)
    
    # 總結
    print("\n" + "=" * 80)
    print(" " * 30 + "測試總結")
    print("=" * 80)
    total = total_passed + total_failed
    pass_rate = (total_passed / total * 100) if total > 0 else 0
    
    print(f"總測試數: {total}")
    print(f"通過: {total_passed} ({pass_rate:.1f}%)")
    print(f"失敗: {total_failed}")
    
    if total_failed == 0:
        print("\n✓ 所有測試通過！顏色輸出合理。")
    else:
        print(f"\n⚠ 有 {total_failed} 個測試失敗，需要檢查。")
    
    print("=" * 80)
    
    return total_failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
