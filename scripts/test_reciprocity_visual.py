"""
視覺測試：reciprocity failure 效果驗證

生成測試影像並應用不同膠片的 reciprocity failure 效果，用於視覺驗證。

執行方式：
    python scripts/test_reciprocity_visual.py

輸出：
    - test_outputs/reciprocity_visual/input_*.png
    - test_outputs/reciprocity_visual/*_t*.png
"""

import numpy as np
import cv2
import os
from film_models import get_film_profile
from reciprocity_failure import apply_reciprocity_failure

# 創建輸出目錄
OUTPUT_DIR = "test_outputs/reciprocity_visual"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_gradient_image(height=512, width=512):
    """創建水平亮度漸層影像"""
    img = np.zeros((height, width, 3), dtype=np.float32)
    for x in range(width):
        img[:, x, :] = x / (width - 1)
    return img


def create_color_bars(height=512, width=512):
    """創建色塊測試影像"""
    img = np.zeros((height, width, 3), dtype=np.float32)
    
    # 分為 6 個色塊
    bar_width = width // 6
    
    # 紅色
    img[:, 0:bar_width, 0] = 0.8
    
    # 黃色（紅+綠）
    img[:, bar_width:2*bar_width, 0] = 0.8
    img[:, bar_width:2*bar_width, 1] = 0.8
    
    # 綠色
    img[:, 2*bar_width:3*bar_width, 1] = 0.8
    
    # 青色（綠+藍）
    img[:, 3*bar_width:4*bar_width, 1] = 0.8
    img[:, 3*bar_width:4*bar_width, 2] = 0.8
    
    # 藍色
    img[:, 4*bar_width:5*bar_width, 2] = 0.8
    
    # 白色
    img[:, 5*bar_width:, :] = 0.8
    
    return img


def create_gray_scale(height=512, width=512, steps=10):
    """創建階調測試影像"""
    img = np.zeros((height, width, 3), dtype=np.float32)
    step_height = height // steps
    
    for i in range(steps):
        value = i / (steps - 1)
        img[i*step_height:(i+1)*step_height, :, :] = value
    
    return img


def save_image(img, filename):
    """儲存影像（float32 [0,1] → uint8 [0,255]）"""
    img_uint8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    # OpenCV 使用 BGR，但我們存 RGB
    cv2.imwrite(filename, cv2.cvtColor(img_uint8, cv2.COLOR_RGB2BGR))
    print(f"✅ 已儲存: {filename}")


def test_film_reciprocity_visual():
    """測試不同膠片的 reciprocity failure 視覺效果"""
    
    print("=== Reciprocity Failure 視覺測試 ===\n")
    
    # 測試影像
    test_images = {
        "gradient": create_gradient_image(),
        "color_bars": create_color_bars(),
        "gray_scale": create_gray_scale(),
    }
    
    # 儲存輸入影像
    for name, img in test_images.items():
        save_image(img, f"{OUTPUT_DIR}/input_{name}.png")
    
    # 測試膠片
    films = ["Portra400", "Velvia50", "HP5Plus400"]
    
    # 測試曝光時間
    exposure_times = [1, 10, 30, 60]
    
    print("\n=== 處理中 ===\n")
    
    for film_name in films:
        film = get_film_profile(film_name)
        film.reciprocity_params.enabled = True
        is_color = (film.reciprocity_params.p_mono is None)
        
        print(f"\n【{film_name}】")
        
        for img_name, test_img in test_images.items():
            # 黑白膠片需轉換為單通道
            if not is_color:
                # 使用 luminance 轉換
                test_img_bw = 0.2126 * test_img[:,:,0] + 0.7152 * test_img[:,:,1] + 0.0722 * test_img[:,:,2]
                test_img_process = test_img_bw[:,:,np.newaxis]
            else:
                test_img_process = test_img.copy()
            
            for t in exposure_times:
                result = apply_reciprocity_failure(
                    test_img_process.copy(),
                    t,
                    film.reciprocity_params,
                    is_color=is_color
                )
                
                # 黑白結果轉回 RGB 顯示
                if not is_color:
                    result_display = np.repeat(result, 3, axis=2)
                else:
                    result_display = result
                
                # 計算亮度損失
                loss = (1 - np.mean(result) / np.mean(test_img_process)) * 100
                
                filename = f"{OUTPUT_DIR}/{film_name}_{img_name}_t{t}s.png"
                save_image(result_display, filename)
                print(f"  {img_name} @ {t}s: 亮度損失 {loss:.1f}%")
    
    print("\n=== 視覺測試完成 ===")
    print(f"輸出目錄: {OUTPUT_DIR}")
    print(f"總計影像: {len(os.listdir(OUTPUT_DIR))} 張")


def test_exposure_time_series():
    """測試同一膠片不同曝光時間的連續效果"""
    
    print("\n\n=== 曝光時間序列測試 ===\n")
    
    film = get_film_profile("Portra400")
    film.reciprocity_params.enabled = True
    
    # 創建測試影像（灰卡）
    test_img = np.ones((256, 256, 3), dtype=np.float32) * 0.5
    
    # 連續曝光時間
    times = [0.1, 0.5, 1, 2, 5, 10, 20, 30, 60, 120]
    
    print("曝光時間序列（Portra 400）：")
    for t in times:
        result = apply_reciprocity_failure(test_img.copy(), t, film.reciprocity_params, is_color=True)
        loss = (1 - np.mean(result) / 0.5) * 100
        
        filename = f"{OUTPUT_DIR}/series_Portra400_t{t:.1f}s.png"
        save_image(result, filename)
        print(f"  t = {t:6.1f}s → 亮度損失 {loss:5.1f}%")
    
    print(f"\n✅ 序列測試完成")


def compare_films_side_by_side():
    """並排比較不同膠片"""
    
    print("\n\n=== 膠片並排比較 ===\n")
    
    films = {
        "Portra400": get_film_profile("Portra400"),
        "Velvia50": get_film_profile("Velvia50"),
        "HP5Plus400": get_film_profile("HP5Plus400"),
    }
    
    # 測試影像
    test_img = create_color_bars(height=256, width=768)
    
    # 30s 長曝光
    t = 30.0
    
    results = []
    labels = []
    
    for name, film in films.items():
        film.reciprocity_params.enabled = True
        is_color = (film.reciprocity_params.p_mono is None)
        
        test_img_process = test_img.copy()
        if not is_color:
            # 黑白轉換
            lum = 0.2126 * test_img[:,:,0] + 0.7152 * test_img[:,:,1] + 0.0722 * test_img[:,:,2]
            test_img_process = lum[:,:,np.newaxis]
        
        result = apply_reciprocity_failure(test_img_process, t, film.reciprocity_params, is_color=is_color)
        
        if not is_color:
            result = np.repeat(result, 3, axis=2)
        
        results.append(result)
        loss = (1 - np.mean(result) / np.mean(test_img)) * 100
        labels.append(f"{name} ({loss:.0f}% loss)")
        
        print(f"{name:15s} @ 30s: 亮度損失 {loss:.1f}%")
    
    # 垂直拼接
    combined = np.vstack(results)
    save_image(combined, f"{OUTPUT_DIR}/comparison_30s.png")
    
    print(f"\n✅ 比較影像已儲存")


if __name__ == "__main__":
    test_film_reciprocity_visual()
    test_exposure_time_series()
    compare_films_side_by_side()
    
    print("\n" + "="*50)
    print("✅ 所有視覺測試完成")
    print(f"請檢查輸出目錄: {OUTPUT_DIR}")
    print("="*50)
