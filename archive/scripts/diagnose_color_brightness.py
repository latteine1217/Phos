"""
色彩與亮度診斷測試腳本

此腳本用於重現並診斷 Phos v0.4.0 中的「變暗＋變色」問題
生成多種測試圖像，通過不同模式處理，並分析輸出結果

Usage:
    python scripts/diagnose_color_brightness.py

Output:
    - 測試圖像: test_outputs/diagnostic_*.png
    - 分析報告: test_outputs/diagnostic_report.txt
    - 對比圖表: test_outputs/diagnostic_comparison.png
"""

import cv2
import numpy as np
import sys
import os
from pathlib import Path
from typing import Tuple, Dict
import time

# 添加專案根目錄到 Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 導入 Phos 核心模組
try:
    import film_models
    from film_models import FilmProfile, PhysicsMode, create_film_profiles
except ImportError as e:
    print(f"❌ 無法導入 film_models: {e}")
    sys.exit(1)

# 創建輸出目錄
output_dir = project_root / "test_outputs"
output_dir.mkdir(exist_ok=True)


# ==================== 測試圖像生成 ====================

def generate_test_images() -> Dict[str, np.ndarray]:
    """
    生成標準測試圖像（BGR 格式）
    
    Returns:
        Dict[str, np.ndarray]: 測試圖像字典
    """
    test_images = {}
    
    # 1. 純色測試（用於檢測通道互換）
    # 純藍色 (BGR = [255, 0, 0])
    blue_img = np.zeros((400, 400, 3), dtype=np.uint8)
    blue_img[:, :, 0] = 255  # B channel
    test_images['pure_blue'] = blue_img
    
    # 純紅色 (BGR = [0, 0, 255])
    red_img = np.zeros((400, 400, 3), dtype=np.uint8)
    red_img[:, :, 2] = 255  # R channel
    test_images['pure_red'] = red_img
    
    # 純綠色 (BGR = [0, 255, 0])
    green_img = np.zeros((400, 400, 3), dtype=np.uint8)
    green_img[:, :, 1] = 255  # G channel
    test_images['pure_green'] = green_img
    
    # 2. 灰階測試（用於檢測亮度變化）
    gray_bars = np.zeros((400, 400, 3), dtype=np.uint8)
    for i, intensity in enumerate([0, 64, 128, 192, 255]):
        gray_bars[:, i*80:(i+1)*80, :] = intensity
    test_images['gray_bars'] = gray_bars
    
    # 3. 彩色漸層測試（用於檢測色彩偏移）
    color_gradient = np.zeros((400, 400, 3), dtype=np.uint8)
    for x in range(400):
        # 水平方向：藍→紅
        color_gradient[:, x, 0] = int(255 * (1 - x/400))  # B: 255→0
        color_gradient[:, x, 2] = int(255 * (x/400))      # R: 0→255
    test_images['color_gradient'] = color_gradient
    
    # 4. 藍天場景模擬（真實場景測試）
    blue_sky = np.zeros((400, 400, 3), dtype=np.uint8)
    # 天空：B=220, G=180, R=120 (偏藍色調)
    blue_sky[:200, :, :] = [220, 180, 120]  # 上半部：天空
    # 地面：B=80, G=120, R=100 (偏綠褐色)
    blue_sky[200:, :, :] = [80, 120, 100]   # 下半部：地面
    test_images['blue_sky_scene'] = blue_sky
    
    # 5. 中性灰卡（50% 灰）
    gray_card = np.full((400, 400, 3), 128, dtype=np.uint8)
    test_images['gray_card_50'] = gray_card
    
    # 6. 白卡（用於檢測高光處理）
    white_card = np.full((400, 400, 3), 255, dtype=np.uint8)
    test_images['white_card'] = white_card
    
    return test_images


def save_test_images(test_images: Dict[str, np.ndarray]) -> None:
    """儲存原始測試圖像"""
    for name, img in test_images.items():
        output_path = output_dir / f"input_{name}.png"
        cv2.imwrite(str(output_path), img)
        print(f"✅ 已儲存測試圖像: {output_path.name}")


# ==================== 簡化版 Phos 處理流程 ====================

def simple_spectral_response(image: np.ndarray, film: FilmProfile) -> Tuple:
    """
    簡化版光譜響應計算（直接從 Phos.py 複製）
    """
    b, g, r = cv2.split(image)
    
    r_float = r.astype(np.float32) / 255.0
    g_float = g.astype(np.float32) / 255.0
    b_float = b.astype(np.float32) / 255.0
    
    r_r, r_g, r_b, g_r, g_g, g_b, b_r, b_g, b_b, t_r, t_g, t_b = film.get_spectral_response()
    
    if film.color_type == "color":
        response_r = r_r * r_float + r_g * g_float + r_b * b_float
        response_g = g_r * r_float + g_g * g_float + g_b * b_float
        response_b = b_r * r_float + b_g * g_float + b_b * b_float
    else:
        response_r = response_g = response_b = None
    
    return response_r, response_g, response_b


def simple_tone_mapping(response_r: np.ndarray, response_g: np.ndarray, 
                       response_b: np.ndarray) -> np.ndarray:
    """
    最簡單的 tone mapping（無物理效果）
    """
    # 直接轉換為 0-255
    result_r = np.clip(response_r * 255, 0, 255).astype(np.uint8)
    result_g = np.clip(response_g * 255, 0, 255).astype(np.uint8)
    result_b = np.clip(response_b * 255, 0, 255).astype(np.uint8)
    
    # 組合為 BGR 圖像
    return cv2.merge([result_b, result_g, result_r])


def process_simple(image: np.ndarray, film: FilmProfile, 
                  use_spectral: bool = False) -> Tuple[np.ndarray, Dict]:
    """
    簡化版處理流程（模擬 Phos 核心邏輯）
    
    Args:
        image: 輸入圖像 (BGR, 0-255)
        film: 膠片配置
        use_spectral: 是否使用光譜模型
        
    Returns:
        (processed_image_bgr, statistics)
    """
    stats = {}
    
    # 1. 計算光譜響應
    response_r, response_g, response_b = simple_spectral_response(image, film)
    
    # 2. 統計原始響應值
    stats['response_mean'] = {
        'r': float(np.mean(response_r)),
        'g': float(np.mean(response_g)),
        'b': float(np.mean(response_b))
    }
    
    # 3. 如果啟用光譜模型
    if use_spectral:
        try:
            from phos_core import rgb_to_spectrum, apply_film_spectral_sensitivity, load_film_sensitivity
            
            # 合併為 RGB 陣列
            lux_combined = np.stack([response_r, response_g, response_b], axis=2)
            
            # RGB → Spectrum → Film RGB
            spectrum = rgb_to_spectrum(lux_combined, use_tiling=True, tile_size=512)
            film_curves = load_film_sensitivity('Portra400')
            rgb_with_film = apply_film_spectral_sensitivity(spectrum, film_curves, normalize=True)
            
            response_r = rgb_with_film[:, :, 0]
            response_g = rgb_with_film[:, :, 1]
            response_b = rgb_with_film[:, :, 2]
            
            stats['spectral_applied'] = True
            stats['response_after_spectral_mean'] = {
                'r': float(np.mean(response_r)),
                'g': float(np.mean(response_g)),
                'b': float(np.mean(response_b))
            }
        except Exception as e:
            stats['spectral_error'] = str(e)
            stats['spectral_applied'] = False
    else:
        stats['spectral_applied'] = False
    
    # 4. Tone mapping
    final_bgr = simple_tone_mapping(response_r, response_g, response_b)
    
    # 5. 統計最終輸出
    stats['output_mean'] = {
        'b': float(np.mean(final_bgr[:, :, 0])),
        'g': float(np.mean(final_bgr[:, :, 1])),
        'r': float(np.mean(final_bgr[:, :, 2]))
    }
    
    return final_bgr, stats


# ==================== 分析與比較 ====================

def analyze_color_shift(input_bgr: np.ndarray, output_bgr: np.ndarray) -> Dict:
    """
    分析色彩偏移
    
    Returns:
        Dict: 分析結果
    """
    input_mean = {
        'b': float(np.mean(input_bgr[:, :, 0])),
        'g': float(np.mean(input_bgr[:, :, 1])),
        'r': float(np.mean(input_bgr[:, :, 2]))
    }
    
    output_mean = {
        'b': float(np.mean(output_bgr[:, :, 0])),
        'g': float(np.mean(output_bgr[:, :, 1])),
        'r': float(np.mean(output_bgr[:, :, 2]))
    }
    
    # 計算亮度變化
    input_luminance = 0.299 * input_mean['r'] + 0.587 * input_mean['g'] + 0.114 * input_mean['b']
    output_luminance = 0.299 * output_mean['r'] + 0.587 * output_mean['g'] + 0.114 * output_mean['b']
    luminance_change_percent = ((output_luminance - input_luminance) / (input_luminance + 1e-6)) * 100
    
    # 檢測通道互換
    channel_swap_detected = False
    swap_type = "None"
    
    # 如果輸入是純色，檢測輸出是否換了通道
    if input_mean['b'] > 200 and input_mean['r'] < 50:  # 純藍
        if output_mean['r'] > output_mean['b']:
            channel_swap_detected = True
            swap_type = "B↔R"
    elif input_mean['r'] > 200 and input_mean['b'] < 50:  # 純紅
        if output_mean['b'] > output_mean['r']:
            channel_swap_detected = True
            swap_type = "R↔B"
    
    return {
        'input_mean': input_mean,
        'output_mean': output_mean,
        'input_luminance': input_luminance,
        'output_luminance': output_luminance,
        'luminance_change_percent': luminance_change_percent,
        'channel_swap_detected': channel_swap_detected,
        'swap_type': swap_type
    }


def generate_comparison_image(test_images: Dict[str, np.ndarray], 
                             results: Dict[str, Dict]) -> np.ndarray:
    """
    生成對比圖（輸入 vs 輸出）
    """
    # 選擇關鍵測試圖像
    key_tests = ['pure_blue', 'pure_red', 'gray_card_50', 'blue_sky_scene']
    
    rows = []
    for test_name in key_tests:
        if test_name not in test_images:
            continue
            
        input_img = test_images[test_name]
        
        # 調整尺寸
        input_resized = cv2.resize(input_img, (300, 300))
        
        # 獲取輸出圖像
        row_images = [input_resized]
        
        for mode in ['simple', 'spectral']:
            key = f"{test_name}_{mode}"
            if key in results and 'output_bgr' in results[key]:
                output_img = results[key]['output_bgr']
                output_resized = cv2.resize(output_img, (300, 300))
                row_images.append(output_resized)
            else:
                # 黑色佔位
                row_images.append(np.zeros((300, 300, 3), dtype=np.uint8))
        
        # 水平拼接
        row = np.hstack(row_images)
        
        # 添加標籤
        cv2.putText(row, test_name, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.7, (255, 255, 255), 2)
        cv2.putText(row, "Input", (10, 270), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, (255, 255, 255), 1)
        cv2.putText(row, "Simple", (310, 270), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, (255, 255, 255), 1)
        cv2.putText(row, "Spectral", (610, 270), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, (255, 255, 255), 1)
        
        rows.append(row)
    
    # 垂直拼接
    if rows:
        comparison = np.vstack(rows)
        return comparison
    else:
        return np.zeros((300, 300, 3), dtype=np.uint8)


# ==================== 主測試流程 ====================

def main():
    print("=" * 60)
    print("🔬 Phos v0.4.0 色彩與亮度診斷測試")
    print("=" * 60)
    print()
    
    # 1. 生成測試圖像
    print("📸 生成測試圖像...")
    test_images = generate_test_images()
    save_test_images(test_images)
    print()
    
    # 2. 載入膠片配置
    print("🎞️  載入膠片配置...")
    try:
        profiles = create_film_profiles()
        film = profiles['Portra400']
        print(f"✅ 已載入: {film.name}")
        print(f"   色彩類型: {film.color_type}")
    except Exception as e:
        print(f"❌ 載入膠片失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    print()
    
    # 3. 處理測試圖像
    print("⚙️  處理測試圖像...")
    results = {}
    
    for test_name, test_img in test_images.items():
        print(f"\n--- 測試: {test_name} ---")
        
        # 3.1 簡單模式（無光譜）
        print("  [1/2] 簡單模式處理...")
        try:
            output_simple, stats_simple = process_simple(test_img, film, use_spectral=False)
            analysis_simple = analyze_color_shift(test_img, output_simple)
            
            results[f"{test_name}_simple"] = {
                'output_bgr': output_simple,
                'stats': stats_simple,
                'analysis': analysis_simple
            }
            
            # 儲存輸出
            output_path = output_dir / f"output_{test_name}_simple.png"
            cv2.imwrite(str(output_path), output_simple)
            
            # 顯示結果
            print(f"    ✅ 完成")
            print(f"    亮度變化: {analysis_simple['luminance_change_percent']:+.1f}%")
            if analysis_simple['channel_swap_detected']:
                print(f"    ⚠️  檢測到通道互換: {analysis_simple['swap_type']}")
            
        except Exception as e:
            print(f"    ❌ 失敗: {e}")
            results[f"{test_name}_simple"] = {'error': str(e)}
        
        # 3.2 光譜模式
        print("  [2/2] 光譜模式處理...")
        try:
            output_spectral, stats_spectral = process_simple(test_img, film, use_spectral=True)
            analysis_spectral = analyze_color_shift(test_img, output_spectral)
            
            results[f"{test_name}_spectral"] = {
                'output_bgr': output_spectral,
                'stats': stats_spectral,
                'analysis': analysis_spectral
            }
            
            # 儲存輸出
            output_path = output_dir / f"output_{test_name}_spectral.png"
            cv2.imwrite(str(output_path), output_spectral)
            
            # 顯示結果
            print(f"    ✅ 完成")
            print(f"    亮度變化: {analysis_spectral['luminance_change_percent']:+.1f}%")
            if analysis_spectral['channel_swap_detected']:
                print(f"    ⚠️  檢測到通道互換: {analysis_spectral['swap_type']}")
            
        except Exception as e:
            print(f"    ❌ 失敗: {e}")
            results[f"{test_name}_spectral"] = {'error': str(e)}
    
    print()
    
    # 4. 生成對比圖
    print("📊 生成對比圖...")
    comparison_img = generate_comparison_image(test_images, results)
    comparison_path = output_dir / "diagnostic_comparison.png"
    cv2.imwrite(str(comparison_path), comparison_img)
    print(f"✅ 已儲存: {comparison_path.name}")
    print()
    
    # 5. 生成分析報告
    print("📝 生成分析報告...")
    report_path = output_dir / "diagnostic_report.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Phos v0.4.0 色彩與亮度診斷報告\n")
        f.write(f"生成時間: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for test_name in test_images.keys():
            f.write(f"\n{'='*60}\n")
            f.write(f"測試: {test_name}\n")
            f.write(f"{'='*60}\n\n")
            
            for mode in ['simple', 'spectral']:
                key = f"{test_name}_{mode}"
                if key not in results:
                    continue
                
                f.write(f"\n--- {mode.upper()} 模式 ---\n")
                
                result = results[key]
                
                if 'error' in result:
                    f.write(f"❌ 錯誤: {result['error']}\n")
                    continue
                
                # 分析結果
                analysis = result['analysis']
                f.write(f"\n輸入平均值 (BGR):\n")
                f.write(f"  B: {analysis['input_mean']['b']:.1f}\n")
                f.write(f"  G: {analysis['input_mean']['g']:.1f}\n")
                f.write(f"  R: {analysis['input_mean']['r']:.1f}\n")
                
                f.write(f"\n輸出平均值 (BGR):\n")
                f.write(f"  B: {analysis['output_mean']['b']:.1f}\n")
                f.write(f"  G: {analysis['output_mean']['g']:.1f}\n")
                f.write(f"  R: {analysis['output_mean']['r']:.1f}\n")
                
                f.write(f"\n亮度分析:\n")
                f.write(f"  輸入亮度: {analysis['input_luminance']:.1f}\n")
                f.write(f"  輸出亮度: {analysis['output_luminance']:.1f}\n")
                f.write(f"  變化: {analysis['luminance_change_percent']:+.1f}%\n")
                
                if analysis['channel_swap_detected']:
                    f.write(f"\n⚠️  通道互換檢測: {analysis['swap_type']}\n")
                
                # 處理統計
                if 'stats' in result:
                    stats = result['stats']
                    f.write(f"\n處理統計:\n")
                    if 'spectral_applied' in stats:
                        f.write(f"  光譜模型: {'✅ 已應用' if stats['spectral_applied'] else '❌ 未應用'}\n")
                    if 'spectral_error' in stats:
                        f.write(f"  光譜錯誤: {stats['spectral_error']}\n")
        
        f.write(f"\n\n{'='*80}\n")
        f.write("診斷完成\n")
        f.write("=" * 80 + "\n")
    
    print(f"✅ 已儲存: {report_path.name}")
    print()
    
    # 6. 總結
    print("=" * 60)
    print("✅ 診斷測試完成！")
    print("=" * 60)
    print(f"\n📁 輸出位置: {output_dir}/")
    print(f"\n請檢查以下文件：")
    print(f"  1. diagnostic_comparison.png - 視覺對比圖")
    print(f"  2. diagnostic_report.txt - 詳細分析報告")
    print(f"  3. output_*.png - 各測試的輸出圖像")
    print()


if __name__ == "__main__":
    main()
