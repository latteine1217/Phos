"""
單色測試 - 驗證 Phos 顏色輸出合理性

測試目標：
1. 使用純色輸入（紅、綠、藍、白、灰、黑）
2. 檢查處理後的顏色是否合理（不應出現色偏）
3. 驗證亮度一致性（灰階應保持灰階）
4. 驗證通道獨立性（純色應保持單通道主導）

使用方式：
    python test_monochrome_colors.py

輸出：
    - 終端顯示測試結果（PASS/FAIL）
    - 生成視覺化圖像：test_output/monochrome_test_*.png
"""

import numpy as np
import cv2
from pathlib import Path
from typing import Dict, Tuple, List
import sys

# 導入 Phos 核心模組
from film_models import FilmProfile, get_film_profile
from phos_core import process_color_channels_parallel
from modules.optical_core import spectral_response
from modules.tone_mapping import apply_reinhard, apply_filmic


# ==================== 測試配置 ====================

# 測試圖像尺寸
TEST_SIZE = (512, 512)

# 測試顏色集（RGB 格式，0-255）
TEST_COLORS = {
    "純紅": (255, 0, 0),
    "純綠": (0, 255, 0),
    "純藍": (0, 0, 255),
    "純白": (255, 255, 255),
    "中灰": (128, 128, 128),
    "純黑": (0, 0, 0),
    "黃色": (255, 255, 0),
    "青色": (0, 255, 255),
    "品紅": (255, 0, 255),
}

# 測試膠片類型
TEST_FILMS = [
    "Portra400",
    "Ektar100",
    "Velvia50",
    "Gold200"
]


# ==================== 工具函數 ====================

def create_solid_color_image(color: Tuple[int, int, int], size: Tuple[int, int] = TEST_SIZE) -> np.ndarray:
    """
    建立純色圖像
    
    Args:
        color: RGB 顏色 (0-255)
        size: 圖像尺寸 (height, width)
        
    Returns:
        BGR 圖像 (OpenCV 格式)
    """
    image = np.zeros((size[0], size[1], 3), dtype=np.uint8)
    # OpenCV 使用 BGR
    image[:, :] = [color[2], color[1], color[0]]
    return image


def rgb_to_float(image: np.ndarray) -> np.ndarray:
    """
    將 uint8 BGR 圖像轉換為 float RGB (0-1)
    
    Args:
        image: BGR 圖像 (0-255)
        
    Returns:
        RGB 圖像 (0-1)
    """
    # BGR -> RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # uint8 -> float
    return image_rgb.astype(np.float32) / 255.0


def float_to_bgr(image: np.ndarray) -> np.ndarray:
    """
    將 float RGB 圖像轉換為 uint8 BGR
    
    Args:
        image: RGB 圖像 (0-1)
        
    Returns:
        BGR 圖像 (0-255)
    """
    # Clip 到 0-1
    image_clipped = np.clip(image, 0, 1)
    # float -> uint8
    image_uint8 = (image_clipped * 255).astype(np.uint8)
    # RGB -> BGR
    return cv2.cvtColor(image_uint8, cv2.COLOR_RGB2BGR)


def calculate_color_shift(input_rgb: np.ndarray, output_rgb: np.ndarray) -> Dict[str, float]:
    """
    計算色偏指標
    
    Args:
        input_rgb: 輸入 RGB (0-1)
        output_rgb: 輸出 RGB (0-1)
        
    Returns:
        色偏指標字典
    """
    # 平均顏色
    input_mean = input_rgb.mean(axis=(0, 1))
    output_mean = output_rgb.mean(axis=(0, 1))
    
    # 色偏向量
    shift = output_mean - input_mean
    
    # 色偏大小（歐氏距離）
    shift_magnitude = np.linalg.norm(shift)
    
    # 主導通道是否改變
    input_dominant = np.argmax(input_mean)
    output_dominant = np.argmax(output_mean)
    dominant_changed = (input_dominant != output_dominant)
    
    # 亮度變化
    input_luminance = 0.299 * input_mean[0] + 0.587 * input_mean[1] + 0.114 * input_mean[2]
    output_luminance = 0.299 * output_mean[0] + 0.587 * output_mean[1] + 0.114 * output_mean[2]
    luminance_ratio = output_luminance / (input_luminance + 1e-8)
    
    return {
        "shift_r": shift[0],
        "shift_g": shift[1],
        "shift_b": shift[2],
        "shift_magnitude": shift_magnitude,
        "dominant_changed": dominant_changed,
        "input_dominant": ["R", "G", "B"][input_dominant],
        "output_dominant": ["R", "G", "B"][output_dominant],
        "luminance_ratio": luminance_ratio,
        "input_mean": input_mean,
        "output_mean": output_mean,
    }


def check_grayscale_preservation(input_rgb: np.ndarray, output_rgb: np.ndarray, tolerance: float = 0.05) -> bool:
    """
    檢查灰階是否保持（無色偏）
    
    Args:
        input_rgb: 輸入 RGB (0-1)
        output_rgb: 輸出 RGB (0-1)
        tolerance: 容差閾值
        
    Returns:
        True 如果灰階保持，False 如果出現色偏
    """
    # 計算輸入是否為灰階
    input_mean = input_rgb.mean(axis=(0, 1))
    input_std = input_rgb.std(axis=(0, 1))
    is_input_gray = np.all(input_std < 0.01) and np.allclose(input_mean[0], input_mean[1], atol=0.01)
    
    if not is_input_gray:
        return True  # 非灰階輸入，不檢查
    
    # 檢查輸出是否仍為灰階
    output_mean = output_rgb.mean(axis=(0, 1))
    max_channel_diff = output_mean.max() - output_mean.min()
    
    return max_channel_diff < tolerance


# ==================== 主測試函數 ====================

def test_single_color(color_name: str, color_rgb: Tuple[int, int, int], 
                      film_name: str, tone_style: str = "reinhard") -> Dict:
    """
    測試單一顏色
    
    Args:
        color_name: 顏色名稱
        color_rgb: RGB 顏色 (0-255)
        film_name: 膠片名稱
        tone_style: Tone mapping 風格
        
    Returns:
        測試結果字典
    """
    # 建立輸入圖像
    input_bgr = create_solid_color_image(color_rgb)
    input_rgb = rgb_to_float(input_bgr)
    
    # 載入膠片配置
    film = get_film_profile(film_name)
    
    # 光譜響應
    response_r, response_g, response_b, response_total = spectral_response(input_rgb, film)
    
    # Tone mapping
    if tone_style == "reinhard":
        result_r, result_g, result_b, result_total = apply_reinhard(
            response_r, response_g, response_b, response_total, film
        )
    else:  # filmic
        result_r, result_g, result_b, result_total = apply_filmic(
            response_r, response_g, response_b, response_total, film
        )
    
    # 合併結果
    if film.color_type == "color":
        output_rgb = np.stack([result_r, result_g, result_b], axis=-1)
    else:
        output_rgb = np.stack([result_total] * 3, axis=-1)
    
    # 計算指標
    shift_metrics = calculate_color_shift(input_rgb, output_rgb)
    is_gray_preserved = check_grayscale_preservation(input_rgb, output_rgb)
    
    # 轉換回 BGR 以便保存
    output_bgr = float_to_bgr(output_rgb)
    
    return {
        "color_name": color_name,
        "film_name": film_name,
        "tone_style": tone_style,
        "input_bgr": input_bgr,
        "output_bgr": output_bgr,
        "shift_metrics": shift_metrics,
        "is_gray_preserved": is_gray_preserved,
    }


def visualize_results(results: List[Dict], output_dir: Path):
    """
    視覺化測試結果
    
    Args:
        results: 測試結果列表
        output_dir: 輸出目錄
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 按膠片分組
    for film_name in TEST_FILMS:
        film_results = [r for r in results if r["film_name"] == film_name]
        if not film_results:
            continue
        
        # 建立網格圖像
        n_colors = len(film_results)
        grid_cols = 4
        grid_rows = (n_colors + grid_cols - 1) // grid_cols
        
        cell_height = TEST_SIZE[0]
        cell_width = TEST_SIZE[1] * 2  # 輸入 + 輸出
        
        grid = np.zeros((grid_rows * cell_height, grid_cols * cell_width, 3), dtype=np.uint8)
        
        for idx, result in enumerate(film_results):
            row = idx // grid_cols
            col = idx % grid_cols
            
            y = row * cell_height
            x = col * cell_width
            
            # 放置輸入
            grid[y:y+cell_height, x:x+TEST_SIZE[1]] = result["input_bgr"]
            
            # 放置輸出
            grid[y:y+cell_height, x+TEST_SIZE[1]:x+cell_width] = result["output_bgr"]
            
            # 添加文字標籤
            color_name = result["color_name"]
            cv2.putText(grid, color_name, (x + 10, y + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 保存
        output_path = output_dir / f"monochrome_test_{film_name.replace(' ', '_')}.png"
        cv2.imwrite(str(output_path), grid)
        print(f"✓ 保存視覺化結果: {output_path}")


def run_tests():
    """
    執行所有測試
    """
    print("=" * 70)
    print("Phos 單色測試 - 顏色輸出合理性驗證")
    print("=" * 70)
    print()
    
    all_results = []
    test_passed = 0
    test_failed = 0
    
    for film_name in TEST_FILMS:
        print(f"\n--- 測試膠片: {film_name} ---\n")
        
        for color_name, color_rgb in TEST_COLORS.items():
            result = test_single_color(color_name, color_rgb, film_name, tone_style="reinhard")
            all_results.append(result)
            
            metrics = result["shift_metrics"]
            is_gray_ok = result["is_gray_preserved"]
            
            # 判定標準
            shift_threshold = 0.15  # 色偏閾值
            is_passed = (metrics["shift_magnitude"] < shift_threshold) and is_gray_ok
            
            status = "✓ PASS" if is_passed else "✗ FAIL"
            if is_passed:
                test_passed += 1
            else:
                test_failed += 1
            
            # 輸出結果
            print(f"{status} | {color_name:8s} | "
                  f"色偏: {metrics['shift_magnitude']:.3f} | "
                  f"主導: {metrics['input_dominant']}→{metrics['output_dominant']} | "
                  f"亮度比: {metrics['luminance_ratio']:.2f}")
            
            # 如果失敗，顯示詳細資訊
            if not is_passed:
                print(f"  ⚠ 輸入平均: R={metrics['input_mean'][0]:.3f} "
                      f"G={metrics['input_mean'][1]:.3f} B={metrics['input_mean'][2]:.3f}")
                print(f"  ⚠ 輸出平均: R={metrics['output_mean'][0]:.3f} "
                      f"G={metrics['output_mean'][1]:.3f} B={metrics['output_mean'][2]:.3f}")
                if not is_gray_ok:
                    print(f"  ⚠ 灰階色偏檢測失敗")
    
    # 生成視覺化
    print("\n" + "=" * 70)
    print("生成視覺化結果...")
    print("=" * 70)
    output_dir = Path("test_output")
    visualize_results(all_results, output_dir)
    
    # 總結
    print("\n" + "=" * 70)
    print("測試總結")
    print("=" * 70)
    total_tests = test_passed + test_failed
    pass_rate = (test_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"總測試數: {total_tests}")
    print(f"通過: {test_passed} ({pass_rate:.1f}%)")
    print(f"失敗: {test_failed}")
    print("=" * 70)
    
    return test_failed == 0


# ==================== 主程式 ====================

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
