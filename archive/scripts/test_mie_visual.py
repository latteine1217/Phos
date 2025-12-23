"""
Phase 5.4 視覺驗證腳本

對比 Portra400_MediumPhysics（經驗公式）vs Portra400_MediumPhysics_Mie（Mie 查表）

用法：
    python3 scripts/test_mie_visual.py <input_image>
    
輸出：
    - output_empirical.jpg (經驗公式)
    - output_mie.jpg (Mie 查表)
    - output_diff.jpg (差異圖)
"""

import sys
import numpy as np
import cv2
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from film_models import get_film_profile
# from Phos_0_3_0 import process_image  # 需要從主程式導入處理函數（TODO）

def load_image(path: str) -> np.ndarray:
    """載入影像並轉為 RGB float32 (0-1)"""
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"無法載入影像: {path}")
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img_rgb.astype(np.float32) / 255.0


def save_image(img: np.ndarray, path: str):
    """儲存影像 (0-1 float32 → 0-255 uint8)"""
    img_uint8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    img_bgr = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2BGR)
    cv2.imwrite(path, img_bgr)
    print(f"✅ 已儲存: {path}")


def compute_difference(img1: np.ndarray, img2: np.ndarray, scale: float = 5.0) -> np.ndarray:
    """計算差異圖（放大對比）"""
    diff = np.abs(img1 - img2) * scale
    diff = np.clip(diff, 0, 1)
    return diff


def main():
    if len(sys.argv) < 2:
        print("用法: python3 scripts/test_mie_visual.py <input_image>")
        print("範例: python3 scripts/test_mie_visual.py test_images/sky.jpg")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    print("=" * 70)
    print("  Phase 5.4 Mie 散射查表 - 視覺對比測試")
    print("=" * 70)
    
    # 1. 載入影像
    print(f"\n[1] 載入影像: {input_path}")
    img = load_image(input_path)
    print(f"    尺寸: {img.shape[1]}x{img.shape[0]}")
    
    # 2. 載入配置
    print("\n[2] 載入膠片配置")
    film_empirical = get_film_profile("Portra400_MediumPhysics")
    film_mie = get_film_profile("Portra400_MediumPhysics_Mie")
    
    use_mie_emp = film_empirical.wavelength_bloom_params.use_mie_lookup if film_empirical.wavelength_bloom_params else False
    use_mie_mie = film_mie.wavelength_bloom_params.use_mie_lookup if film_mie.wavelength_bloom_params else False
    print(f"    經驗公式: use_mie_lookup={use_mie_emp}")
    print(f"    Mie 查表: use_mie_lookup={use_mie_mie}")
    
    # 3. 處理影像（需要實作簡化的處理流程）
    print("\n[3] 處理影像")
    print("    ⚠️  注意: 此腳本需要從主程式導入處理函數")
    print("    建議: 使用 Streamlit UI 進行視覺對比（streamlit run Phos_0.3.0.py）")
    
    # 4. 輸出指引
    print("\n[4] 視覺對比步驟（Streamlit UI）")
    print("    1. 啟動 UI: streamlit run Phos_0.3.0.py")
    print("    2. 上傳測試影像（建議：藍天、高光場景）")
    print("    3. 選擇「Portra400_MediumPhysics」處理並下載")
    print("    4. 選擇「Portra400_MediumPhysics_Mie」處理並下載")
    print("    5. 比較兩者的 Bloom 效果差異（尤其藍光通道）")
    
    print("\n" + "=" * 70)
    print("  提示: 主要觀察指標")
    print("=" * 70)
    print("  - 藍光 Bloom 強度（Mie 理論預測較弱，η ∝ λ^-p）")
    print("  - 紅光 Bloom 強度（Mie 理論預測較強或相近）")
    print("  - 整體能量分布（兩者應相似，但細節不同）")
    print("  - 高光過渡自然度")
    print("=" * 70)


if __name__ == "__main__":
    main()
