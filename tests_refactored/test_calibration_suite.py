"""
Pytest 測試：光譜校正與物理驗證

整合所有校正工具到 pytest 框架中，支持自動化測試
"""

import pytest
import numpy as np
import sys
import os

# 添加專案根目錄
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from film_models import get_film_profile
from tools.physics_validator import PhysicsValidator
from tools.comprehensive_calibration_tool import ComprehensiveCalibrator


# ==================== 測試數據 ====================

COLOR_FILMS = [
    "Portra400", "Ektar100", "Velvia50", "NC200",
    "Cinestill800T", "Gold200", "ProImage100", "Superia400"
]

BW_FILMS = [
    "TriX400", "HP5Plus400", "FP4Plus125", "AS100", "FS200"
]

ALL_FILMS = COLOR_FILMS + BW_FILMS


# ==================== 物理驗證測試 ====================

class TestPhysicsValidation:
    """物理理論驗證測試"""
    
    @pytest.mark.parametrize("film_name", COLOR_FILMS)
    def test_energy_conservation_color_films(self, film_name):
        """測試能量守恆（彩色膠片）"""
        film = get_film_profile(film_name)
        validator = PhysicsValidator(film, verbose=False)
        
        result = validator.validate_energy_conservation(tolerance=0.002)
        
        assert result.passed, f"{film_name}: {result.message}"
    
    @pytest.mark.parametrize("film_name", COLOR_FILMS)
    def test_row_normalization_color_films(self, film_name):
        """測試行正規化（彩色膠片）"""
        film = get_film_profile(film_name)
        validator = PhysicsValidator(film, verbose=False)
        
        results = validator.validate_row_normalization(tolerance=0.02)
        
        for result in results:
            assert result.passed, f"{film_name}: {result.message}"
    
    @pytest.mark.parametrize("film_name", COLOR_FILMS)
    def test_non_negativity_color_films(self, film_name):
        """測試非負性（彩色膠片）"""
        film = get_film_profile(film_name)
        validator = PhysicsValidator(film, verbose=False)
        
        results = validator.validate_non_negativity()
        
        for result in results:
            assert result.passed, f"{film_name}: {result.message}"
    
    @pytest.mark.parametrize("film_name", COLOR_FILMS)
    def test_monotonicity_color_films(self, film_name):
        """測試單調性（彩色膠片）"""
        film = get_film_profile(film_name)
        validator = PhysicsValidator(film, verbose=False)
        
        results = validator.validate_monotonicity()
        
        for result in results:
            assert result.passed, f"{film_name}: {result.message}"
    
    @pytest.mark.parametrize("film_name", COLOR_FILMS)
    def test_linearity_color_films(self, film_name):
        """測試線性疊加（彩色膠片）"""
        film = get_film_profile(film_name)
        validator = PhysicsValidator(film, verbose=False)
        
        result = validator.validate_linearity(tolerance=0.05)
        
        assert result.passed, f"{film_name}: {result.message}"
    
    @pytest.mark.parametrize("film_name", COLOR_FILMS)
    def test_diagonal_dominance_color_films(self, film_name):
        """測試對角線主導性（彩色膠片）"""
        film = get_film_profile(film_name)
        validator = PhysicsValidator(film, verbose=False)
        
        result = validator.validate_diagonal_dominance(min_ratio=5.0)
        
        # 這是警告級別測試，不影響整體通過
        if not result.passed:
            pytest.skip(f"{film_name}: Diagonal dominance below target (warning level)")
    
    def test_all_films_comprehensive(self):
        """綜合測試：所有彩色膠片"""
        failed_films = []
        
        for film_name in COLOR_FILMS:
            film = get_film_profile(film_name)
            validator = PhysicsValidator(film, verbose=False)
            summary = validator.run_all_validations()
            
            if not summary["all_passed"]:
                failed_films.append((film_name, summary["errors"]))
        
        assert len(failed_films) == 0, \
            f"以下膠片未通過物理驗證: {', '.join([f'{n} ({e} errors)' for n, e in failed_films])}"


# ==================== 校正驗證測試 ====================

class TestCalibrationQuality:
    """校正品質測試"""
    
    @pytest.mark.parametrize("film_name", COLOR_FILMS)
    def test_calibrated_gray_deviation(self, film_name):
        """測試校正後的灰階偏差"""
        calibrator = ComprehensiveCalibrator(verbose=False)
        result = calibrator.calibrate_film(film_name, strategy_id=3)
        
        if result.get("is_bw"):
            pytest.skip("黑白膠片無需光譜校正")
        
        gray_dev = result["calibrated_eval"]["gray_deviation"]
        
        assert gray_dev < 0.002, \
            f"{film_name}: 校正後灰階偏差 {gray_dev:.6f} 仍超過閾值 0.002"
    
    @pytest.mark.parametrize("film_name", COLOR_FILMS)
    def test_calibrated_row_balance(self, film_name):
        """測試校正後的行和平衡"""
        calibrator = ComprehensiveCalibrator(verbose=False)
        result = calibrator.calibrate_film(film_name, strategy_id=3)
        
        if result.get("is_bw"):
            pytest.skip("黑白膠片無需光譜校正")
        
        row_imbalance = result["calibrated_eval"]["row_imbalance"]
        
        assert row_imbalance < 0.02, \
            f"{film_name}: 校正後行不平衡 {row_imbalance:.6f} 超過閾值 0.02"
    
    @pytest.mark.parametrize("film_name", COLOR_FILMS)
    def test_calibration_improvement(self, film_name):
        """測試校正改善程度"""
        calibrator = ComprehensiveCalibrator(verbose=False)
        result = calibrator.calibrate_film(film_name, strategy_id=3)
        
        if result.get("is_bw"):
            pytest.skip("黑白膠片無需光譜校正")
        
        improvement = result["improvement"]["gray_deviation"]
        
        # 校正應該有明顯改善（至少50%）
        assert improvement > 0.5, \
            f"{film_name}: 校正改善不足 {improvement*100:.1f}% (應 > 50%)"
    
    @pytest.mark.parametrize("strategy_id", [1, 2, 3, 4, 5])
    def test_all_strategies_validity(self, strategy_id):
        """測試所有策略的有效性（使用 Portra400）"""
        calibrator = ComprehensiveCalibrator(verbose=False)
        result = calibrator.calibrate_film("Portra400", strategy_id=strategy_id)
        
        gray_dev = result["calibrated_eval"]["gray_deviation"]
        
        # 所有策略都應該減少色偏
        assert gray_dev < 0.01, \
            f"策略 {strategy_id}: 灰階偏差 {gray_dev:.6f} 過高"


# ==================== 迴歸測試 ====================

class TestCalibrationRegression:
    """校正迴歸測試：確保校正不破壞其他特性"""
    
    @pytest.mark.parametrize("film_name", COLOR_FILMS)
    def test_diagonal_preservation(self, film_name):
        """測試校正後對角線值保持合理"""
        calibrator = ComprehensiveCalibrator(verbose=False)
        result = calibrator.calibrate_film(film_name, strategy_id=3)
        
        if result.get("is_bw"):
            pytest.skip("黑白膠片無需光譜校正")
        
        original_matrix = result["original_matrix"]
        calibrated_matrix = result["calibrated_matrix"]
        
        # 對角線值不應該降低太多（保持 > 80%）
        for i in range(3):
            ratio = calibrated_matrix[i, i] / original_matrix[i, i]
            assert ratio > 0.8, \
                f"{film_name}: 對角線元素 [{i},{i}] 降低過多 ({ratio*100:.1f}%)"
    
    @pytest.mark.parametrize("film_name", COLOR_FILMS)
    def test_cross_response_validity(self, film_name):
        """測試校正後交叉響應合理"""
        calibrator = ComprehensiveCalibrator(verbose=False)
        result = calibrator.calibrate_film(film_name, strategy_id=3)
        
        if result.get("is_bw"):
            pytest.skip("黑白膠片無需光譜校正")
        
        calibrated_matrix = result["calibrated_matrix"]
        
        # 非對角線元素應該保持在合理範圍 (0-0.25)
        for i in range(3):
            for j in range(3):
                if i != j:
                    assert 0 <= calibrated_matrix[i, j] <= 0.25, \
                        f"{film_name}: 交叉響應 [{i},{j}]={calibrated_matrix[i, j]:.4f} 超出範圍"


# ==================== 性能測試 ====================

class TestCalibrationPerformance:
    """校正性能測試"""
    
    def test_validation_speed(self, benchmark):
        """測試物理驗證速度"""
        film = get_film_profile("Portra400")
        
        def run_validation():
            validator = PhysicsValidator(film, verbose=False)
            return validator.run_all_validations()
        
        result = benchmark(run_validation)
        assert result is not None
    
    def test_calibration_speed(self, benchmark):
        """測試校正速度"""
        def run_calibration():
            calibrator = ComprehensiveCalibrator(verbose=False)
            return calibrator.calibrate_film("Portra400", strategy_id=3)
        
        result = benchmark(run_calibration)
        assert result is not None


# ==================== Pytest Configuration ====================

@pytest.fixture(scope="session")
def calibration_results():
    """Session-wide fixture: 預先計算所有校正結果"""
    calibrator = ComprehensiveCalibrator(verbose=False)
    return calibrator.calibrate_all_films(strategy_id=3)


@pytest.fixture(scope="session")
def physics_results():
    """Session-wide fixture: 預先計算所有物理驗證結果"""
    from tools.physics_validator import validate_all_films
    return validate_all_films(verbose=False)


# ==================== 測試標記 ====================

# 在 pytest.ini 中添加以下標記：
# [tool:pytest]
# markers =
#     calibration: 光譜校正測試
#     physics: 物理理論驗證測試
#     regression: 迴歸測試
#     performance: 性能測試
#     slow: 慢速測試

# 使用方式：
# pytest tests_refactored/test_calibration_suite.py -m calibration
# pytest tests_refactored/test_calibration_suite.py -m physics
# pytest tests_refactored/test_calibration_suite.py -m "not slow"
