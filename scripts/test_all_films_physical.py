#!/usr/bin/env python3
"""
測試所有彩色膠片的中階物理模式

使用方式:
    python3 scripts/test_all_films_physical.py

測試範圍:
    - 驗證 8 款主要彩色膠片的 Physical 模式配置
    - 檢查 BloomParams, HalationParams, WavelengthBloomParams
    - 輸出每款膠片的散射比例（ISO 依賴）
"""

from film_models import get_film_profile, PhysicsMode

def test_all_color_films():
    """測試所有彩色膠片的中階物理參數"""
    
    # 主要彩色膠片（8 款）
    main_color_films = [
        ('NC200', 200),
        ('Portra400', 400),
        ('Ektar100', 100),
        ('Cinestill800T', 800),
        ('Velvia50', 50),
        ('Gold200', 200),
        ('ProImage100', 100),
        ('Superia400', 400)
    ]
    
    print("=" * 80)
    print("Phos 彩色膠片中階物理模式驗證報告")
    print("=" * 80)
    print()
    
    all_passed = True
    
    for film_name, expected_iso in main_color_films:
        profile = get_film_profile(film_name)
        
        # 驗證 physics_mode
        if profile.physics_mode != PhysicsMode.PHYSICAL:
            print(f"❌ {film_name}: physics_mode 不是 PHYSICAL (實際: {profile.physics_mode})")
            all_passed = False
            continue
        
        # 驗證參數存在
        if not profile.bloom_params:
            print(f"❌ {film_name}: bloom_params 缺失")
            all_passed = False
            continue
        
        if not profile.halation_params:
            print(f"❌ {film_name}: halation_params 缺失")
            all_passed = False
            continue
        
        if not profile.wavelength_bloom_params:
            print(f"❌ {film_name}: wavelength_bloom_params 缺失")
            all_passed = False
            continue
        
        # 輸出配置資訊
        scattering_ratio = profile.bloom_params.scattering_ratio  # Physical 模式使用 scattering_ratio
        energy_fraction = profile.halation_params.energy_fraction
        ah_absorption = profile.halation_params.ah_absorption
        has_ah_layer = ah_absorption > 0.5  # 推測是否有 AH 層
        
        print(f"✅ {film_name:18s} (ISO {expected_iso:3d})")
        print(f"   ├─ Scattering Ratio: {scattering_ratio:.1%}")
        print(f"   ├─ Halation Energy: {energy_fraction:.1%}")
        print(f"   ├─ AH Layer: {'有' if has_ah_layer else '無（Cinestill 類型）'}")
        print(f"   └─ AH Absorption: {ah_absorption:.1%}")
        print()
    
    print("=" * 80)
    if all_passed:
        print("🎉 所有彩色膠片中階物理模式驗證通過！")
    else:
        print("⚠️  部分膠片配置有問題，請檢查 film_models.py")
    print("=" * 80)
    
    return all_passed


def show_iso_scatter_mapping():
    """顯示 ISO → 散射比例映射表"""
    
    print()
    print("=" * 80)
    print("ISO → 散射比例映射表")
    print("=" * 80)
    print()
    print("| ISO  | 散射比例 | 說明                           |")
    print("|------|---------|--------------------------------|")
    print("| 50   | 4.5%    | 極細膩（風景膠片）             |")
    print("| 100  | 5.5%    | 標準日光膠片                   |")
    print("| 200  | 6.5%    | 溫暖散射，金黃色調             |")
    print("| 400  | 7.0%    | 經典人像/街拍                  |")
    print("| 800  | 9.0%    | 明顯光暈（高感光度）           |")
    print()
    print("說明: 散射比例越高，高光溢出越明顯，光暈越大")
    print("=" * 80)
    print()


if __name__ == "__main__":
    # 運行測試
    passed = test_all_color_films()
    
    # 顯示映射表
    show_iso_scatter_mapping()
    
    # 返回狀態碼
    exit(0 if passed else 1)
