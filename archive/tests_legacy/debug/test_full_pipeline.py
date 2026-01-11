#!/usr/bin/env python3
"""
完整流程測試：模擬實際的 Streamlit 處理流程
使用藍天測試圖像
"""

import numpy as np
import cv2
import sys
import importlib.util
from PIL import Image

# 載入 Phos 模組
spec = importlib.util.spec_from_file_location("phos", "/Users/latteine/Documents/coding/Phos/Phos_0.3.0.py")
phos = importlib.util.module_from_spec(spec)
sys.modules['streamlit'] = type(sys)('streamlit')  # Mock streamlit
sys.modules['streamlit'].cache_data = lambda func: func
sys.modules['streamlit'].session_state = {}
spec.loader.exec_module(phos)

from film_models import get_film_profile

def test_full_pipeline():
    """測試完整處理管線"""
    
    print("=" * 70)
    print("完整管線測試：藍天 → Portra400_MediumPhysics")
    print("=" * 70)
    print()
    
    # 1. 創建測試圖像（模擬用戶上傳）
    test_img = np.zeros((400, 400, 3), dtype=np.uint8)
    test_img[:200, :, :] = [255, 100, 100]  # BGR: 藍天（高B，低GR）
    test_img[200:, :, :] = [128, 128, 128]  # BGR: 灰色建築
    
    print(f"1. 輸入圖像（BGR）:")
    print(f"   藍天區域 [100,200]: {test_img[100, 200]}")
    print(f"   建築區域 [300,200]: {test_img[300, 200]}")
    print()
    
    # 2. 獲取底片配置
    film = get_film_profile("Portra400_MediumPhysics")
    print(f"2. 底片配置: {film.name}")
    print(f"   Physics Mode: {film.physics_mode.name if hasattr(film.physics_mode, 'name') else film.physics_mode}")
    print(f"   Wavelength Bloom: {film.wavelength_bloom_params.enabled if film.wavelength_bloom_params else False}")
    print()
    
    # 3. 呼叫 optical_processing（核心處理）
    print("3. 執行 optical_processing...")
    try:
        result = phos.optical_processing(
            test_img, film,
            tone_style="reinhard",
            use_grain=False  # 簡化測試
        )
        
        print(f"   ✅ 處理完成")
        print(f"   輸出 shape: {result.shape}, dtype: {result.dtype}")
        print()
        
    except Exception as e:
        print(f"   ❌ 失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. 檢查輸出顏色
    print("4. 檢查輸出顏色（BGR 格式）:")
    sky_pixel = result[100, 200]
    building_pixel = result[300, 200]
    
    print(f"   藍天區域 [100,200]: B={sky_pixel[0]}, G={sky_pixel[1]}, R={sky_pixel[2]}")
    print(f"   建築區域 [300,200]: B={building_pixel[0]}, G={building_pixel[1]}, R={building_pixel[2]}")
    print()
    
    # 5. 判斷結果
    print("=" * 70)
    if sky_pixel[0] > sky_pixel[2]:  # B > R
        print("✅ 正確：藍天的藍色通道 > 紅色通道")
        print("   輸出圖像應該顯示為藍色天空")
    else:
        print("❌ 錯誤：藍天的紅色通道 > 藍色通道")
        print("   輸出圖像會顯示為紅色/橙色天空 ← BUG!")
    print("=" * 70)
    print()
    
    # 6. 保存測試圖像
    cv2.imwrite('test_full_pipeline_output_bgr.png', result)
    print("測試圖像已保存：test_full_pipeline_output_bgr.png")
    
    # 7. 模擬 Streamlit 下載流程（BGR → RGB）
    result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    result_pil = Image.fromarray(result_rgb)
    result_pil.save('test_full_pipeline_output_rgb.png')
    print("RGB 版本已保存：test_full_pipeline_output_rgb.png")
    print()
    
    # 8. 驗證兩個版本
    print("驗證兩個版本的藍天像素:")
    bgr_reloaded = cv2.imread('test_full_pipeline_output_bgr.png')
    rgb_reloaded = np.array(Image.open('test_full_pipeline_output_rgb.png'))
    
    print(f"  BGR 版本 [100,200]: {bgr_reloaded[100, 200]}")
    print(f"  RGB 版本 [100,200]: {rgb_reloaded[100, 200]}")
    print()
    
    # 9. 最終結論
    print("=" * 70)
    print("結論:")
    if bgr_reloaded[100, 200, 0] > bgr_reloaded[100, 200, 2]:
        print("✅ BGR 版本正確（B > R）")
    else:
        print("❌ BGR 版本錯誤（R > B）")
        
    if rgb_reloaded[100, 200, 2] > rgb_reloaded[100, 200, 0]:
        print("✅ RGB 版本正確（B > R）")
    else:
        print("❌ RGB 版本錯誤（R > B）")
    print("=" * 70)

if __name__ == "__main__":
    test_full_pipeline()
