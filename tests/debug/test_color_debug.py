#!/usr/bin/env python3
"""
最小測試案例：檢測顏色通道反轉問題
測試藍天（BGR=[255,100,100]）是否正確處理
"""

import numpy as np
import cv2
from film_models import get_film_profile
import sys

# 添加當前目錄到 Python path
sys.path.insert(0, '/Users/latteine/Documents/coding/Phos')

# 直接載入模組
import importlib.util
spec = importlib.util.spec_from_file_location("phos", "/Users/latteine/Documents/coding/Phos/Phos_0.3.0.py")
phos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phos)

# 導入必要函數
spectral_response = phos.spectral_response
apply_wavelength_bloom = phos.apply_wavelength_bloom
apply_halation = phos.apply_halation

def test_blue_sky():
    """測試藍天像素處理"""
    
    # 創建測試圖像：上半部藍天，下半部灰色建築
    test_img = np.zeros((200, 200, 3), dtype=np.uint8)
    test_img[:100, :, :] = [255, 100, 100]  # BGR: 藍天（高B，低GR）
    test_img[100:, :, :] = [128, 128, 128]  # BGR: 灰色建築
    
    print("=" * 60)
    print("測試輸入影像")
    print("=" * 60)
    print(f"藍天像素 [50, 100]: BGR = {test_img[50, 100]}")
    print(f"建築像素 [150, 100]: BGR = {test_img[150, 100]}")
    print()
    
    # 載入底片參數
    film = get_film_profile("Portra400_MediumPhysics")
    
    # 階段 1: Spectral Response
    print("=" * 60)
    print("階段 1: Spectral Response")
    print("=" * 60)
    
    # 手動拆分通道以追蹤
    b, g, r = cv2.split(test_img.astype(np.float32) / 255.0)
    
    print(f"輸入通道（歸一化）:")
    print(f"  R channel [50,100]: {r[50, 100]:.3f} (應該 LOW，因為藍天)")
    print(f"  G channel [50,100]: {g[50, 100]:.3f} (應該 LOW)")
    print(f"  B channel [50,100]: {b[50, 100]:.3f} (應該 HIGH，因為藍天)")
    print()
    
    # 調用 spectral_response
    try:
        response_r, response_g, response_b, gray = spectral_response(test_img, film)
        
        print(f"Spectral Response 輸出:")
        print(f"  response_r [50,100]: {response_r[50, 100]:.3f} (應該 LOW)")
        print(f"  response_g [50,100]: {response_g[50, 100]:.3f} (應該 LOW)")
        print(f"  response_b [50,100]: {response_b[50, 100]:.3f} (應該 HIGH)")
        print()
        
        # 檢查是否反轉
        if response_r[50, 100] > response_b[50, 100]:
            print("⚠️  WARNING: response_r > response_b 在藍天區域！")
            print("    這表示紅色通道比藍色通道強，顏色已經反轉！")
            print("    BUG 位置：spectral_response() 函數")
        else:
            print("✅ Spectral response 正確：藍天有高 B 通道")
        print()
        
    except Exception as e:
        print(f"❌ spectral_response() 失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 階段 2: Wavelength Bloom
    print("=" * 60)
    print("階段 2: Wavelength Bloom")
    print("=" * 60)
    
    try:
        bloom_r, bloom_g, bloom_b = apply_wavelength_bloom(
            response_r, response_g, response_b,
            film.wavelength_bloom_params,
            film.bloom_params
        )
        
        print(f"Wavelength Bloom 輸出:")
        print(f"  bloom_r [50,100]: {bloom_r[50, 100]:.3f} (應該 LOW)")
        print(f"  bloom_g [50,100]: {bloom_g[50, 100]:.3f} (應該 LOW)")
        print(f"  bloom_b [50,100]: {bloom_b[50, 100]:.3f} (應該 HIGH)")
        print()
        
        if bloom_r[50, 100] > bloom_b[50, 100]:
            print("⚠️  WARNING: bloom_r > bloom_b 在藍天區域！")
            print("    BUG 位置：apply_wavelength_bloom() 函數")
        else:
            print("✅ Wavelength bloom 正確")
        print()
        
    except Exception as e:
        print(f"❌ apply_wavelength_bloom() 失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 階段 3: Halation
    print("=" * 60)
    print("階段 3: Halation")
    print("=" * 60)
    
    try:
        print(f"Halation 參數:")
        print(f"  transmittance_r: {film.halation_params.transmittance_r}")
        print(f"  transmittance_g: {film.halation_params.transmittance_g}")
        print(f"  transmittance_b: {film.halation_params.transmittance_b}")
        print()
        
        halation_r = apply_halation(bloom_r.copy(), film.halation_params, wavelength=650.0)
        halation_g = apply_halation(bloom_g.copy(), film.halation_params, wavelength=550.0)
        halation_b = apply_halation(bloom_b.copy(), film.halation_params, wavelength=450.0)
        
        print(f"Halation 輸出:")
        print(f"  halation_r [50,100]: {halation_r[50, 100]:.3f} (應該 LOW)")
        print(f"  halation_g [50,100]: {halation_g[50, 100]:.3f} (應該 LOW)")
        print(f"  halation_b [50,100]: {halation_b[50, 100]:.3f} (應該 HIGH)")
        print()
        
        if halation_r[50, 100] > halation_b[50, 100]:
            print("⚠️  WARNING: halation_r > halation_b 在藍天區域！")
            print("    BUG 位置：apply_halation() 函數或波長參數")
        else:
            print("✅ Halation 正確")
        print()
        
    except Exception as e:
        print(f"❌ apply_halation() 失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 最終合併
    print("=" * 60)
    print("最終合併")
    print("=" * 60)
    
    # 模擬 cv2.merge([b, g, r])
    final = cv2.merge([halation_b, halation_g, halation_r])
    final_uint8 = (np.clip(final, 0, 1) * 255).astype(np.uint8)
    
    print(f"最終輸出 [50,100]: BGR = {final_uint8[50, 100]}")
    print(f"  預期：B 應該最高（接近 255）")
    print(f"  實際：B={final_uint8[50, 100, 0]}, G={final_uint8[50, 100, 1]}, R={final_uint8[50, 100, 2]}")
    print()
    
    if final_uint8[50, 100, 2] > final_uint8[50, 100, 0]:
        print("❌ 確認 BUG：紅色通道 > 藍色通道！")
        print("   藍天被渲染成紅色/橙色")
    else:
        print("✅ 正確：藍色通道保持最高")
    
    # 保存測試圖像
    cv2.imwrite('/Users/latteine/Documents/coding/Phos/test_color_debug_output.png', final_uint8)
    print()
    print(f"測試圖像已保存：test_color_debug_output.png")
    print("=" * 60)

if __name__ == "__main__":
    test_blue_sky()
