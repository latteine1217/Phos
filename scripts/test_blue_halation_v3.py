"""
藍光 Halation 視覺測試腳本
測試 Mie v3 藍光增強是否過強

Background:
- TASK-010 使用 Palik (1985) 折射率數據生成 Mie v3 查表
- 結果: η_blue ↑20.8× (0.067 → 1.387)
- 理論預測: η_b/η_r = 1.7× (仍在合理範圍)
- 風險: 實際圖像中藍光外環可能視覺過強

Test Strategy:
1. 生成 3 個測試場景（點光源、藍天、純藍高光）
2. 使用 CineStill800T_MediumPhysics 處理（最強 Halation）
3. 測量 B/R 半徑比例、外環強度比
4. 驗收標準: B/R < 2.0×, 外環比 < 1.5×

Date: 2025-12-24
Task: TASK-013 Phase 1
"""

import sys
from pathlib import Path
from typing import Dict, Any

import numpy as np

try:
    import cv2  # type: ignore
except ImportError:
    print("錯誤: 需要安裝 opencv-python")
    print("請執行: pip install opencv-python")
    sys.exit(1)

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from film_models import create_film_profiles, FilmProfile  # type: ignore
from Phos import spectral_response, optical_processing, standardize  # type: ignore


def generate_test_scenes() -> Dict[str, Any]:
    """
    生成測試場景
    
    Returns:
        場景字典 {scene_name: image_bgr}
    """
    scenes: Dict[str, Any] = {}
    
    # 場景 1: 點光源 (白色) - 測試整體 Halation 行為
    print("生成場景 1: 點光源...")
    point_light = np.zeros((512, 512, 3), dtype=np.uint8)
    center = 256
    # 創建小尺寸高光點（20x20 像素）
    point_light[center-10:center+10, center-10:center+10, :] = 255
    scenes['point_light_white'] = point_light
    
    # 場景 2: 藍天高光（太陽） - 真實場景測試
    print("生成場景 2: 藍天場景...")
    blue_sky = np.zeros((512, 512, 3), dtype=np.uint8)
    # 藍天背景 (BGR: 220, 180, 120 - 淺藍色)
    blue_sky[:, :, :] = [220, 180, 120]
    # 太陽高光點（20x20 像素）
    blue_sky[center-10:center+10, center-10:center+10, :] = 255
    scenes['blue_sky_sun'] = blue_sky
    
    # 場景 3: 純藍高光 - 極端情況測試
    print("生成場景 3: 純藍高光...")
    blue_highlight = np.zeros((512, 512, 3), dtype=np.uint8)
    # 純藍色高光點（20x20 像素）
    blue_highlight[center-10:center+10, center-10:center+10, 0] = 255  # B channel
    scenes['pure_blue_highlight'] = blue_highlight
    
    # 場景 4: 白色高光陣列 - 測試多點 Halation 交互
    print("生成場景 4: 高光陣列...")
    grid = np.zeros((512, 512, 3), dtype=np.uint8)
    positions = [(128, 128), (128, 384), (384, 128), (384, 384), (256, 256)]
    for (cy, cx) in positions:
        grid[cy-8:cy+8, cx-8:cx+8, :] = 255
    scenes['highlight_grid'] = grid
    
    return scenes


def measure_halo_metrics(img: Any, scene_name: str) -> Dict[str, Any]:
    """
    測量 Halation 指標
    
    測量方法:
    - 藍光/紅光半徑: 50% 峰值強度的徑向距離
    - B/R 比例: blue_radius / red_radius
    - 外環強度比: 外環區域的平均 B/R 強度比
    
    Args:
        img: 輸出圖像 (BGR, uint8)
        scene_name: 場景名稱
        
    Returns:
        metrics 字典
    """
    h, w = img.shape[:2]
    center_y, center_x = h // 2, w // 2
    
    # 轉換為 float32
    b, g, r = cv2.split(img.astype(np.float32))
    
    # 計算半徑（50% 強度點）
    def find_radius(channel: Any, threshold: float = 0.5) -> float:
        """找到指定強度閾值的徑向半徑"""
        peak = float(channel[center_y, center_x])
        if peak < 10.0:
            return 0.0
        
        target_value = peak * threshold
        
        # 沿 8 個方向搜尋
        for radius in range(1, min(h, w) // 2):
            ring_values = []
            for angle in np.linspace(0, 2*np.pi, 8, endpoint=False):
                y = int(center_y + radius * np.sin(angle))
                x = int(center_x + radius * np.cos(angle))
                if 0 <= y < h and 0 <= x < w:
                    ring_values.append(float(channel[y, x]))
            
            # 如果平均值低於閾值，返回半徑
            if len(ring_values) > 0 and np.mean(ring_values) < target_value:
                return float(radius)
        
        return float(min(h, w) // 2)
    
    blue_radius = find_radius(b)
    red_radius = find_radius(r)
    green_radius = find_radius(g)
    
    # 計算外環強度比例（在 80% 的最大半徑處測量）
    max_radius = max(blue_radius, red_radius)
    outer_r = int(max_radius * 0.8)
    
    if outer_r > 10 and outer_r < min(h, w) // 2:
        # 創建外環遮罩（環形區域）
        y_grid, x_grid = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((y_grid - center_y)**2 + (x_grid - center_x)**2)
        outer_mask = (dist_from_center >= outer_r * 0.9) & (dist_from_center <= outer_r * 1.1)
        
        if np.sum(outer_mask) > 0:
            outer_blue = float(np.mean(b[outer_mask]))
            outer_red = float(np.mean(r[outer_mask]))
            outer_ratio = outer_blue / outer_red if outer_red > 1.0 else 0.0
        else:
            outer_ratio = 0.0
    else:
        outer_ratio = 0.0
    
    # 計算峰值強度
    peak_blue = float(b[center_y, center_x])
    peak_red = float(r[center_y, center_x])
    peak_green = float(g[center_y, center_x])
    
    return {
        'scene': scene_name,
        'blue_radius': blue_radius,
        'red_radius': red_radius,
        'green_radius': green_radius,
        'blue_to_red_ratio': blue_radius / red_radius if red_radius > 0 else 0.0,
        'outer_intensity_ratio': outer_ratio,
        'peak_blue': peak_blue,
        'peak_red': peak_red,
        'peak_green': peak_green
    }


def process_with_film(input_img: Any, film: FilmProfile) -> Any:
    """
    使用指定膠片處理圖像
    
    Args:
        input_img: 輸入圖像 (BGR, uint8)
        film: 膠片配置
        
    Returns:
        處理後圖像 (BGR, uint8)
    """
    # 標準化尺寸
    img = standardize(input_img)
    
    # 計算光譜響應
    response_r, response_g, response_b, response_total = spectral_response(img, film)
    
    # 應用光學處理
    output = optical_processing(
        response_r, response_g, response_b, response_total,
        film, 
        grain_style='off',  # 關閉顆粒以專注於 Halation
        tone_style='filmic',
        use_film_spectra=False,
        film_spectra_name='Portra400'
    )
    
    return output


def main() -> None:
    print("=" * 80)
    print("藍光 Halation 視覺測試 (Mie v3)")
    print("=" * 80)
    print()
    print("測試目標: 驗證 TASK-010 Mie v3 藍光增強 (20.8×) 是否視覺過強")
    print("膠片: CineStill800T_MediumPhysics (最強 Halation)")
    print()
    
    # 載入膠片配置
    print("載入膠片配置...")
    films = create_film_profiles()
    cinestill = films.get('Cinestill800T_MediumPhysics')
    
    if cinestill is None:
        print("❌ 錯誤: 找不到 Cinestill800T_MediumPhysics 配置")
        print("可用配置:", list(films.keys()))
        return
    
    print(f"✅ 已載入: {cinestill.name}")
    print(f"   Halation 啟用: {cinestill.halation_params.enabled}")
    print(f"   Wavelength Bloom 啟用: {cinestill.wavelength_bloom_params.enabled}")
    print()
    
    # 生成測試場景
    print("生成測試場景...")
    scenes = generate_test_scenes()
    print(f"✅ 生成 {len(scenes)} 個場景")
    print()
    
    # 創建輸出目錄
    output_dir = Path('test_outputs/blue_halation_v3')
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"輸出目錄: {output_dir}")
    print()
    
    # 處理每個場景
    results = []
    
    for scene_name, input_img in scenes.items():
        print("-" * 80)
        print(f"測試場景: {scene_name}")
        print("-" * 80)
        
        # 儲存輸入
        input_path = output_dir / f'{scene_name}_input.png'
        cv2.imwrite(str(input_path), input_img)
        print(f"✅ 輸入已保存: {input_path.name}")
        
        # 處理圖像
        print("處理中...")
        output_img = process_with_film(input_img, cinestill)
        
        # 儲存輸出
        output_path = output_dir / f'{scene_name}_output.png'
        cv2.imwrite(str(output_path), output_img)
        print(f"✅ 輸出已保存: {output_path.name}")
        
        # 測量指標
        metrics = measure_halo_metrics(output_img, scene_name)
        results.append(metrics)
        
        # 顯示指標
        print()
        print(f"指標:")
        print(f"  藍光半徑: {metrics['blue_radius']:.1f} px")
        print(f"  紅光半徑: {metrics['red_radius']:.1f} px")
        print(f"  綠光半徑: {metrics['green_radius']:.1f} px")
        print(f"  B/R 半徑比例: {metrics['blue_to_red_ratio']:.2f}")
        print(f"  外環強度比 (B/R): {metrics['outer_intensity_ratio']:.2f}")
        print(f"  峰值 B/G/R: {metrics['peak_blue']:.0f} / {metrics['peak_green']:.0f} / {metrics['peak_red']:.0f}")
        print()
    
    # 驗收檢查
    print("=" * 80)
    print("驗收檢查")
    print("=" * 80)
    print()
    
    # 計算平均值（排除零值）
    valid_br_ratios = [float(r['blue_to_red_ratio']) for r in results if float(r['blue_to_red_ratio']) > 0]
    valid_outer_ratios = [float(r['outer_intensity_ratio']) for r in results if float(r['outer_intensity_ratio']) > 0]
    
    if len(valid_br_ratios) > 0:
        avg_br_ratio = float(np.mean(valid_br_ratios))
        max_br_ratio = float(np.max(valid_br_ratios))
        min_br_ratio = float(np.min(valid_br_ratios))
    else:
        avg_br_ratio = 0.0
        max_br_ratio = 0.0
        min_br_ratio = 0.0
    
    if len(valid_outer_ratios) > 0:
        avg_outer_ratio = float(np.mean(valid_outer_ratios))
        max_outer_ratio = float(np.max(valid_outer_ratios))
    else:
        avg_outer_ratio = 0.0
        max_outer_ratio = 0.0
    
    # 顯示統計
    print(f"B/R 半徑比例:")
    print(f"  平均: {avg_br_ratio:.2f}")
    print(f"  最大: {max_br_ratio:.2f}")
    print(f"  最小: {min_br_ratio:.2f}")
    print(f"  驗收標準: < 2.0× {'✅ 通過' if avg_br_ratio < 2.0 else '❌ 未通過'}")
    print()
    
    print(f"外環強度比:")
    print(f"  平均: {avg_outer_ratio:.2f}")
    print(f"  最大: {max_outer_ratio:.2f}")
    print(f"  驗收標準: < 1.5× {'✅ 通過' if avg_outer_ratio < 1.5 else '❌ 未通過'}")
    print()
    
    # 綜合判定
    print("=" * 80)
    print("綜合判定")
    print("=" * 80)
    print()
    
    br_pass = avg_br_ratio < 2.0
    outer_pass = avg_outer_ratio < 1.5
    
    if br_pass and outer_pass:
        print("✅ 測試通過: 藍光 Halation 在合理範圍內")
        print()
        print("結論:")
        print("- Mie v3 藍光增強 (20.8×) 並未導致視覺過強")
        print("- 無需調整 mie_intensity 參數")
        print("- 可以保持當前配置")
    else:
        print("❌ 測試未通過: 藍光 Halation 可能過強")
        print()
        print("建議:")
        print("1. 降低 mie_intensity: 0.7 → 0.5")
        print("   位置: film_models.py, Line ~1700 (CineStill 配置)")
        print()
        print("2. 或調整 wavelength_bloom_params.core_fraction_b")
        print("   從 0.80 增加到 0.85 (減少藍光擴散範圍)")
        print()
        print("3. 重新執行此測試驗證調整效果")
    
    print()
    print("=" * 80)
    print(f"📁 所有輸出已保存至: {output_dir.absolute()}")
    print("=" * 80)
    print()
    print("下一步:")
    print("1. 檢視輸出圖像進行視覺評估")
    print("2. 如需調整參數，修改後重新測試")
    print("3. 更新 tasks/TASK-013-fix-known-issues/ 完成報告")
    print()


if __name__ == '__main__':
    main()
