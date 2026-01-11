"""
PR #3: Tone Mapping 模組測試

測試範圍：
1. 功能正確性：測試 Reinhard 和 Filmic tone mapping 算法
2. 模組結構：驗證 __all__ 列表正確

Version: 0.7.0-dev (PR #3)
Date: 2026-01-12
"""

import pytest
import numpy as np

from modules import tone_mapping
from modules.tone_mapping import (
    apply_reinhard_to_channel,
    apply_reinhard,
    apply_filmic_to_channel,
    apply_filmic
)
from film_models import get_film_profile


# ==================== Reinhard Tone Mapping 測試 ====================

class TestReinhardToChannel:
    """測試 apply_reinhard_to_channel() 函數"""
    
    def test_reinhard_output_range(self):
        """測試 Reinhard 輸出範圍在 0-1"""
        lux = np.random.rand(100, 100).astype(np.float32) * 10  # 0-10 HDR 範圍
        result = apply_reinhard_to_channel(lux, gamma=2.2, color_mode=False)
        
        assert result.min() >= 0.0
        assert result.max() <= 1.0
    
    def test_reinhard_black_input(self):
        """測試純黑輸入"""
        lux = np.zeros((100, 100), dtype=np.float32)
        result = apply_reinhard_to_channel(lux, gamma=2.2, color_mode=False)
        
        assert np.allclose(result, 0.0)
    
    def test_reinhard_monotonic(self):
        """測試 Reinhard 單調遞增性質"""
        lux1 = np.array([[0.5]], dtype=np.float32)
        lux2 = np.array([[1.0]], dtype=np.float32)
        
        result1 = apply_reinhard_to_channel(lux1, gamma=2.2, color_mode=False)
        result2 = apply_reinhard_to_channel(lux2, gamma=2.2, color_mode=False)
        
        assert result2 > result1  # 更亮的輸入應該產生更亮的輸出
    
    def test_reinhard_color_mode_effect(self):
        """測試彩色模式對 gamma 的影響"""
        lux = np.ones((100, 100), dtype=np.float32)
        
        result_bw = apply_reinhard_to_channel(lux, gamma=2.2, color_mode=False)
        result_color = apply_reinhard_to_channel(lux, gamma=2.2, color_mode=True)
        
        # 彩色模式會應用 REINHARD_GAMMA_ADJUSTMENT，結果應該不同
        assert not np.allclose(result_bw, result_color)


class TestReinhard:
    """測試 apply_reinhard() 函數"""
    
    def test_reinhard_color_film(self):
        """測試彩色膠片的 Reinhard tone mapping"""
        film = get_film_profile("Portra400")
        
        # 創建測試數據
        response_r = np.random.rand(100, 100).astype(np.float32)
        response_g = np.random.rand(100, 100).astype(np.float32)
        response_b = np.random.rand(100, 100).astype(np.float32)
        response_total = (response_r + response_g + response_b) / 3.0
        
        result_r, result_g, result_b, result_total = apply_reinhard(
            response_r, response_g, response_b, response_total, film
        )
        
        # 彩色膠片應該返回 RGB 通道
        assert result_r is not None
        assert result_g is not None
        assert result_b is not None
        assert result_total is None
        
        # 所有通道應該在 0-1 範圍
        assert result_r.min() >= 0 and result_r.max() <= 1
        assert result_g.min() >= 0 and result_g.max() <= 1
        assert result_b.min() >= 0 and result_b.max() <= 1
    
    def test_reinhard_bw_film(self):
        """測試黑白膠片的 Reinhard tone mapping"""
        film = get_film_profile("HP5Plus400")
        
        response_total = np.random.rand(100, 100).astype(np.float32)
        
        result_r, result_g, result_b, result_total_out = apply_reinhard(
            None, None, None, response_total, film
        )
        
        # 黑白膠片只返回 total 通道
        assert result_r is None
        assert result_g is None
        assert result_b is None
        assert result_total_out is not None
        
        assert result_total_out.min() >= 0 and result_total_out.max() <= 1


# ==================== Filmic Tone Mapping 測試 ====================

class TestFilmicToChannel:
    """測試 apply_filmic_to_channel() 函數"""
    
    def test_filmic_output_range(self):
        """測試 Filmic 輸出範圍合理"""
        lux = np.random.rand(100, 100).astype(np.float32) * 10
        film = get_film_profile("Portra400")
        
        result = apply_filmic_to_channel(lux, film)
        
        # Filmic 可能超過 1.0，但應該在合理範圍
        assert result.min() >= -0.5  # 允許一些負值（toe 部分）
        assert result.max() < 2.0    # 不應該太大
    
    def test_filmic_black_input(self):
        """測試純黑輸入"""
        lux = np.zeros((100, 100), dtype=np.float32)
        film = get_film_profile("Portra400")
        
        result = apply_filmic_to_channel(lux, film)
        
        # 純黑應該產生接近 0 或負值（toe 部分）
        assert result.max() < 0.1
    
    def test_filmic_monotonic(self):
        """測試 Filmic 單調遞增性質"""
        film = get_film_profile("Portra400")
        
        lux1 = np.array([[0.5]], dtype=np.float32)
        lux2 = np.array([[1.0]], dtype=np.float32)
        
        result1 = apply_filmic_to_channel(lux1, film)
        result2 = apply_filmic_to_channel(lux2, film)
        
        assert result2 > result1
    
    def test_filmic_no_divide_by_zero(self):
        """測試避免除零錯誤"""
        lux = np.array([[0.0, 1.0, 100.0]], dtype=np.float32)
        film = get_film_profile("Portra400")
        
        # 不應該產生 NaN 或 inf
        result = apply_filmic_to_channel(lux, film)
        assert not np.any(np.isnan(result))
        assert not np.any(np.isinf(result))


class TestFilmic:
    """測試 apply_filmic() 函數"""
    
    def test_filmic_color_film(self):
        """測試彩色膠片的 Filmic tone mapping"""
        film = get_film_profile("Portra400")
        
        response_r = np.random.rand(100, 100).astype(np.float32)
        response_g = np.random.rand(100, 100).astype(np.float32)
        response_b = np.random.rand(100, 100).astype(np.float32)
        response_total = (response_r + response_g + response_b) / 3.0
        
        result_r, result_g, result_b, result_total = apply_filmic(
            response_r, response_g, response_b, response_total, film
        )
        
        # 彩色膠片應該返回 RGB 通道
        assert result_r is not None
        assert result_g is not None
        assert result_b is not None
        assert result_total is None
    
    def test_filmic_bw_film(self):
        """測試黑白膠片的 Filmic tone mapping"""
        film = get_film_profile("HP5Plus400")
        
        response_total = np.random.rand(100, 100).astype(np.float32)
        
        result_r, result_g, result_b, result_total_out = apply_filmic(
            None, None, None, response_total, film
        )
        
        # 黑白膠片只返回 total 通道
        assert result_r is None
        assert result_g is None
        assert result_b is None
        assert result_total_out is not None


# ==================== 比較測試 ====================

class TestReinhardVsFilmic:
    """比較 Reinhard 和 Filmic 的行為"""
    
    def test_different_algorithms(self):
        """測試兩種算法產生不同結果"""
        film = get_film_profile("Portra400")
        response_total = np.random.rand(100, 100).astype(np.float32) * 2
        
        _, _, _, reinhard_result = apply_reinhard(None, None, None, response_total, film)
        _, _, _, filmic_result = apply_filmic(None, None, None, response_total, film)
        
        # 兩種算法應該產生不同的結果
        assert not np.allclose(reinhard_result, filmic_result)
    
    def test_both_preserve_relative_order(self):
        """測試兩種算法都保持相對順序"""
        film = get_film_profile("Portra400")
        
        # 創建從暗到亮的梯度
        response_total = np.linspace(0, 1, 100).reshape(10, 10).astype(np.float32)
        
        _, _, _, reinhard_result = apply_reinhard(None, None, None, response_total, film)
        _, _, _, filmic_result = apply_filmic(None, None, None, response_total, film)
        
        # 檢查單調性：後面的像素應該更亮
        assert np.all(np.diff(reinhard_result.flatten()) >= -1e-6)  # 允許小誤差
        assert np.all(np.diff(filmic_result.flatten()) >= -1e-6)


# ==================== 模組結構測試 ====================

class TestModuleStructure:
    """測試模組結構與 __all__ 列表"""
    
    def test_tone_mapping_has_all_list(self):
        """tone_mapping 應該有 __all__ 列表"""
        assert hasattr(tone_mapping, '__all__')
        assert isinstance(tone_mapping.__all__, list)
    
    def test_all_list_contains_four_functions(self):
        """__all__ 應該包含 4 個函數"""
        assert len(tone_mapping.__all__) == 4
        assert 'apply_reinhard_to_channel' in tone_mapping.__all__
        assert 'apply_reinhard' in tone_mapping.__all__
        assert 'apply_filmic_to_channel' in tone_mapping.__all__
        assert 'apply_filmic' in tone_mapping.__all__
    
    def test_all_functions_importable(self):
        """__all__ 中的函數都應該可導入"""
        for func_name in tone_mapping.__all__:
            assert hasattr(tone_mapping, func_name)
            func = getattr(tone_mapping, func_name)
            assert callable(func)
    
    def test_module_has_docstring(self):
        """模組應該有文檔字串"""
        assert tone_mapping.__doc__ is not None
        assert len(tone_mapping.__doc__) > 50


# ==================== 集成測試 ====================

class TestIntegration:
    """測試完整的 tone mapping 流程"""
    
    def test_full_tone_mapping_pipeline_reinhard(self):
        """測試完整的 Reinhard tone mapping 流程"""
        film = get_film_profile("Portra400")
        
        # 模擬光譜響應數據
        response_r = np.random.rand(100, 100).astype(np.float32) * 5
        response_g = np.random.rand(100, 100).astype(np.float32) * 5
        response_b = np.random.rand(100, 100).astype(np.float32) * 5
        response_total = (response_r + response_g + response_b) / 3.0
        
        # 應用 Reinhard tone mapping
        result_r, result_g, result_b, _ = apply_reinhard(
            response_r, response_g, response_b, response_total, film
        )
        
        # 驗證結果
        assert result_r is not None
        assert result_g is not None
        assert result_b is not None
        assert result_r.shape == (100, 100)
        assert result_g.shape == (100, 100)
        assert result_b.shape == (100, 100)
    
    def test_full_tone_mapping_pipeline_filmic(self):
        """測試完整的 Filmic tone mapping 流程"""
        film = get_film_profile("Portra400")
        
        response_r = np.random.rand(100, 100).astype(np.float32) * 5
        response_g = np.random.rand(100, 100).astype(np.float32) * 5
        response_b = np.random.rand(100, 100).astype(np.float32) * 5
        response_total = (response_r + response_g + response_b) / 3.0
        
        # 應用 Filmic tone mapping
        result_r, result_g, result_b, _ = apply_filmic(
            response_r, response_g, response_b, response_total, film
        )
        
        # 驗證結果
        assert result_r is not None
        assert result_g is not None
        assert result_b is not None


# ==================== PR #3 完成檢查清單 ====================

class TestPR3Completion:
    """PR #3 完成狀態檢查"""
    
    def test_pr3_checklist(self):
        """驗證 PR #3 的所有要求"""
        # ✅ 1. 4 個函數已從 Phos.py 搬移至 modules/tone_mapping.py
        assert hasattr(tone_mapping, 'apply_reinhard_to_channel')
        assert hasattr(tone_mapping, 'apply_reinhard')
        assert hasattr(tone_mapping, 'apply_filmic_to_channel')
        assert hasattr(tone_mapping, 'apply_filmic')
        
        # ✅ 2. modules/__init__.py 已更新 __all__
        from modules import __all__ as modules_all
        assert 'apply_reinhard_to_channel' in modules_all
        assert 'apply_reinhard' in modules_all
        assert 'apply_filmic_to_channel' in modules_all
        assert 'apply_filmic' in modules_all
        
        # ✅ 3. 功能測試已完成
        # （由上述測試覆蓋）
        
        print("✅ PR #3 完成檢查清單通過！")
