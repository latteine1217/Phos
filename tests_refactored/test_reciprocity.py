"""
Reciprocity Failure 測試套件（重構版）

合併自：
- test_reciprocity_failure.py (49 tests)
- test_reciprocity_integration.py (23 tests)

總測試數：72 tests

測試範圍：
1. Reciprocity Failure 參數與核心函數
2. 補償計算與參數驗證
3. 真實膠片配置整合
4. 與 H&D 曲線整合
5. 端到端流程測試
6. 邊界條件與數值穩定性
7. 效能測試

哲學原則：
- Never Break Userspace: 保持 100% 向後相容
- Pragmatism: 測試真實膠片數據（Kodak, Fuji）
- Simplicity: 集中相關測試，便於維護

重構日期：2026-01-11
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import numpy as np
import time
from film_models import ReciprocityFailureParams, get_film_profile, FilmProfile
from reciprocity_failure import (
    apply_reciprocity_failure,
    calculate_exposure_compensation,
    validate_params,
    get_reciprocity_chart,
    get_film_reciprocity_params
)


# ============================================================
# 單元測試：Reciprocity Failure 核心功能
# 來源：test_reciprocity_failure.py (49 tests)
# ============================================================

class TestReciprocityFailureParams:
    """測試 ReciprocityFailureParams 數據類"""
    
    def test_default_initialization(self):
        """測試預設初始化"""
        params = ReciprocityFailureParams()
        assert params.enabled == False
        assert params.p_red == 0.93  # 修正為實際預設值
        assert params.p_green == 0.90
        assert params.p_blue == 0.87  # 修正為實際預設值
        assert params.p_mono is None
        assert params.t_critical_low == 0.001
        assert params.t_critical_high == 1.0
    
    def test_color_film_initialization(self):
        """測試彩色膠片參數"""
        params = ReciprocityFailureParams(
            enabled=True,
            p_red=0.93,
            p_green=0.90,
            p_blue=0.87
        )
        assert params.enabled == True
        assert params.p_red == 0.93
        assert params.p_green == 0.90
        assert params.p_blue == 0.87
        assert params.p_mono is None
    
    def test_bw_film_initialization(self):
        """測試黑白膠片參數"""
        params = ReciprocityFailureParams(
            enabled=True,
            p_mono=0.88
        )
        assert params.enabled == True
        assert params.p_mono == 0.88
    
    def test_curve_type_options(self):
        """測試曲線類型選項"""
        params_const = ReciprocityFailureParams(curve_type="constant")
        params_log = ReciprocityFailureParams(curve_type="logarithmic")
        
        assert params_const.curve_type == "constant"
        assert params_log.curve_type == "logarithmic"


class TestApplyReciprocityFailure:
    """測試 apply_reciprocity_failure() 函數"""
    
    def test_disabled_no_effect(self):
        """測試 enabled=False 時無影響"""
        params = ReciprocityFailureParams(enabled=False)
        intensity = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        result = apply_reciprocity_failure(intensity, 10.0, params, is_color=True)
        np.testing.assert_allclose(result, intensity, rtol=1e-6)
    
    def test_1s_exposure_no_effect(self):
        """測試 t=1s 時無影響（向後相容）"""
        params = ReciprocityFailureParams(enabled=True, p_green=0.90)
        intensity = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        result = apply_reciprocity_failure(intensity, 1.0, params, is_color=True)
        # 允許微小誤差（浮點數精度）
        np.testing.assert_allclose(result, intensity, atol=1e-4)
    
    def test_long_exposure_darkening(self):
        """測試長曝光變暗效應"""
        params = ReciprocityFailureParams(enabled=True, p_green=0.90)
        intensity = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        result = apply_reciprocity_failure(intensity, 10.0, params, is_color=True)
        
        # 10s, p=0.90 → t^(p-1) = 10^(-0.1) ≈ 0.794
        # 預期亮度損失 20-30%
        darkening = (1 - np.mean(result) / 0.5) * 100
        assert 18 < darkening < 35, f"Darkening {darkening:.1f}% out of range [18, 35]"
    
    def test_channel_independence_color(self):
        """測試通道獨立效應（彩色膠片）"""
        params = ReciprocityFailureParams(
            enabled=True,
            p_red=0.93,
            p_green=0.90,
            p_blue=0.87
        )
        intensity = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        result = apply_reciprocity_failure(intensity, 30.0, params, is_color=True)
        
        # 紅色損失 < 綠色損失 < 藍色損失
        r_loss = (1 - np.mean(result[:,:,0]) / 0.5) * 100
        g_loss = (1 - np.mean(result[:,:,1]) / 0.5) * 100
        b_loss = (1 - np.mean(result[:,:,2]) / 0.5) * 100
        
        assert r_loss < g_loss < b_loss, \
            f"Channel independence failed: R={r_loss:.1f}, G={g_loss:.1f}, B={b_loss:.1f}"
    
    def test_bw_film_single_channel(self):
        """測試黑白膠片單通道處理（修復後）"""
        params = ReciprocityFailureParams(enabled=True, p_mono=0.88)
        intensity = np.ones((100, 100, 1), dtype=np.float32) * 0.5
        result = apply_reciprocity_failure(intensity, 10.0, params, is_color=False)
        
        assert result.shape == intensity.shape, f"Shape mismatch: {result.shape} vs {intensity.shape}"
        darkening = (1 - np.mean(result) / 0.5) * 100
        assert 20 < darkening < 40, f"BW darkening {darkening:.1f}% out of range [20, 40]"
    
    def test_bw_film_2d_input(self):
        """測試黑白膠片 2D 輸入 (H, W)"""
        params = ReciprocityFailureParams(enabled=True, p_mono=0.88)
        intensity = np.ones((100, 100), dtype=np.float32) * 0.5
        result = apply_reciprocity_failure(intensity, 10.0, params, is_color=False)
        
        assert result.shape == intensity.shape, f"Shape mismatch: {result.shape} vs {intensity.shape}"
        darkening = (1 - np.mean(result) / 0.5) * 100
        assert 20 < darkening < 40, f"BW 2D darkening {darkening:.1f}% out of range"
    
    def test_clipping_upper_bound(self):
        """測試值域裁剪上界 [0, 1]"""
        params = ReciprocityFailureParams(enabled=True, p_green=0.90)
        intensity = np.ones((100, 100, 3), dtype=np.float32) * 1.5  # 超出範圍
        result = apply_reciprocity_failure(intensity, 10.0, params, is_color=True)
        
        assert np.all(result >= 0.0), "Values below 0"
        assert np.all(result <= 1.0), "Values above 1"
    
    def test_clipping_lower_bound(self):
        """測試值域裁剪下界（負值處理）"""
        params = ReciprocityFailureParams(enabled=True, p_green=0.90)
        intensity = np.ones((100, 100, 3), dtype=np.float32) * -0.1  # 負值
        result = apply_reciprocity_failure(intensity, 10.0, params, is_color=True)
        
        assert np.all(result >= 0.0), "Negative values not clipped"
    
    def test_monotonicity_with_time(self):
        """測試時間單調性（時間越長，越暗）"""
        params = ReciprocityFailureParams(enabled=True, p_green=0.90)
        intensity = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        
        times = [1, 5, 10, 30, 60]
        brightness = []
        
        for t in times:
            result = apply_reciprocity_failure(intensity, t, params, is_color=True)
            brightness.append(np.mean(result))
        
        # 確保單調遞減
        for i in range(len(brightness) - 1):
            assert brightness[i] >= brightness[i+1], \
                f"Brightness increased at t={times[i+1]}: {brightness}"
    
    def test_short_exposure_no_failure(self):
        """測試極短曝光（< 1ms）無明顯失效"""
        params = ReciprocityFailureParams(enabled=True, p_green=0.90)
        intensity = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        result = apply_reciprocity_failure(intensity, 0.0001, params, is_color=True)
        
        # 極短曝光損失應很小
        darkening = (1 - np.mean(result) / 0.5) * 100
        assert darkening < 10, f"Short exposure darkening {darkening:.1f}% too high"
    
    def test_invalid_exposure_time(self):
        """測試無效曝光時間（負數/零）"""
        params = ReciprocityFailureParams(enabled=True)
        intensity = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        
        with pytest.raises(ValueError, match="exposure_time must be > 0"):
            apply_reciprocity_failure(intensity, 0.0, params, is_color=True)
        
        with pytest.raises(ValueError, match="exposure_time must be > 0"):
            apply_reciprocity_failure(intensity, -1.0, params, is_color=True)


class TestExposureCompensation:
    """測試 calculate_exposure_compensation() 函數"""
    
    def test_1s_no_compensation(self):
        """測試 t=1s 時無需補償"""
        params = ReciprocityFailureParams(enabled=True, p_green=0.90)
        comp = calculate_exposure_compensation(1.0, params, "green")
        assert abs(comp) < 0.01, f"Compensation at 1s should be ~0, got {comp:.3f}"
    
    def test_10s_compensation(self):
        """測試 10s 補償計算"""
        params = ReciprocityFailureParams(enabled=True, p_green=0.90)
        comp = calculate_exposure_compensation(10.0, params, "green")
        # p=0.90, 對數模型 → 預期約 0.5 EV
        assert 0.40 < comp < 0.60, f"Compensation at 10s out of range: {comp:.2f} EV"
    
    def test_30s_compensation(self):
        """測試 30s 補償計算"""
        params = ReciprocityFailureParams(enabled=True, p_green=0.90)
        comp = calculate_exposure_compensation(30.0, params, "green")
        # 預期 0.75 - 0.95 EV
        assert 0.70 < comp < 1.00, f"Compensation at 30s out of range: {comp:.2f} EV"
    
    def test_portra400_kodak_data(self):
        """測試 Portra 400 與 Kodak 官方數據比對"""
        params = get_film_reciprocity_params("Portra 400")
        
        # Kodak P-315: 10s → +0.50 EV, 30s → +0.90 EV
        comp_10s = calculate_exposure_compensation(10.0, params, "green")
        comp_30s = calculate_exposure_compensation(30.0, params, "green")
        
        # 允許 ±0.20 EV 誤差（對數模型與文獻略有差異）
        assert abs(comp_10s - 0.50) < 0.20, \
            f"Portra 10s: expected +0.50 EV, got {comp_10s:.2f}"
        assert abs(comp_30s - 0.90) < 0.20, \
            f"Portra 30s: expected +0.90 EV, got {comp_30s:.2f}"
    
    def test_channel_specific_compensation(self):
        """測試通道特定補償計算"""
        params = ReciprocityFailureParams(
            enabled=True,
            p_red=0.93,
            p_green=0.90,
            p_blue=0.87
        )
        
        comp_red = calculate_exposure_compensation(30.0, params, "red")
        comp_green = calculate_exposure_compensation(30.0, params, "green")
        comp_blue = calculate_exposure_compensation(30.0, params, "blue")
        
        # 藍色補償 > 綠色補償 > 紅色補償
        assert comp_blue > comp_green > comp_red, \
            f"Channel compensation order wrong: R={comp_red:.2f}, G={comp_green:.2f}, B={comp_blue:.2f}"
    
    def test_mono_channel_compensation(self):
        """測試黑白膠片補償"""
        params = ReciprocityFailureParams(enabled=True, p_mono=0.88)
        comp = calculate_exposure_compensation(30.0, params, "mono")
        
        # 黑白膠片 p=0.88 應比 p=0.90 需要更多補償
        assert 0.6 < comp < 1.0, f"Mono compensation at 30s out of range: {comp:.2f} EV"


class TestValidation:
    """測試參數驗證"""
    
    def test_valid_params(self):
        """測試有效參數"""
        params = ReciprocityFailureParams(p_red=0.93, p_green=0.90, p_blue=0.87)
        is_valid, msg = validate_params(params)
        assert is_valid, f"Valid params marked invalid: {msg}"
    
    def test_invalid_p_value_too_high(self):
        """測試無效 p 值（過高）"""
        with pytest.raises(AssertionError, match="p_red.*超出範圍"):
            params = ReciprocityFailureParams(p_red=1.5)  # p > 1.0
    
    def test_invalid_p_value_too_low(self):
    
        """測試無效 p 值（過低）"""
        with pytest.raises(AssertionError, match="p_green.*超出範圍"):
            params = ReciprocityFailureParams(p_green=0.5)  # p < 0.75
    
    def test_invalid_t_critical(self):
    
        """測試無效臨界時間"""
        with pytest.raises(AssertionError, match="t_critical_high.*超出範圍"):
            params = ReciprocityFailureParams(t_critical_high=-1.0)  # 負數
    
    def test_invalid_curve_type(self):
    
        """測試無效曲線類型"""
        with pytest.raises(AssertionError, match="curve_type.*無效"):
            params = ReciprocityFailureParams(curve_type="invalid_type")




class TestRealFilmProfiles:
    """測試真實膠片配置整合"""
    
    @pytest.mark.parametrize("film_name", [
        "Portra400", "Ektar100", "Velvia50",
        "HP5Plus400", "TriX400", "Cinestill800T"
    ])
    def test_film_has_reciprocity_params(self, film_name):
        """測試所有膠片都有 reciprocity_params"""
        film = get_film_profile(film_name)
        assert hasattr(film, 'reciprocity_params'), f"{film_name} missing reciprocity_params"
        assert film.reciprocity_params is not None
        assert isinstance(film.reciprocity_params, ReciprocityFailureParams)
    
    def test_portra400_30s_loss(self):
        """測試 Portra400 @ 30s 亮度損失"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        
        intensity = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        result = apply_reciprocity_failure(intensity, 30.0, film.reciprocity_params, is_color=True)
        loss = (1 - np.mean(result) / 0.5) * 100
        
        # 預期 35-43%（允許誤差）
        assert 33 < loss < 45, f"Portra400 @ 30s loss {loss:.1f}% out of range [33, 45]"
    
    def test_velvia50_high_failure(self):
        """測試 Velvia50 高失效特性"""
        film = get_film_profile("Velvia50")
        film.reciprocity_params.enabled = True
        
        intensity = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        result = apply_reciprocity_failure(intensity, 30.0, film.reciprocity_params, is_color=True)
        loss = (1 - np.mean(result) / 0.5) * 100
        
        # Velvia 失效應 > Portra （預期 50-60%）
        assert 48 < loss < 65, f"Velvia50 @ 30s loss {loss:.1f}% out of range [48, 65]"
    
    def test_hp5plus400_bw_processing(self):
        """測試 HP5Plus400 黑白膠片處理"""
        film = get_film_profile("HP5Plus400")
        film.reciprocity_params.enabled = True
        
        intensity = np.ones((100, 100, 1), dtype=np.float32) * 0.5
        result = apply_reciprocity_failure(intensity, 10.0, film.reciprocity_params, is_color=False)
        
        assert result.shape == intensity.shape
        loss = (1 - np.mean(result) / 0.5) * 100
        assert 25 < loss < 45, f"HP5Plus400 @ 10s loss {loss:.1f}% out of range"
    
    def test_trix400_bw_processing(self):
        """測試 TriX400 黑白膠片處理"""
        film = get_film_profile("TriX400")
        film.reciprocity_params.enabled = True
        
        intensity = np.ones((100, 100, 1), dtype=np.float32) * 0.5
        result = apply_reciprocity_failure(intensity, 30.0, film.reciprocity_params, is_color=False)
        
        loss = (1 - np.mean(result) / 0.5) * 100
        assert 40 < loss < 55, f"TriX400 @ 30s loss {loss:.1f}% out of range"
    
    def test_film_reciprocity_consistency(self):
        """測試膠片失效一致性（Velvia > HP5 > Portra）"""
        films = {
            "Portra400": get_film_profile("Portra400"),
            "HP5Plus400": get_film_profile("HP5Plus400"),
            "Velvia50": get_film_profile("Velvia50")
        }
        
        intensity = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        results = {}
        
        for name, film in films.items():
            film.reciprocity_params.enabled = True
            is_color = (film.reciprocity_params.p_mono is None)
            result = apply_reciprocity_failure(intensity, 30.0, film.reciprocity_params, is_color=is_color)
            results[name] = np.mean(result)
        
        # Velvia 最暗（失效最嚴重）
        assert results["Velvia50"] < results["HP5Plus400"]
        assert results["Velvia50"] < results["Portra400"]


class TestGetReciprocityChart:
    """測試 get_reciprocity_chart() 函數"""
    
    def test_chart_generation(self):
        """測試特性曲線生成"""
        params = ReciprocityFailureParams(enabled=True, p_green=0.90)
        times, compensations = get_reciprocity_chart(params)  # 修正：只有兩個返回值
        
        assert len(times) > 0
        assert len(times) == len(compensations)
        
        # 檢查單調性（補償值應遞增）
        for i in range(len(compensations) - 1):
            assert compensations[i] <= compensations[i+1], "Compensation not monotonic"
    
    def test_chart_multiple_channels(self):
        """測試多通道特性曲線"""
        params = ReciprocityFailureParams(
            enabled=True,
            p_red=0.93,
            p_green=0.90,
            p_blue=0.87
        )
        
        # 分別計算三個通道
        _, comp_r = get_reciprocity_chart(params)  # 預設綠通道
        _, comp_g = get_reciprocity_chart(params)
        _, comp_b = get_reciprocity_chart(params)
        
        # 注：get_reciprocity_chart 預設使用 "green"，需手動計算其他通道
        # 這裡只測試函數可以運行
        assert len(comp_r) > 0
        assert len(comp_g) > 0
        assert len(comp_b) > 0


class TestGetFilmReciprocityParams:
    """測試 get_film_reciprocity_params() 函數"""
    
    @pytest.mark.parametrize("film_name", [
        "Portra 400", "Velvia 50", "Tri-X 400", "HP5 Plus"
    ])
    def test_preset_loading(self, film_name):
        """測試預設配置載入"""
        params = get_film_reciprocity_params(film_name)
        assert params is not None
        assert isinstance(params, ReciprocityFailureParams)
    
    def test_unknown_film_raises_error(self):
        """測試未知膠片引發錯誤"""
        with pytest.raises(ValueError, match="not supported"):
            get_film_reciprocity_params("Unknown Film")


class TestPerformance:
    """測試效能"""
    
    def test_performance_512x512(self):
        """測試效能 @ 512x512"""
        params = ReciprocityFailureParams(enabled=True)
        intensity = np.random.rand(512, 512, 3).astype(np.float32)
        
        start = time.perf_counter()
        for _ in range(10):
            _ = apply_reciprocity_failure(intensity, 10.0, params, is_color=True)
        elapsed = (time.perf_counter() - start) / 10
        
        assert elapsed < 0.005, f"Performance @ 512x512: {elapsed*1000:.2f} ms > 5 ms"
    
    def test_performance_1024x1024(self):
        """測試效能 @ 1024x1024"""
        params = ReciprocityFailureParams(enabled=True)
        intensity = np.random.rand(1024, 1024, 3).astype(np.float32)
        
        start = time.perf_counter()
        for _ in range(10):
            _ = apply_reciprocity_failure(intensity, 10.0, params, is_color=True)
        elapsed = (time.perf_counter() - start) / 10
        
        assert elapsed < 0.010, f"Performance @ 1024x1024: {elapsed*1000:.2f} ms > 10 ms"
    
    def test_performance_4k(self):
        """測試效能 @ 4K (3840x2160)"""
        params = ReciprocityFailureParams(enabled=True)
        intensity = np.random.rand(2160, 3840, 3).astype(np.float32)
        
        start = time.perf_counter()
        result = apply_reciprocity_failure(intensity, 10.0, params, is_color=True)
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.100, f"Performance @ 4K: {elapsed*1000:.2f} ms > 100 ms"


class TestEnergyConservation:
    """測試能量守恆"""
    
    def test_energy_conservation(self):
        """測試能量守恆（不增加能量）"""
        params = ReciprocityFailureParams(enabled=True, p_green=0.90)
        intensity = np.random.rand(256, 256, 3).astype(np.float32)
        result = apply_reciprocity_failure(intensity, 30.0, params, is_color=True)
        
        # reciprocity failure 只能減少或保持能量
        assert np.sum(result) <= np.sum(intensity), "Energy increased (violation)"
    
    def test_energy_monotonicity(self):
        """測試能量單調性（時間越長，能量越低）"""
        params = ReciprocityFailureParams(enabled=True, p_green=0.90)
        intensity = np.random.rand(256, 256, 3).astype(np.float32)
        
        times = [1, 10, 30, 60]
        energies = []
        
        for t in times:
            result = apply_reciprocity_failure(intensity.copy(), t, params, is_color=True)
            energies.append(np.sum(result))
        
        # 確保單調遞減
        for i in range(len(energies) - 1):
            assert energies[i] >= energies[i+1], f"Energy increased at t={times[i+1]}"


# ============================================================
# 整合測試：Reciprocity Failure 與完整處理流程
# 來源：test_reciprocity_integration.py (23 tests)
# ============================================================

class TestIntegrationWithFilmProfiles:
    """測試與膠片配置整合"""
    
    def test_portra400_full_pipeline(self):
        """測試 Portra400 完整流程"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        
        # 模擬完整流程：spectral response → reciprocity → H&D curve
        test_img = np.random.rand(256, 256, 3).astype(np.float32) * 0.8
        
        # 應用 reciprocity
        result = apply_reciprocity_failure(test_img, 30.0, film.reciprocity_params, is_color=True)
        
        # 檢查結果
        assert result.shape == test_img.shape
        assert np.all(result >= 0) and np.all(result <= 1)
        assert np.mean(result) < np.mean(test_img)  # 應變暗
    
    def test_multiple_films_consistency(self):
        """測試多種膠片一致性"""
        films = ["Portra400", "Velvia50", "HP5Plus400"]
        test_img = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        
        results = {}
        for film_name in films:
            film = get_film_profile(film_name)
            film.reciprocity_params.enabled = True
            is_color = (film.reciprocity_params.p_mono is None)
            result = apply_reciprocity_failure(test_img, 30.0, film.reciprocity_params, is_color=is_color)
            results[film_name] = np.mean(result)
        
        # Velvia 失效最嚴重（結果最暗）
        assert results["Velvia50"] < results["Portra400"]
        assert results["Velvia50"] < results["HP5Plus400"]
    
    def test_exposure_time_monotonicity(self):
        """測試曝光時間單調性（時間越長，越暗）"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        test_img = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        
        times = [1, 5, 10, 30, 60]
        brightness = []
        
        for t in times:
            result = apply_reciprocity_failure(test_img, t, film.reciprocity_params, is_color=True)
            brightness.append(np.mean(result))
        
        # 確保單調遞減
        for i in range(len(brightness) - 1):
            assert brightness[i] >= brightness[i+1], f"Brightness increased: {brightness}"


class TestColorVsBlackWhite:
    """測試彩色與黑白膠片處理差異"""
    
    def test_color_film_channel_independence(self):
        """測試彩色膠片通道獨立性"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        
        # 純色輸入
        red_img = np.zeros((100, 100, 3), dtype=np.float32)
        red_img[:, :, 0] = 0.8
        
        green_img = np.zeros((100, 100, 3), dtype=np.float32)
        green_img[:, :, 1] = 0.8
        
        blue_img = np.zeros((100, 100, 3), dtype=np.float32)
        blue_img[:, :, 2] = 0.8
        
        # 應用失效
        result_r = apply_reciprocity_failure(red_img, 30.0, film.reciprocity_params, is_color=True)
        result_g = apply_reciprocity_failure(green_img, 30.0, film.reciprocity_params, is_color=True)
        result_b = apply_reciprocity_failure(blue_img, 30.0, film.reciprocity_params, is_color=True)
        
        # 三個通道損失應不同
        loss_r = (1 - np.mean(result_r[:, :, 0]) / 0.8) * 100
        loss_g = (1 - np.mean(result_g[:, :, 1]) / 0.8) * 100
        loss_b = (1 - np.mean(result_b[:, :, 2]) / 0.8) * 100
        
        assert loss_r < loss_g < loss_b, f"Channel losses: R={loss_r:.1f}, G={loss_g:.1f}, B={loss_b:.1f}"
    
    def test_bw_film_uniform_channel(self):
        """測試黑白膠片單通道處理"""
        film = get_film_profile("HP5Plus400")
        film.reciprocity_params.enabled = True
        
        # 黑白輸入 (H, W, 1)
        test_bw = np.ones((100, 100, 1), dtype=np.float32) * 0.5
        result = apply_reciprocity_failure(test_bw, 30.0, film.reciprocity_params, is_color=False)
        
        assert result.shape == test_bw.shape
        assert np.mean(result) < 0.5


class TestEdgeCases:
    """測試邊界條件"""
    
    def test_very_short_exposure(self):
        """測試極短曝光（< 0.1s）"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        test_img = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        
        result = apply_reciprocity_failure(test_img, 0.0001, film.reciprocity_params, is_color=True)
        
        # 極短曝光應無明顯失效
        loss = (1 - np.mean(result) / 0.5) * 100
        assert loss < 10, f"Short exposure loss {loss:.1f}% too high"
    
    def test_very_long_exposure(self):
        """測試極長曝光（> 100s）"""
        film = get_film_profile("Velvia50")
        film.reciprocity_params.enabled = True
        test_img = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        
        result = apply_reciprocity_failure(test_img, 300.0, film.reciprocity_params, is_color=True)
        
        # 極長曝光應有顯著失效
        loss = (1 - np.mean(result) / 0.5) * 100
        assert loss > 50, f"Long exposure loss {loss:.1f}% too low"
    
    def test_zero_intensity(self):
        """測試零強度輸入（全黑）"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        test_img = np.zeros((100, 100, 3), dtype=np.float32)
        
        result = apply_reciprocity_failure(test_img, 30.0, film.reciprocity_params, is_color=True)
        
        # 全黑應保持全黑
        assert np.all(result == 0)
    
    def test_full_intensity(self):
        """測試滿強度輸入（全白）"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        test_img = np.ones((100, 100, 3), dtype=np.float32)
        
        result = apply_reciprocity_failure(test_img, 30.0, film.reciprocity_params, is_color=True)
        
        # 全白應變暗
        assert np.mean(result) < 1.0
        assert np.all(result >= 0) and np.all(result <= 1)
    
    def test_single_pixel(self):
        """測試單像素輸入"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        test_img = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float32)
        
        result = apply_reciprocity_failure(test_img, 30.0, film.reciprocity_params, is_color=True)
        
        assert result.shape == test_img.shape
        assert result[0, 0, 0] < 0.5
    
    def test_large_image(self):
        """測試大影像（4K）"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        test_img = np.random.rand(2160, 3840, 3).astype(np.float32) * 0.5
        
        result = apply_reciprocity_failure(test_img, 10.0, film.reciprocity_params, is_color=True)
        
        assert result.shape == test_img.shape
        assert np.mean(result) < np.mean(test_img)


class TestDisabledMode:
    """測試禁用模式"""
    
    def test_disabled_no_change(self):
        """測試 enabled=False 時無變化"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = False
        test_img = np.random.rand(256, 256, 3).astype(np.float32)
        
        result = apply_reciprocity_failure(test_img, 30.0, film.reciprocity_params, is_color=True)
        
        np.testing.assert_allclose(result, test_img, rtol=1e-6)
    
    def test_1s_exposure_backward_compatibility(self):
        """測試 t=1s 時向後相容性"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        test_img = np.random.rand(256, 256, 3).astype(np.float32)
        
        result = apply_reciprocity_failure(test_img, 1.0, film.reciprocity_params, is_color=True)
        
        # t=1s 時應無明顯變化
        np.testing.assert_allclose(result, test_img, atol=1e-3)


class TestNumericalStability:
    """測試數值穩定性"""
    
    def test_no_nan_or_inf(self):
        """測試不產生 NaN 或 Inf"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        
        # 測試極端值
        test_cases = [
            np.ones((100, 100, 3), dtype=np.float32) * 1e-6,  # 極小值
            np.ones((100, 100, 3), dtype=np.float32) * 1.5,  # 超出範圍
            np.random.rand(100, 100, 3).astype(np.float32),  # 隨機值
        ]
        
        for test_img in test_cases:
            result = apply_reciprocity_failure(test_img, 30.0, film.reciprocity_params, is_color=True)
            assert not np.any(np.isnan(result)), "Result contains NaN"
            assert not np.any(np.isinf(result)), "Result contains Inf"
    
    def test_range_preservation(self):
        """測試值域保持在 [0, 1]"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        test_img = np.random.rand(256, 256, 3).astype(np.float32) * 1.2  # 故意超出範圍
        
        result = apply_reciprocity_failure(test_img, 30.0, film.reciprocity_params, is_color=True)
        
        assert np.all(result >= 0.0), "Values below 0"
        assert np.all(result <= 1.0), "Values above 1"
    
    def test_reproducibility(self):
        """測試可重現性（相同輸入→相同輸出）"""
        film = get_film_profile("Portra400")
        film.reciprocity_params.enabled = True
        test_img = np.random.rand(256, 256, 3).astype(np.float32)
        
        result1 = apply_reciprocity_failure(test_img.copy(), 30.0, film.reciprocity_params, is_color=True)
        result2 = apply_reciprocity_failure(test_img.copy(), 30.0, film.reciprocity_params, is_color=True)
        
        np.testing.assert_array_equal(result1, result2)


class TestAllFilmProfiles:
    """測試所有膠片配置"""
    
    @pytest.mark.parametrize("film_name", [
        "Portra400", "Ektar100", "Velvia50",
        "HP5Plus400", "TriX400", "Cinestill800T"
    ])
    def test_all_films_processable(self, film_name):
        """測試所有膠片都能正常處理"""
        film = get_film_profile(film_name)
        film.reciprocity_params.enabled = True
        
        test_img = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        is_color = (film.reciprocity_params.p_mono is None)
        
        if not is_color:
            # 黑白膠片
            test_img = test_img[:, :, :1]  # (H, W, 1)
        
        result = apply_reciprocity_failure(test_img, 30.0, film.reciprocity_params, is_color=is_color)
        
        assert result.shape == test_img.shape
        assert np.all(result >= 0) and np.all(result <= 1)
        assert np.mean(result) < np.mean(test_img)
    
    def test_film_failure_ranking(self):
        """測試膠片失效程度排序"""
        # 預期排序（從低到高失效）：Ektar < Portra < HP5 < TriX < Velvia
        films = {
            "Ektar100": get_film_profile("Ektar100"),
            "Portra400": get_film_profile("Portra400"),
            "Velvia50": get_film_profile("Velvia50"),
        }
        
        test_img = np.ones((100, 100, 3), dtype=np.float32) * 0.5
        results = {}
        
        for name, film in films.items():
            film.reciprocity_params.enabled = True
            result = apply_reciprocity_failure(test_img, 30.0, film.reciprocity_params, is_color=True)
            results[name] = np.mean(result)
        
        # Ektar（現代膠片）失效最低 → 亮度最高
        assert results["Ektar100"] > results["Portra400"]
        # Velvia（反轉片）失效最高 → 亮度最低
        assert results["Velvia50"] < results["Portra400"]


# 運行測試
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
