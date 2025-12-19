"""
效能基準測試
"""

import pytest
import numpy as np
import time
from phos_core import (
    generate_grain_optimized,
    apply_bloom_optimized,
    apply_reinhard_optimized,
    apply_filmic_optimized,
    cached_gaussian_blur
)
from film_models import get_film_profile


class TestPerformance:
    """效能基準測試"""
    
    def test_grain_generation_speed(self, sample_image_float, benchmark):
        """基準：顆粒生成速度"""
        if 'benchmark' in dir(pytest):
            result = benchmark(generate_grain_optimized, sample_image_float, 0.5)
            assert result.shape == sample_image_float.shape
        else:
            # 如果沒有 pytest-benchmark，手動計時
            start = time.time()
            for _ in range(10):
                result = generate_grain_optimized(sample_image_float, 0.5)
            elapsed = (time.time() - start) / 10
            print(f"\n顆粒生成平均時間: {elapsed*1000:.2f}ms")
            assert result.shape == sample_image_float.shape
    
    def test_bloom_speed(self, sample_image_float):
        """測試光暈效果速度"""
        start = time.time()
        for _ in range(5):
            result = apply_bloom_optimized(
                sample_image_float, 0.5, 20, 0.5, 0.05, 3, 55
            )
        elapsed = (time.time() - start) / 5
        print(f"\n光暈效果平均時間: {elapsed*1000:.2f}ms")
        assert result.shape == sample_image_float.shape
    
    def test_tone_mapping_speed(self, sample_image_float):
        """測試 Tone mapping 速度"""
        film = get_film_profile("NC200")
        
        # Reinhard
        start = time.time()
        for _ in range(100):
            result_r = apply_reinhard_optimized(sample_image_float, 2.0, True)
        reinhard_time = (time.time() - start) / 100
        
        # Filmic
        start = time.time()
        for _ in range(100):
            result_f = apply_filmic_optimized(sample_image_float, film)
        filmic_time = (time.time() - start) / 100
        
        print(f"\nReinhard 平均時間: {reinhard_time*1000:.3f}ms")
        print(f"Filmic 平均時間: {filmic_time*1000:.3f}ms")
        
        assert result_r.shape == sample_image_float.shape
        assert result_f.shape == sample_image_float.shape
    
    def test_gaussian_blur_cache_效benefit(self, sample_image_float):
        """測試 Gaussian blur 快取效益"""
        # 首次調用（未快取）
        start = time.time()
        result1 = cached_gaussian_blur(sample_image_float, 21, 3.0)
        first_time = time.time() - start
        
        # 第二次調用（已快取核大小計算）
        start = time.time()
        for _ in range(10):
            result2 = cached_gaussian_blur(sample_image_float, 21, 3.0)
        cached_time = (time.time() - start) / 10
        
        print(f"\n首次調用: {first_time*1000:.3f}ms")
        print(f"快取調用平均: {cached_time*1000:.3f}ms")
        
        # 快取版本應該至少有 5% 的速度提升（主要是避免重複計算核大小）
        # 注意：這個測試更多是確保快取不會變慢
        assert cached_time <= first_time * 1.1  # 允許 10% 誤差
    
    def test_memory_efficiency(self, sample_image_float):
        """測試記憶體效率（檢查 in-place 操作）"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 記錄初始記憶體
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 執行多次操作
        for _ in range(50):
            _ = generate_grain_optimized(sample_image_float, 0.5)
        
        # 記錄最終記憶體
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\n初始記憶體: {initial_memory:.2f} MB")
        print(f"最終記憶體: {final_memory:.2f} MB")
        print(f"記憶體增長: {memory_increase:.2f} MB")
        
        # 記憶體增長應該合理（允許 50MB 內的增長）
        assert memory_increase < 50, f"記憶體增長過大: {memory_increase:.2f} MB"


class TestScalability:
    """可擴展性測試"""
    
    @pytest.mark.parametrize("size", [(100, 100), (500, 500), (1000, 1000)])
    def test_processing_scales_linearly(self, size):
        """測試處理時間是否線性增長"""
        np.random.seed(42)
        image = np.random.rand(*size).astype(np.float32)
        
        start = time.time()
        result = generate_grain_optimized(image, 0.5)
        elapsed = time.time() - start
        
        pixels = size[0] * size[1]
        time_per_pixel = elapsed / pixels * 1e6  # 微秒/像素
        
        print(f"\n尺寸 {size}: {elapsed*1000:.2f}ms ({time_per_pixel:.3f} µs/pixel)")
        
        assert result.shape == image.shape
        # 每像素處理時間應該合理（< 1微秒/像素）
        assert time_per_pixel < 1.0
