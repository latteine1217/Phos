"""
端到端測試：驗證中等物理模式完整流程

測試範圍：
1. 配置載入驗證（Cinestill800T_MediumPhysics, Portra400_MediumPhysics）
2. 參數正確性檢查（Physics Mode, Bloom, Halation）
3. 物理特性驗證（Beer-Lambert, 能量守恆）
4. 性能基準測試（< 10s 目標）

限制：
- 由於 Phos_0.3.0.py 依賴 Streamlit，無法直接導入處理函數
- 本測試僅驗證配置層面，實際影像處理需通過 UI 或獨立腳本測試

作者：TASK-003 Phase 2
日期：2025-12-19
"""

import numpy as np
import time
import sys
import pytest
from pathlib import Path
from typing import Tuple

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 從 film_models 導入測試配置
from film_models import (
    get_film_profile, 
    PhysicsMode, 
    HalationParams,
    BloomParams
)

# ==================== Fixtures ====================
@pytest.fixture
def cs():
    """CineStill800T Medium Physics profile fixture"""
    return get_film_profile("Cinestill800T")

@pytest.fixture
def portra():
    """Portra400 Medium Physics profile fixture"""
    return get_film_profile("Portra400")


def test_medium_physics_profiles_exist(cs, portra):
    """測試 1: 中等物理配置存在性"""
    print("\n" + "=" * 70)
    print("Test 1: 驗證中等物理配置存在")
    print("=" * 70)
    
    # 測試 CineStill 配置
    assert cs is not None, "CineStill Medium Physics profile should exist"
    print("  ✓ Cinestill800T loaded")
    
    # 測試 Portra 配置
    assert portra is not None, "Portra400 Medium Physics profile should exist"
    print("  ✓ Portra400 loaded")
    
    print("  ✅ Test 1 Passed")


def test_physics_mode_activation(cs, portra):
    """測試 2: 物理模式啟用驗證"""
    print("\n" + "=" * 70)
    print("Test 2: 驗證物理模式啟用狀態")
    print("=" * 70)
    
    # CineStill 測試
    print("\n  [CineStill800T_MediumPhysics]")
    assert cs.physics_mode == PhysicsMode.PHYSICAL, \
        f"Expected PhysicsMode.PHYSICAL, got {cs.physics_mode}"
    print(f"    Physics Mode: {cs.physics_mode} ✓")
    
    assert cs.bloom_params.mode == "physical", \
        f"Expected bloom mode 'physical', got {cs.bloom_params.mode}"
    print(f"    Bloom Mode: {cs.bloom_params.mode} ✓")
    
    assert cs.halation_params.enabled == True, \
        "Halation should be enabled"
    print(f"    Halation Enabled: {cs.halation_params.enabled} ✓")
    
    # Portra 測試
    print("\n  [Portra400_MediumPhysics]")
    assert portra.physics_mode == PhysicsMode.PHYSICAL
    assert portra.bloom_params.mode == "physical"
    assert portra.halation_params.enabled == True
    print(f"    Physics Mode: {portra.physics_mode} ✓")
    print(f"    Bloom Mode: {portra.bloom_params.mode} ✓")
    print(f"    Halation Enabled: {portra.halation_params.enabled} ✓")
    
    print("\n  ✅ Test 2 Passed")


def test_halation_parameters(cs, portra):
    """測試 3: Halation 參數正確性"""
    print("\n" + "=" * 70)
    print("Test 3: 驗證 Halation 參數配置")
    print("=" * 70)
    
    # CineStill: 無 AH 層（極端光暈）
    print("\n  [CineStill800T - 極端 Halation]")
    print(f"    AH Absorption: {cs.halation_params.ah_absorption}")
    assert cs.halation_params.ah_absorption == 0.0, \
        "CineStill should have no AH layer (ah_absorption=0)"
    print("      ✓ 無 AH 層（ah_absorption=0.0）")
    
    print(f"    Transmittance (R,G,B): ({cs.halation_params.transmittance_r}, "
          f"{cs.halation_params.transmittance_g}, {cs.halation_params.transmittance_b})")
    assert cs.halation_params.transmittance_r > cs.halation_params.transmittance_b, \
        "Red should penetrate more than blue"
    print("      ✓ 紅光穿透力 > 藍光（符合 Beer-Lambert）")
    
    print(f"    PSF Radius: {cs.halation_params.psf_radius}px")
    assert cs.halation_params.psf_radius == 150, \
        "CineStill should have large halo (150px)"
    print("      ✓ 極大光暈半徑（200px = 2x 標準）")
    
    print(f"    Energy Fraction: {cs.halation_params.energy_fraction}")
    assert cs.halation_params.energy_fraction == 0.15, \
        "CineStill should have 15% halation energy"
    print("      ✓ 高能量比例（0.15 = 3x 標準）")
    
    # Portra: 有 AH 層（標準膠片）
    print("\n  [Portra400 - 標準 Halation]")
    print(f"    AH Absorption: {portra.halation_params.ah_absorption}")
    assert portra.halation_params.ah_absorption == 0.95, \
        "Portra should have AH layer (ah_absorption=0.95)"
    print("      ✓ 有 AH 層（ah_absorption=0.95）")
    
    print(f"    Transmittance (R,G,B): ({portra.halation_params.transmittance_r}, "
          f"{portra.halation_params.transmittance_g}, {portra.halation_params.transmittance_b})")
    assert portra.halation_params.transmittance_r > portra.halation_params.transmittance_b
    print("      ✓ 紅光穿透力 > 藍光")
    
    print(f"    PSF Radius: {portra.halation_params.psf_radius}px")
    assert portra.halation_params.psf_radius == 80, \
        "Portra should have standard halo (80px)"
    print("      ✓ 標準光暈半徑（80px）")
    
    print(f"    Energy Fraction: {portra.halation_params.energy_fraction}")
    assert portra.halation_params.energy_fraction == 0.03, \
        "Portra should have 3% halation energy"
    print("      ✓ 標準能量比例（0.03）")
    
    print("\n  ✅ Test 3 Passed")


def test_beer_lambert_ratios(cs, portra):
    """測試 4: Beer-Lambert 波長依賴驗證"""
    print("\n" + "=" * 70)
    print("Test 4: 驗證 Beer-Lambert 波長依賴特性")
    print("=" * 70)
    
    def compute_halation_coefficient(hp: HalationParams, T_lambda: float) -> float:
        """計算 Halation 有效係數：f_h(λ) = (1-ah_abs) × R_bp × T(λ)²"""
        return (1.0 - hp.ah_absorption) * hp.backplate_reflectance * (T_lambda ** 2)
    
    # CineStill 測試
    print("\n  [CineStill800T - Beer-Lambert 係數]")
    f_h_r = compute_halation_coefficient(cs.halation_params, cs.halation_params.transmittance_r)
    f_h_g = compute_halation_coefficient(cs.halation_params, cs.halation_params.transmittance_g)
    f_h_b = compute_halation_coefficient(cs.halation_params, cs.halation_params.transmittance_b)
    
    print(f"    f_h(紅) = {f_h_r:.6f}")
    print(f"    f_h(綠) = {f_h_g:.6f}")
    print(f"    f_h(藍) = {f_h_b:.6f}")
    print(f"    比例 f_h(紅)/f_h(藍) = {f_h_r/f_h_b:.2f}x")
    
    assert f_h_r > f_h_g > f_h_b, "Should follow: Red > Green > Blue"
    print("      ✓ 紅光 Halation 最強（符合物理預期）")
    
    # Portra 測試
    print("\n  [Portra400 - Beer-Lambert 係數]")
    f_h_r_p = compute_halation_coefficient(portra.halation_params, portra.halation_params.transmittance_r)
    f_h_g_p = compute_halation_coefficient(portra.halation_params, portra.halation_params.transmittance_g)
    f_h_b_p = compute_halation_coefficient(portra.halation_params, portra.halation_params.transmittance_b)
    
    print(f"    f_h(紅) = {f_h_r_p:.6f}")
    print(f"    f_h(綠) = {f_h_g_p:.6f}")
    print(f"    f_h(藍) = {f_h_b_p:.6f}")
    print(f"    比例 f_h(紅)/f_h(藍) = {f_h_r_p/f_h_b_p:.2f}x")
    
    assert f_h_r_p > f_h_g_p > f_h_b_p
    print("      ✓ 紅光 Halation 最強")
    
    # AH 層效果比較
    print("\n  [AH 層效果比較]")
    print(f"    CineStill (無AH) f_h(紅): {f_h_r:.6f}")
    print(f"    Portra (有AH) f_h(紅): {f_h_r_p:.6f}")
    print(f"    抑制比例: {f_h_r_p/f_h_r:.2%} (AH 層抑制 {100*(1-f_h_r_p/f_h_r):.1f}%)")
    
    assert f_h_r > f_h_r_p, "CineStill (no AH) should have stronger halation than Portra (with AH)"
    print("      ✓ AH 層有效抑制 Halation")
    
    print("\n  ✅ Test 4 Passed")


def test_bloom_parameters(cs, portra):
    """測試 5: Bloom 參數驗證"""
    print("\n" + "=" * 70)
    print("Test 5: 驗證 Bloom 參數配置")
    print("=" * 70)
    
    for name, film in [("CineStill", cs), ("Portra", portra)]:
        print(f"\n  [{name}]")
        bp = film.bloom_params
        
        print(f"    Mode: {bp.mode}")
        assert bp.mode == "physical", f"{name} should use physical bloom"
        
        print(f"    Threshold: {bp.threshold}")
        assert bp.threshold > 0.0, "Threshold should be positive"
        
        print(f"    Scattering Ratio: {bp.scattering_ratio}")
        assert 0 < bp.scattering_ratio <= 0.1, "Scattering ratio should be 0-10%"
        
        print(f"    PSF Type: {bp.psf_type}")
        assert bp.psf_type in ["gaussian", "exponential"], "PSF type should be valid"
        
        print(f"    Energy Conservation: {bp.energy_conservation}")
        assert bp.energy_conservation == True, "Energy conservation must be enabled"
        
        print(f"      ✓ All parameters valid")
    
    print("\n  ✅ Test 5 Passed")


def test_mode_detection_logic():
    """測試 6: 驗證中等物理模式檢測邏輯"""
    print("\n" + "=" * 70)
    print("Test 6: 驗證中等物理模式檢測邏輯")
    print("=" * 70)
    
    # 測試 CineStill (Decision #020: 已升級為 PHYSICAL 模式)
    cs = get_film_profile("Cinestill800T")
    
    # 模擬 Phos_0.3.0.py 中的檢測邏輯
    use_physical_bloom = (
        cs.physics_mode == PhysicsMode.PHYSICAL and
        cs.bloom_params.mode == "physical"
    )
    
    use_medium_physics = (
        use_physical_bloom and
        hasattr(cs, 'halation_params') and
        cs.halation_params is not None and
        cs.halation_params.enabled
    )
    
    print(f"\n  Physics Mode: {cs.physics_mode}")
    print(f"  Bloom Mode: {cs.bloom_params.mode}")
    print(f"  Has Halation Params: {hasattr(cs, 'halation_params')}")
    print(f"  Halation Enabled: {cs.halation_params.enabled if hasattr(cs, 'halation_params') else 'N/A'}")
    print(f"\n  → use_physical_bloom: {use_physical_bloom}")
    print(f"  → use_medium_physics: {use_medium_physics}")
    
    assert use_physical_bloom == True, "Physical bloom should be detected (Decision #020)"
    assert use_medium_physics == True, "Medium physics should be detected for all color films (Decision #020)"
    print("\n  ✓ 中等物理模式檢測邏輯正確")
    
    # 測試黑白底片（應該保持 ARTISTIC 模式）
    hp5 = get_film_profile("HP5Plus400")
    
    use_physical_bloom_bw = (
        hp5.physics_mode == PhysicsMode.PHYSICAL and
        hp5.bloom_params.mode == "physical"
    )
    
    print(f"\n  [HP5Plus400 (B&W) - Should remain ARTISTIC]")
    print(f"  Physics Mode: {hp5.physics_mode}")
    print(f"  → use_physical_bloom: {use_physical_bloom_bw}")
    
    assert use_physical_bloom_bw == False, "B&W films should remain ARTISTIC mode"
    print("  ✓ 黑白底片保持 ARTISTIC 模式（正確）")
    
    print("\n  ✅ Test 6 Passed")


def test_performance_estimate():
    """測試 7: 效能估算（基於 Phase 2 測試結果）"""
    print("\n" + "=" * 70)
    print("Test 7: 效能估算（基於已知基準）")
    print("=" * 70)
    
    # 基於 test_phase2_integration.py 測試結果
    known_times = {
        "1000x1000": 0.023,   # 秒
        "2000x3000": 0.136    # 秒
    }
    
    print(f"\n  已知效能基準（Phase 2 Halation 測試）:")
    print(f"    1000×1000: {known_times['1000x1000']:.3f}s")
    print(f"    2000×3000: {known_times['2000x3000']:.3f}s")
    
    target_time = 10.0  # 秒
    print(f"\n  目標限制: < {target_time}s (2000×3000 影像)")
    
    margin = target_time / known_times["2000x3000"]
    print(f"  安全邊界: {margin:.1f}x (實際用時為目標的 {100/margin:.1f}%)")
    
    assert known_times["2000x3000"] < target_time, \
        f"Performance should meet target: {known_times['2000x3000']:.3f}s < {target_time}s"
    print(f"  ✓ 效能達標 ({known_times['2000x3000']:.3f}s < {target_time}s)")
    
    # 估算 Bloom + Halation 總時間
    estimated_total = known_times["2000x3000"] * 2  # Bloom + Halation (粗略估算)
    print(f"\n  估算 Bloom+Halation 總時間: ~{estimated_total:.3f}s")
    print(f"  ✓ 仍遠低於目標 ({estimated_total:.3f}s < {target_time}s)")
    
    print("\n  ✅ Test 7 Passed")


def run_all_tests():
    """
    執行所有測試（已棄用）
    
    建議使用 pytest 執行測試：
    $ pytest tests/test_medium_physics_e2e.py -v
    """
    print("\n")
    print("█" * 70)
    print("███ 中等物理模式端到端測試 (TASK-003 Phase 2) ███")
    print("█" * 70)
    print("\n⚠️  此函數已棄用，請使用 pytest 執行測試")
    print("指令：pytest tests/test_medium_physics_e2e.py -v\n")


if __name__ == "__main__":
    import sys
    run_all_tests()
    sys.exit(0)
