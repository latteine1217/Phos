"""
PR #2: Optical Core 模組測試

測試範圍：
1. 功能正確性：測試各函數邏輯未被破壞
2. 模組結構：驗證 __all__ 列表正確

Version: 0.7.0-dev (PR #2)
Date: 2026-01-12
"""

import pytest
import numpy as np
import cv2

from modules import optical_core
from modules.optical_core import standardize, spectral_response, average_response
from film_models import get_film_profile, STANDARD_IMAGE_SIZE


# ==================== 功能正確性測試 ====================

class TestStandardize:
    """測試 standardize() 函數邏輯"""
    
    def test_standardize_portrait_image(self):
        """測試豎圖（高 < 寬）標準化"""
        # 創建 2000x3000 的豎圖
        image = np.random.randint(0, 256, (2000, 3000, 3), dtype=np.uint8)
        result = standardize(image)
        
        # 短邊（高）應該被調整為 STANDARD_IMAGE_SIZE (3000)
        assert result.shape[0] == STANDARD_IMAGE_SIZE
        assert result.shape[1] == int(3000 * STANDARD_IMAGE_SIZE / 2000)
        
        # 尺寸應該是偶數
        assert result.shape[0] % 2 == 0
        assert result.shape[1] % 2 == 0
    
    def test_standardize_landscape_image(self):
        """測試橫圖（寬 < 高）標準化"""
        # 創建 3000x2000 的橫圖
        image = np.random.randint(0, 256, (3000, 2000, 3), dtype=np.uint8)
        result = standardize(image)
        
        # 短邊（寬）應該被調整為 STANDARD_IMAGE_SIZE (3000)
        assert result.shape[1] == STANDARD_IMAGE_SIZE
        assert result.shape[0] == int(3000 * STANDARD_IMAGE_SIZE / 2000)
        
        # 尺寸應該是偶數
        assert result.shape[0] % 2 == 0
        assert result.shape[1] % 2 == 0
    
    def test_standardize_square_image(self):
        """測試正方形圖像標準化"""
        image = np.random.randint(0, 256, (2000, 2000, 3), dtype=np.uint8)
        result = standardize(image)
        
        # 正方形應該保持正方形
        assert result.shape[0] == STANDARD_IMAGE_SIZE
        assert result.shape[1] == STANDARD_IMAGE_SIZE
    
    def test_standardize_preserves_aspect_ratio(self):
        """測試標準化保持寬高比"""
        image = np.random.randint(0, 256, (1000, 1500, 3), dtype=np.uint8)
        result = standardize(image)
        
        original_ratio = 1000 / 1500
        result_ratio = result.shape[0] / result.shape[1]
        
        # 寬高比誤差應該 < 1%
        assert abs(original_ratio - result_ratio) / original_ratio < 0.01


class TestSpectralResponse:
    """測試 spectral_response() 函數邏輯"""
    
    def test_spectral_response_color_film(self):
        """測試彩色膠片的光譜響應"""
        # 創建小測試圖像
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        film = get_film_profile("Portra400")
        
        response_r, response_g, response_b, response_total = spectral_response(image, film)
        
        # 彩色膠片應該有 RGB 三個通道的響應
        assert response_r is not None
        assert response_g is not None
        assert response_b is not None
        assert response_total is not None
        
        # 所有響應應該是浮點數 (0-1 範圍)
        # 注意：光譜響應可能因光譜係數組合而略超過 1.0
        assert response_r.dtype == np.float32
        assert response_r.min() >= 0
        assert response_r.max() < 1.5  # 允許一定範圍的超出
        
        # 形狀應該與輸入相同
        assert response_r.shape == (100, 100)
    
    def test_spectral_response_bw_film(self):
        """測試黑白膠片的光譜響應"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        film = get_film_profile("HP5Plus400")  # 黑白膠片
        
        response_r, response_g, response_b, response_total = spectral_response(image, film)
        
        # 黑白膠片只有 total 通道
        assert response_r is None
        assert response_g is None
        assert response_b is None
        assert response_total is not None
        
        # Total 響應應該在 0-1 範圍
        assert response_total.dtype == np.float32
        assert 0 <= response_total.min() <= response_total.max() <= 1
    
    def test_spectral_response_pure_white(self):
        """測試純白圖像的響應"""
        image = np.full((100, 100, 3), 255, dtype=np.uint8)
        film = get_film_profile("Portra400")
        
        response_r, response_g, response_b, response_total = spectral_response(image, film)
        
        # 純白應該產生接近 1.0 的響應（取決於光譜係數）
        assert response_total.mean() > 0.8
    
    def test_spectral_response_pure_black(self):
        """測試純黑圖像的響應"""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        film = get_film_profile("Portra400")
        
        response_r, response_g, response_b, response_total = spectral_response(image, film)
        
        # 純黑應該產生接近 0.0 的響應
        assert response_total.max() < 0.01


class TestAverageResponse:
    """測試 average_response() 函數邏輯"""
    
    def test_average_response_uniform_image(self):
        """測試均勻響應圖像的平均值"""
        response_total = np.full((100, 100), 0.5, dtype=np.float32)
        avg = average_response(response_total)
        
        assert isinstance(avg, (float, np.floating))
        assert abs(avg - 0.5) < 0.001
    
    def test_average_response_clipping(self):
        """測試平均響應的裁剪 (0-1)"""
        # 創建超出範圍的響應（不應該發生，但測試防禦性編程）
        response_total = np.array([[1.5, 2.0], [-0.5, 0.5]], dtype=np.float32)
        avg = average_response(response_total)
        
        # 結果應該被裁剪到 0-1 範圍
        assert 0 <= avg <= 1
    
    def test_average_response_all_black(self):
        """測試全黑響應的平均值"""
        response_total = np.zeros((100, 100), dtype=np.float32)
        avg = average_response(response_total)
        
        assert avg == 0.0
    
    def test_average_response_all_white(self):
        """測試全白響應的平均值"""
        response_total = np.ones((100, 100), dtype=np.float32)
        avg = average_response(response_total)
        
        assert avg == 1.0


# ==================== 模組結構測試 ====================

class TestModuleStructure:
    """測試模組結構與 __all__ 列表"""
    
    def test_optical_core_has_all_list(self):
        """optical_core 應該有 __all__ 列表"""
        assert hasattr(optical_core, '__all__')
        assert isinstance(optical_core.__all__, list)
    
    def test_all_list_contains_three_functions(self):
        """__all__ 應該包含 3 個函數"""
        assert len(optical_core.__all__) == 3
        assert 'standardize' in optical_core.__all__
        assert 'spectral_response' in optical_core.__all__
        assert 'average_response' in optical_core.__all__
    
    def test_all_functions_importable(self):
        """__all__ 中的函數都應該可導入"""
        for func_name in optical_core.__all__:
            assert hasattr(optical_core, func_name)
            func = getattr(optical_core, func_name)
            assert callable(func)
    
    def test_module_has_docstring(self):
        """模組應該有文檔字串"""
        assert optical_core.__doc__ is not None
        assert len(optical_core.__doc__) > 50


# ==================== 集成測試 ====================

class TestIntegration:
    """測試函數之間的集成"""
    
    def test_full_optical_core_pipeline(self):
        """測試完整的光學核心流程"""
        # 1. 創建測試圖像
        image = np.random.randint(100, 200, (1000, 1500, 3), dtype=np.uint8)
        
        # 2. 標準化
        standardized = standardize(image)
        assert standardized.shape[0] == STANDARD_IMAGE_SIZE or standardized.shape[1] == STANDARD_IMAGE_SIZE
        
        # 3. 計算光譜響應
        film = get_film_profile("Portra400")
        response_r, response_g, response_b, response_total = spectral_response(standardized, film)
        
        # 4. 計算平均響應
        avg = average_response(response_total)
        
        # 驗證流程完整性
        assert 0 <= avg <= 1
        assert response_r is not None
        assert response_g is not None
        assert response_b is not None


# ==================== PR #2 完成檢查清單 ====================

class TestPR2Completion:
    """PR #2 完成狀態檢查"""
    
    def test_pr2_checklist(self):
        """驗證 PR #2 的所有要求"""
        # ✅ 1. 3 個函數已從 Phos.py 搬移至 modules/optical_core.py
        assert hasattr(optical_core, 'standardize')
        assert hasattr(optical_core, 'spectral_response')
        assert hasattr(optical_core, 'average_response')
        
        # ✅ 2. modules/__init__.py 已更新 __all__
        from modules import __all__ as modules_all
        assert 'standardize' in modules_all
        assert 'spectral_response' in modules_all
        assert 'average_response' in modules_all
        
        # ✅ 3. 功能測試已完成
        # （由上述測試覆蓋）
        
        print("✅ PR #2 完成檢查清單通過！")
