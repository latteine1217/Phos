"""
ISO Scaling Visual Verification Script

驗證 ISO 統一化系統的視覺與定量指標：
1. 生成標準測試影像（漸層 + 高頻紋理）
2. 處理 ISO 100/200/400/800/1600/3200（3 種 film_type）
3. 生成對比網格（6 ISO × 3 film_type = 18 張）
4. 測量 RMS 顆粒度並繪製曲線
5. 驗證單調性與物理合理性

Usage:
    python scripts/visualize_iso_scaling.py
    
Output:
    results/iso_scaling_comparison.png  # 視覺對比網格
    results/iso_scaling_metrics.json    # 定量指標
    results/iso_scaling_plot.png        # RMS 顆粒度曲線
"""

import numpy as np
import cv2
import matplotlib.pyplot as plt
import json
from pathlib import Path
from typing import Dict, Tuple, List
import sys

# 添加專案根目錄到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from film_models import create_film_profile_from_iso, FilmProfile

# 導入核心處理函數（需要從 Phos_0.3.0.py 中提取關鍵函數）
# 為簡化測試，直接實現簡化版處理流程
def process_simple_film_test(image: np.ndarray, film: FilmProfile) -> np.ndarray:
    """
    簡化版膠片處理（用於測試顆粒效果）
    
    僅應用核心效果：
    1. Spectral response（簡化為 gamma 調整）
    2. Grain（Poisson noise）
    3. Tone mapping（power curve）
    
    Args:
        image: RGB 影像，shape (H, W, 3)，範圍 [0, 1]
        film: FilmProfile 配置
    
    Returns:
        處理後影像，shape (H, W, 3)，範圍 [0, 1]
    """
    img = image.copy()
    
    # 1. Gamma adjustment (模擬 spectral response)
    img = np.power(img, 0.8)
    
    # 2. 添加顆粒（Poisson + Gaussian noise）
    if film.grain_params and film.grain_params.intensity > 0:
        grain_intensity = film.grain_params.intensity
        
        # Poisson noise (模擬銀鹽顆粒)
        img_scaled = (img * 255).astype(np.float32)
        lam = img_scaled + 1e-6  # 避免零值
        poisson = np.random.poisson(lam).astype(np.float32) / 255.0
        
        # Gaussian noise (高頻紋理)
        gaussian = np.random.normal(0, grain_intensity * 0.02, img.shape).astype(np.float32)
        
        # 混合顆粒
        img = poisson * (1 - grain_intensity) + img * grain_intensity + gaussian
        img = np.clip(img, 0, 1)
    
    # 3. Tone mapping (簡化 S 曲線)
    if film.tone_params:
        gamma = film.tone_params.gamma
        img = np.power(img, 1.0 / gamma)
    
    return img

# ==================== 配置參數 ====================
ISO_LEVELS = [100, 200, 400, 800, 1600, 3200]
FILM_TYPES = ["fine_grain", "standard", "high_speed"]
OUTPUT_DIR = Path("results")
OUTPUT_DIR.mkdir(exist_ok=True)

# 測試影像尺寸
TEST_IMG_SIZE = (512, 512)  # 小尺寸加快處理速度


# ==================== 測試影像生成 ====================
def generate_test_image() -> np.ndarray:
    """
    生成標準測試影像：包含漸層與高頻紋理
    
    設計：
    - 左半部：水平漸層（0-1），用於測試色調映射
    - 右半部：棋盤紋理 + 漸層，用於測試顆粒可見度
    
    Returns:
        RGB 影像，shape (H, W, 3)，範圍 [0, 1]
    """
    H, W = TEST_IMG_SIZE
    img = np.zeros((H, W, 3), dtype=np.float32)
    
    # 左半部：水平漸層（測試色調映射）
    gradient = np.linspace(0, 1, W // 2).reshape(1, -1, 1)
    gradient = np.repeat(gradient, H, axis=0)
    img[:, :W//2, :] = gradient
    
    # 右半部：高頻棋盤紋理
    checker_size = 8
    checker = np.indices((H, W // 2)) // checker_size
    checker = (checker[0] + checker[1]) % 2
    checker = checker.astype(np.float32) * 0.5 + 0.25  # [0.25, 0.75] 範圍
    
    # 疊加漸層
    vertical_gradient = np.linspace(0.3, 0.7, H).reshape(-1, 1)
    checker = checker * vertical_gradient
    
    img[:, W//2:, 0] = checker * 0.9  # R
    img[:, W//2:, 1] = checker * 1.0  # G
    img[:, W//2:, 2] = checker * 0.8  # B
    
    return img


def measure_rms_granularity(image: np.ndarray, roi_size: int = 64) -> float:
    """
    測量影像中心區域的 RMS 顆粒度
    
    方法：
    1. 提取中心 ROI（均勻灰階區域）
    2. 高通濾波（去除低頻趨勢）
    3. 計算 RMS（高頻成分標準差）
    
    Args:
        image: RGB 影像，範圍 [0, 1]
        roi_size: ROI 邊長（像素）
    
    Returns:
        RMS 顆粒度（0-1 範圍）
    """
    # 轉灰階
    gray = cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    
    # 提取中心 ROI（選擇棋盤區域中的均勻塊）
    H, W = gray.shape
    cx, cy = W * 3 // 4, H // 2  # 右半部中心
    roi = gray[cy - roi_size//2 : cy + roi_size//2,
               cx - roi_size//2 : cx + roi_size//2]
    
    # 高通濾波（移除低頻趨勢）
    blur = cv2.GaussianBlur(roi, (11, 11), 5)
    high_freq = roi - blur
    
    # 計算 RMS
    rms = np.sqrt(np.mean(high_freq ** 2))
    
    return rms


# ==================== ISO 掃描處理 ====================
def process_iso_sweep(test_img: np.ndarray) -> Dict[Tuple[int, str], Dict]:
    """
    處理所有 ISO 與 film_type 組合
    
    Args:
        test_img: 測試影像，shape (H, W, 3)
    
    Returns:
        results = {
            (iso, film_type): {
                "image": np.ndarray,  # 處理後影像
                "rms_granularity": float,
                "grain_intensity": float,
                "scattering_ratio": float
            }
        }
    """
    results = {}
    total = len(ISO_LEVELS) * len(FILM_TYPES)
    count = 0
    
    print("=" * 60)
    print("開始 ISO 掃描處理...")
    print("=" * 60)
    
    for iso in ISO_LEVELS:
        for film_type in FILM_TYPES:
            count += 1
            print(f"[{count}/{total}] 處理 ISO {iso} / {film_type}...", end=" ")
            
            # 創建膠片配置
            film_name = f"Test_{film_type}_{iso}"
            film = create_film_profile_from_iso(
                name=film_name,
                iso=iso,
                film_type=film_type,
                tone_mapping_style="balanced"
            )
            
            # 處理影像
            processed = process_simple_film_test(test_img, film)
            
            # 測量顆粒度
            rms = measure_rms_granularity(processed)
            
            # 儲存結果（添加防護性檢查）
            grain_intensity = film.grain_params.intensity if film.grain_params else 0.0
            scattering_ratio = film.bloom_params.scattering_ratio if film.bloom_params else 0.0
            
            results[(iso, film_type)] = {
                "image": processed,
                "rms_granularity": rms,
                "grain_intensity": grain_intensity,
                "scattering_ratio": scattering_ratio
            }
            
            print(f"RMS={rms:.4f}, grain={grain_intensity:.3f}")
    
    print("=" * 60)
    print("處理完成！")
    print("=" * 60)
    
    return results


# ==================== 視覺化生成 ====================
def create_comparison_grid(results: Dict, test_img: np.ndarray):
    """
    生成 6×3 對比網格（ISO × film_type）
    
    Layout:
    - 行：ISO 100 → 3200（由上至下）
    - 列：fine_grain, standard, high_speed（由左至右）
    - 左上角：原始影像
    """
    n_rows = len(ISO_LEVELS) + 1  # +1 for original
    n_cols = len(FILM_TYPES)
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 18))
    
    # 第一行：原始影像
    for col in range(n_cols):
        ax = axes[0, col]
        ax.imshow(test_img)
        ax.axis("off")
        if col == 1:
            ax.set_title("Original Test Image", fontsize=14, fontweight="bold")
    
    # ISO 行
    for row, iso in enumerate(ISO_LEVELS, start=1):
        for col, film_type in enumerate(FILM_TYPES):
            ax = axes[row, col]
            
            # 獲取處理結果
            key = (iso, film_type)
            img = results[key]["image"]
            rms = results[key]["rms_granularity"]
            
            # 顯示影像
            ax.imshow(img)
            ax.axis("off")
            
            # 標題
            title = f"ISO {iso}"
            if row == 1:  # 第一行顯示 film_type
                title = f"{film_type.replace('_', ' ').title()}\n{title}"
            ax.set_title(title, fontsize=10)
            
            # 左側顯示 RMS
            if col == 0:
                ax.text(-0.1, 0.5, f"RMS: {rms:.4f}", 
                       transform=ax.transAxes,
                       rotation=90, va='center', fontsize=8)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "iso_scaling_comparison.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ 對比網格已儲存：{output_path}")
    plt.close()


def plot_granularity_curves(results: Dict):
    """
    繪製 RMS 顆粒度 vs ISO 曲線（3 條線：3 種 film_type）
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # === Subplot 1: RMS Granularity vs ISO ===
    ax1 = axes[0]
    for film_type in FILM_TYPES:
        isos = []
        rms_values = []
        for iso in ISO_LEVELS:
            isos.append(iso)
            rms_values.append(results[(iso, film_type)]["rms_granularity"])
        
        ax1.plot(isos, rms_values, marker='o', label=film_type.replace("_", " ").title())
    
    ax1.set_xlabel("ISO", fontsize=12)
    ax1.set_ylabel("RMS Granularity", fontsize=12)
    ax1.set_title("RMS Granularity vs ISO", fontsize=14, fontweight="bold")
    ax1.set_xscale("log")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # === Subplot 2: Grain Intensity vs ISO ===
    ax2 = axes[1]
    for film_type in FILM_TYPES:
        isos = []
        grain_values = []
        for iso in ISO_LEVELS:
            isos.append(iso)
            grain_values.append(results[(iso, film_type)]["grain_intensity"])
        
        ax2.plot(isos, grain_values, marker='s', label=film_type.replace("_", " ").title())
    
    ax2.set_xlabel("ISO", fontsize=12)
    ax2.set_ylabel("Grain Intensity (Derived)", fontsize=12)
    ax2.set_title("Grain Intensity (Theory) vs ISO", fontsize=14, fontweight="bold")
    ax2.set_xscale("log")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # === Subplot 3: Scattering Ratio vs ISO ===
    ax3 = axes[2]
    for film_type in FILM_TYPES:
        isos = []
        scatter_values = []
        for iso in ISO_LEVELS:
            isos.append(iso)
            scatter_values.append(results[(iso, film_type)]["scattering_ratio"])
        
        ax3.plot(isos, scatter_values, marker='^', label=film_type.replace("_", " ").title())
    
    ax3.set_xlabel("ISO", fontsize=12)
    ax3.set_ylabel("Scattering Ratio", fontsize=12)
    ax3.set_title("Scattering Ratio vs ISO", fontsize=14, fontweight="bold")
    ax3.set_xscale("log")
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "iso_scaling_curves.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ 指標曲線已儲存：{output_path}")
    plt.close()


# ==================== 定量驗證 ====================
def validate_quantitative_criteria(results: Dict) -> Dict[str, bool]:
    """
    驗證定量指標（單調性、物理範圍、film_type 排序）
    
    Returns:
        criteria = {
            "rms_monotonicity": bool,
            "film_type_ordering": bool,
            "grain_intensity_range": bool,
            "scattering_ratio_range": bool
        }
    """
    criteria = {}
    
    # === 1. RMS 單調性（同 film_type 下，ISO ↑ → RMS ↑）===
    monotonic = True
    for film_type in FILM_TYPES:
        rms_series = [results[(iso, film_type)]["rms_granularity"] for iso in ISO_LEVELS]
        for i in range(len(rms_series) - 1):
            if rms_series[i+1] <= rms_series[i]:
                print(f"❌ 單調性失敗：{film_type} ISO {ISO_LEVELS[i]} → {ISO_LEVELS[i+1]}")
                monotonic = False
    criteria["rms_monotonicity"] = monotonic
    
    # === 2. Film type 排序（同 ISO 下，fine_grain < standard < high_speed）===
    ordering = True
    for iso in ISO_LEVELS:
        fine = results[(iso, "fine_grain")]["rms_granularity"]
        standard = results[(iso, "standard")]["rms_granularity"]
        high = results[(iso, "high_speed")]["rms_granularity"]
        if not (fine < standard < high):
            print(f"❌ Film type 排序失敗：ISO {iso}")
            ordering = False
    criteria["film_type_ordering"] = ordering
    
    # === 3. Grain intensity 範圍 [0.03, 0.35] ===
    in_range = True
    for key, val in results.items():
        grain = val["grain_intensity"]
        if not (0.03 <= grain <= 0.35):
            print(f"❌ Grain intensity 超出範圍：{key} = {grain:.3f}")
            in_range = False
    criteria["grain_intensity_range"] = in_range
    
    # === 4. Scattering ratio 範圍 [0.03, 0.15] ===
    in_range = True
    for key, val in results.items():
        scatter = val["scattering_ratio"]
        if not (0.03 <= scatter <= 0.15):
            print(f"❌ Scattering ratio 超出範圍：{key} = {scatter:.4f}")
            in_range = False
    criteria["scattering_ratio_range"] = in_range
    
    return criteria


# ==================== 主流程 ====================
def main():
    print("\n" + "=" * 60)
    print("ISO Scaling Visual Verification")
    print("Task: TASK-007-P1-2 Phase 4")
    print("=" * 60 + "\n")
    
    # 1. 生成測試影像
    print("⏳ 生成測試影像...")
    test_img = generate_test_image()
    cv2.imwrite(str(OUTPUT_DIR / "test_image.png"), (test_img[:, :, ::-1] * 255).astype(np.uint8))
    print("✅ 測試影像已儲存：results/test_image.png\n")
    
    # 2. 處理 ISO 掃描
    results = process_iso_sweep(test_img)
    
    # 3. 生成視覺對比
    print("\n⏳ 生成視覺對比網格...")
    create_comparison_grid(results, test_img)
    
    # 4. 繪製指標曲線
    print("⏳ 繪製 RMS 顆粒度曲線...")
    plot_granularity_curves(results)
    
    # 5. 定量驗證
    print("\n" + "=" * 60)
    print("定量指標驗證")
    print("=" * 60)
    criteria = validate_quantitative_criteria(results)
    
    for name, passed in criteria.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name.replace('_', ' ').title()}")
    
    # 6. 儲存 JSON 結果
    metrics = {}
    for (iso, film_type), data in results.items():
        key = f"ISO{iso}_{film_type}"
        metrics[key] = {
            "iso": iso,
            "film_type": film_type,
            "rms_granularity": float(data["rms_granularity"]),
            "grain_intensity": float(data["grain_intensity"]),
            "scattering_ratio": float(data["scattering_ratio"])
        }
    
    metrics["validation_criteria"] = criteria
    
    json_path = OUTPUT_DIR / "iso_scaling_metrics.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 定量指標已儲存：{json_path}")
    
    # 7. 總結
    print("\n" + "=" * 60)
    print("驗證完成！")
    print("=" * 60)
    print(f"總處理影像數：{len(results)}")
    print(f"通過指標數：{sum(criteria.values())}/{len(criteria)}")
    
    if all(criteria.values()):
        print("\n🎉 所有定量指標通過！ISO 統一化系統驗證成功。")
    else:
        print("\n⚠️  部分指標未通過，請檢查視覺對比與曲線。")
    
    print(f"\n輸出檔案：")
    print(f"  - results/test_image.png")
    print(f"  - results/iso_scaling_comparison.png")
    print(f"  - results/iso_scaling_curves.png")
    print(f"  - results/iso_scaling_metrics.json")


if __name__ == "__main__":
    main()
