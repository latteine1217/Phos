#!/usr/bin/env python3
"""
完整效能基準測試腳本
測試多種解析度、膠片模式，生成 JSON 格式結果
"""

import numpy as np
import cv2
import time
import json
from pathlib import Path
import sys
from datetime import datetime

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from film_models import create_film_profiles, PhysicsMode


def create_test_image(size=(2000, 3000)):
    """
    創建標準測試影像
    - 高光：模擬路燈、霓虹燈
    - 中間調：一般場景
    - 陰影：暗部
    """
    img = np.zeros((*size, 3), dtype=np.float32)
    
    # 背景（中間調 0.3）
    img[:, :] = 0.3
    
    # 添加高光區域（10個圓形路燈）
    for i in range(2):
        for j in range(5):
            cx = 300 + j * (size[1] // 6)
            cy = 300 + i * (size[0] // 2 - 200)
            y, x = np.ogrid[:size[0], :size[1]]
            mask = ((x - cx)**2 + (y - cy)**2) <= 30**2
            img[mask] = [0.95, 0.90, 0.85]  # 暖色高光
    
    return img


def benchmark_function(func, *args, repeat=3, **kwargs):
    """
    測量函數執行時間（重複測試取平均）
    
    Returns:
        (平均時間, 標準差, 結果)
    """
    times = []
    result = None
    for _ in range(repeat):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    return np.mean(times), np.std(times), result


def profile_pipeline_stages(film, image_size=(2000, 3000)):
    """
    測量各階段執行時間
    
    Returns:
        dict: 各階段耗時統計
    """
    # 創建測試影像
    img_rgb = create_test_image(image_size)
    # 分離通道
    b = img_rgb[:, :, 2]
    g = img_rgb[:, :, 1]
    r = img_rgb[:, :, 0]
    
    stages = {}
    
    # Stage 1: 光譜響應計算
    def spectral_response_stage():
        response_r = 0.32*r + 0.12*g + 0.06*b
        response_g = 0.09*r + 0.45*g + 0.12*b
        response_b = 0.06*r + 0.12*g + 0.77*b
        return response_r, response_g, response_b
    
    t_spectral, std_spectral, (resp_r, resp_g, resp_b) = benchmark_function(spectral_response_stage)
    stages['spectral_response'] = {
        'time_ms': t_spectral * 1000,
        'std_ms': std_spectral * 1000
    }
    
    # Stage 2: Bloom 散射
    if film.physics_mode == PhysicsMode.PHYSICAL:
        def bloom_stage():
            threshold = 0.7
            highlight_r = np.maximum(resp_r - threshold, 0)
            highlight_g = np.maximum(resp_g - threshold, 0)
            highlight_b = np.maximum(resp_b - threshold, 0)
            
            sigma = 20
            ksize = int(sigma * 6) | 1
            bloom_r = cv2.GaussianBlur(highlight_r * 0.08, (ksize, ksize), sigma)
            bloom_g = cv2.GaussianBlur(highlight_g * 0.08, (ksize, ksize), sigma)
            bloom_b = cv2.GaussianBlur(highlight_b * 0.08, (ksize, ksize), sigma)
            
            return bloom_r, bloom_g, bloom_b
        
        t_bloom, std_bloom, _ = benchmark_function(bloom_stage)
        stages['bloom'] = {
            'time_ms': t_bloom * 1000,
            'std_ms': std_bloom * 1000
        }
    else:
        stages['bloom'] = {'time_ms': 0, 'std_ms': 0}
    
    # Stage 3: Halation 背層反射
    if hasattr(film, 'halation_params') and film.halation_params.enabled:
        def halation_stage():
            threshold = 0.5
            highlight = np.maximum(resp_r - threshold, 0)
            
            sigma_base = 20
            ksize = 201
            
            kernel_small = cv2.getGaussianKernel(ksize // 3, sigma_base)
            kernel_small = kernel_small @ kernel_small.T
            
            kernel_medium = cv2.getGaussianKernel(ksize, sigma_base * 2)
            kernel_medium = kernel_medium @ kernel_medium.T
            
            kernel_large = cv2.getGaussianKernel(ksize, sigma_base * 4)
            kernel_large = kernel_large @ kernel_large.T
            
            hal_1 = cv2.filter2D(highlight, -1, kernel_small, borderType=cv2.BORDER_REFLECT)
            hal_2 = cv2.filter2D(highlight, -1, kernel_medium, borderType=cv2.BORDER_REFLECT)
            hal_3 = cv2.filter2D(highlight, -1, kernel_large, borderType=cv2.BORDER_REFLECT)
            
            halation = 0.5 * hal_1 + 0.3 * hal_2 + 0.2 * hal_3
            
            return halation
        
        t_halation, std_halation, _ = benchmark_function(halation_stage)
        stages['halation'] = {
            'time_ms': t_halation * 1000,
            'std_ms': std_halation * 1000
        }
    else:
        stages['halation'] = {'time_ms': 0, 'std_ms': 0}
    
    # Stage 4: H&D 曲線
    def hd_curve_stage():
        exposure = np.clip(resp_r, 1e-10, None)
        density = 0.65 * np.log10(exposure) + 0.3
        transmittance = 10**(-density)
        return transmittance
    
    t_hd, std_hd, _ = benchmark_function(hd_curve_stage)
    stages['hd_curve'] = {
        'time_ms': t_hd * 1000,
        'std_ms': std_hd * 1000
    }
    
    # Stage 5: 顆粒噪聲
    def grain_stage():
        grain = np.random.normal(0, 0.1, resp_r.shape).astype(np.float32)
        grain_blurred = cv2.GaussianBlur(grain, (5, 5), 1.5)
        return grain_blurred
    
    t_grain, std_grain, _ = benchmark_function(grain_stage)
    stages['grain'] = {
        'time_ms': t_grain * 1000,
        'std_ms': std_grain * 1000
    }
    
    # Stage 6: Tone Mapping
    def tone_mapping_stage():
        result = resp_r ** (1/2.2)
        result = np.clip(result, 0, 1)
        return result
    
    t_tone, std_tone, _ = benchmark_function(tone_mapping_stage)
    stages['tone_mapping'] = {
        'time_ms': t_tone * 1000,
        'std_ms': std_tone * 1000
    }
    
    # 計算總時間
    total_time = sum(stage['time_ms'] for stage in stages.values())
    
    return stages, total_time


def run_benchmark_suite():
    """
    執行完整基準測試套件
    """
    print("=" * 80)
    print("  Phos v0.4.1 效能基準測試")
    print("=" * 80)
    print(f"  測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 載入膠片配置
    films = create_film_profiles()
    
    # 測試配置
    test_configs = [
        # 格式: (膠片名稱, 解析度, 描述)
        ("Portra400", (512, 512), "Artistic mode, 低解析度"),
        ("Portra400", (1024, 1024), "Artistic mode, 中解析度"),
        ("Portra400", (2048, 2048), "Artistic mode, 高解析度"),
        ("Portra400_MediumPhysics_Mie", (512, 512), "Physics+Mie, 低解析度"),
        ("Portra400_MediumPhysics_Mie", (1024, 1024), "Physics+Mie, 中解析度"),
        ("Portra400_MediumPhysics_Mie", (2048, 2048), "Physics+Mie, 高解析度"),
        ("Cinestill800T_MediumPhysics", (1024, 1024), "CineStill (強 Halation)"),
        ("Cinestill800T_Mie", (2048, 2048), "CineStill+Mie (最複雜)"),
    ]
    
    results = {
        'metadata': {
            'version': 'v0.4.1',
            'timestamp': datetime.now().isoformat(),
            'test_date': datetime.now().strftime('%Y-%m-%d'),
            'platform': sys.platform,
        },
        'benchmarks': []
    }
    
    # 執行測試
    for film_name, size, description in test_configs:
        print(f"\n{'─' * 80}")
        print(f"測試: {description}")
        print(f"膠片: {film_name}, 解析度: {size[0]}×{size[1]}")
        print(f"{'─' * 80}")
        
        try:
            film = films[film_name]
            stages, total_time = profile_pipeline_stages(film, size)
            
            # 計算每百萬像素時間
            megapixels = (size[0] * size[1]) / 1e6
            time_per_megapixel = total_time / megapixels
            
            # 顯示結果
            print(f"\n階段耗時:")
            for stage_name, stats in stages.items():
                if stats['time_ms'] > 0:
                    percentage = (stats['time_ms'] / total_time) * 100
                    print(f"  {stage_name:20s}: {stats['time_ms']:6.1f} ± {stats['std_ms']:4.1f} ms  ({percentage:4.1f}%)")
            
            print(f"\n總時間: {total_time:.1f} ms ({total_time/1000:.2f} s)")
            print(f"百萬像素時間: {time_per_megapixel:.1f} ms/MP")
            
            # 判斷是否達標
            if time_per_megapixel < 100:
                status = "✅ 優秀"
            elif time_per_megapixel < 300:
                status = "✅ 良好"
            elif time_per_megapixel < 500:
                status = "⚠️  可接受"
            else:
                status = "❌ 需優化"
            print(f"效能評級: {status}")
            
            # 儲存結果
            results['benchmarks'].append({
                'film_name': film_name,
                'description': description,
                'resolution': {'width': size[1], 'height': size[0]},
                'megapixels': megapixels,
                'physics_mode': film.physics_mode.value,
                'halation_enabled': hasattr(film, 'halation_params') and film.halation_params.enabled,
                'stages': stages,
                'total_time_ms': total_time,
                'time_per_megapixel_ms': time_per_megapixel,
                'status': status
            })
            
        except Exception as e:
            print(f"  ❌ 測試失敗: {e}")
            import traceback
            traceback.print_exc()
    
    # 儲存 JSON 結果
    output_path = Path(__file__).parent.parent / 'test_outputs' / 'performance_baseline_v041.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print(f"✅ 基準測試完成")
    print(f"📁 結果已儲存: {output_path}")
    print("=" * 80)
    
    # 生成摘要
    print("\n" + "=" * 80)
    print("  效能摘要")
    print("=" * 80)
    
    artistic_benchmarks = [b for b in results['benchmarks'] if 'Artistic' in b['description']]
    physics_benchmarks = [b for b in results['benchmarks'] if 'Physics' in b['description']]
    
    avg_artistic = None
    avg_physics = None
    
    if artistic_benchmarks:
        avg_artistic = np.mean([b['time_per_megapixel_ms'] for b in artistic_benchmarks])
        print(f"\nArtistic Mode 平均: {avg_artistic:.1f} ms/MP")
    
    if physics_benchmarks:
        avg_physics = np.mean([b['time_per_megapixel_ms'] for b in physics_benchmarks])
        print(f"Physics Mode 平均: {avg_physics:.1f} ms/MP")
        
        if avg_artistic is not None:
            overhead = ((avg_physics - avg_artistic) / avg_artistic) * 100
            print(f"Physics 模式開銷: +{overhead:.1f}%")
    
    # 瓶頸分析
    print(f"\n主要瓶頸:")
    all_stages = {}
    for benchmark in results['benchmarks']:
        for stage_name, stats in benchmark['stages'].items():
            if stage_name not in all_stages:
                all_stages[stage_name] = []
            all_stages[stage_name].append(stats['time_ms'])
    
    stage_avgs = {name: np.mean(times) for name, times in all_stages.items() if np.mean(times) > 0}
    sorted_stages = sorted(stage_avgs.items(), key=lambda x: x[1], reverse=True)
    
    for stage_name, avg_time in sorted_stages[:3]:
        print(f"  {stage_name:20s}: {avg_time:6.1f} ms (平均)")
    
    return results


if __name__ == "__main__":
    results = run_benchmark_suite()
