#!/usr/bin/env python3
"""
Physical Mode 通道順序測試

目的：追蹤 Physical Mode 下從輸入到輸出的完整通道順序
"""

import numpy as np
import cv2
import sys
from pathlib import Path

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent))

import film_models
from film_models import PhysicsMode

# 創建簡單的藍色測試影像（純藍 BGR=[255, 0, 0]）
def create_blue_test_image():
    """創建 100x100 純藍色影像（BGR 格式）"""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :, 0] = 255  # B channel
    img[:, :, 1] = 0    # G channel
    img[:, :, 2] = 0    # R channel
    return img

def test_channel_order_at_merge():
    """測試最終 merge 點的通道順序"""
    print("=" * 60)
    print("測試：Physical Mode 通道順序")
    print("=" * 60)
    
    # 1. 創建測試影像
    img_bgr = create_blue_test_image()
    print(f"\n1. 輸入影像（BGR 格式）:")
    print(f"   B channel mean: {img_bgr[:, :, 0].mean():.1f}")
    print(f"   G channel mean: {img_bgr[:, :, 1].mean():.1f}")
    print(f"   R channel mean: {img_bgr[:, :, 2].mean():.1f}")
    
    # 2. 模擬通道分離（OpenCV 順序）
    b, g, r = cv2.split(img_bgr)
    print(f"\n2. cv2.split() 後:")
    print(f"   b (blue layer) mean: {b.mean():.1f}")
    print(f"   g (green layer) mean: {g.mean():.1f}")
    print(f"   r (red layer) mean: {r.mean():.1f}")
    
    # 3. 模擬處理後的結果（假設保持相同）
    result_b = b.astype(np.float32) / 255.0
    result_g = g.astype(np.float32) / 255.0
    result_r = r.astype(np.float32) / 255.0
    
    print(f"\n3. 處理後的通道（0-1 範圍）:")
    print(f"   result_b mean: {result_b.mean():.3f}")
    print(f"   result_g mean: {result_g.mean():.3f}")
    print(f"   result_r mean: {result_r.mean():.3f}")
    
    # 4. 模擬 film_spectra 路徑（如果啟用）
    use_film_spectra = True
    if use_film_spectra:
        print(f"\n4. 啟用膠片光譜處理:")
        
        # 組合成 RGB（注意：這裡是 RGB 順序！）
        lux_combined = np.stack([result_r, result_g, result_b], axis=2)
        print(f"   lux_combined shape: {lux_combined.shape}")
        print(f"   lux_combined[:,:,0] (R) mean: {lux_combined[:, :, 0].mean():.3f}")
        print(f"   lux_combined[:,:,1] (G) mean: {lux_combined[:, :, 1].mean():.3f}")
        print(f"   lux_combined[:,:,2] (B) mean: {lux_combined[:, :, 2].mean():.3f}")
        
        # 模擬 color_utils.spectrum_to_rgb_with_film() 返回 RGB
        # 這裡為了測試，我們假設它原封不動返回（實際會有轉換）
        rgb_with_film = lux_combined.copy()  # 實際會經過 spectrum 轉換
        
        # 重新賦值
        result_r = rgb_with_film[:, :, 0]
        result_g = rgb_with_film[:, :, 1]
        result_b = rgb_with_film[:, :, 2]
        
        print(f"\n5. spectrum_to_rgb_with_film() 後:")
        print(f"   result_r mean: {result_r.mean():.3f}")
        print(f"   result_g mean: {result_g.mean():.3f}")
        print(f"   result_b mean: {result_b.mean():.3f}")
    
    # 6. 轉換為 uint8 並合併（BGR 順序）
    combined_r = (result_r * 255).astype(np.uint8)
    combined_g = (result_g * 255).astype(np.uint8)
    combined_b = (result_b * 255).astype(np.uint8)
    
    print(f"\n6. 轉換為 uint8:")
    print(f"   combined_r mean: {combined_r.mean():.1f}")
    print(f"   combined_g mean: {combined_g.mean():.1f}")
    print(f"   combined_b mean: {combined_b.mean():.1f}")
    
    final_image = cv2.merge([combined_b, combined_g, combined_r])
    
    print(f"\n7. 最終影像（BGR 格式）:")
    print(f"   final_image[:,:,0] (B) mean: {final_image[:, :, 0].mean():.1f}")
    print(f"   final_image[:,:,1] (G) mean: {final_image[:, :, 1].mean():.1f}")
    print(f"   final_image[:,:,2] (R) mean: {final_image[:, :, 2].mean():.1f}")
    
    # 8. 測試顯示路徑（BGR → RGB 轉換）
    film_rgb = cv2.cvtColor(final_image, cv2.COLOR_BGR2RGB)
    
    print(f"\n8. 顯示轉換後（RGB 格式）:")
    print(f"   film_rgb[:,:,0] (R) mean: {film_rgb[:, :, 0].mean():.1f}")
    print(f"   film_rgb[:,:,1] (G) mean: {film_rgb[:, :, 1].mean():.1f}")
    print(f"   film_rgb[:,:,2] (B) mean: {film_rgb[:, :, 2].mean():.1f}")
    
    # 驗證
    print(f"\n" + "=" * 60)
    print("驗證結果:")
    if film_rgb[:, :, 2].mean() > 200:  # Blue channel should be high
        print("✅ PASS: 藍色通道在 RGB 格式中正確（channel 2 高）")
        return True
    else:
        print("❌ FAIL: 藍色通道錯誤！")
        print(f"   預期: film_rgb[:,:,2] (B) > 200")
        print(f"   實際: film_rgb[:,:,2] (B) = {film_rgb[:, :, 2].mean():.1f}")
        return False

def test_with_actual_color_utils():
    """使用實際的 color_utils 測試"""
    print("\n" + "=" * 60)
    print("測試：使用實際 color_utils 的轉換")
    print("=" * 60)
    
    try:
        import color_utils
        
        # 創建純藍色影像（RGB 格式，值域 0-1）
        img_rgb = np.zeros((100, 100, 3), dtype=np.float32)
        img_rgb[:, :, 2] = 1.0  # B channel = 1.0
        
        print(f"\n輸入（RGB 格式，0-1 範圍）:")
        print(f"   R mean: {img_rgb[:, :, 0].mean():.3f}")
        print(f"   G mean: {img_rgb[:, :, 1].mean():.3f}")
        print(f"   B mean: {img_rgb[:, :, 2].mean():.3f}")
        
        # RGB → Spectrum
        spectrum = color_utils.rgb_to_spectrum(img_rgb)
        print(f"\n光譜轉換:")
        print(f"   spectrum shape: {spectrum.shape}")
        print(f"   spectrum mean: {spectrum.mean():.3f}")
        
        # Spectrum → RGB (with film)
        rgb_with_film = color_utils.spectrum_to_rgb_with_film(
            spectrum, 
            film_name='Portra400',
            apply_gamma=True
        )
        
        print(f"\n膠片光譜處理後（RGB 格式）:")
        print(f"   R mean: {rgb_with_film[:, :, 0].mean():.3f}")
        print(f"   G mean: {rgb_with_film[:, :, 1].mean():.3f}")
        print(f"   B mean: {rgb_with_film[:, :, 2].mean():.3f}")
        
        # 驗證：藍色輸入應該產生藍色輸出
        if rgb_with_film[:, :, 2].mean() > rgb_with_film[:, :, 0].mean():
            print("\n✅ PASS: 藍色輸入產生藍色輸出")
            return True
        else:
            print("\n❌ FAIL: 藍色輸入產生錯誤輸出！")
            print(f"   B mean ({rgb_with_film[:, :, 2].mean():.3f}) 應該 > R mean ({rgb_with_film[:, :, 0].mean():.3f})")
            return False
            
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 執行測試
    result1 = test_channel_order_at_merge()
    result2 = test_with_actual_color_utils()
    
    print("\n" + "=" * 60)
    print("總結:")
    print(f"  通道順序測試: {'✅ PASS' if result1 else '❌ FAIL'}")
    print(f"  color_utils 測試: {'✅ PASS' if result2 else '❌ FAIL'}")
    print("=" * 60)
    
    sys.exit(0 if (result1 and result2) else 1)
