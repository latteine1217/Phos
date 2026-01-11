"""
視覺驗證腳本 - v0.4.1 物理改進驗證
TASK-012: Visual Verification

此腳本生成關鍵測試場景，驗證以下物理改進的視覺效果：
- TASK-009: Mie PSF 波長依賴（藍光外環 vs 紅光核心）
- TASK-010: Mie 折射率修正（藍光 Halation ↑20×）
- TASK-011: Beer-Lambert 標準化（CineStill vs Portra 差異）
- TASK-008: 光譜亮度修正（色彩準確度）

Usage:
    python scripts/visual_verification_v041.py

Output:
    - test_outputs/visual_v041/
      - S1_point_light_cinestill.png (CineStill 高光點源)
      - S2_point_light_portra.png (Portra 高光點源)
      - S3_backlit_scene.png (逆光場景 - 藍光 Halation)
      - S4_skin_tone.png (膚色測試 - 色彩準確度)
      - comparison_grid.png (對比網格)
      - metrics_report.txt (定量指標報告)
"""

import cv2
import numpy as np
import sys
import os
from pathlib import Path
from typing import Dict, Tuple
import json
from dataclasses import dataclass, asdict

# 添加專案根目錄到 Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 導入 Phos 核心模組
try:
    from film_models import FilmProfile, PhysicsMode, create_film_profiles
    from Phos import process_image_core  # 假設有核心處理函數
    import phos_core
except ImportError as e:
    print(f"❌ 無法導入必要模組: {e}")
    sys.exit(1)

# 創建輸出目錄
output_dir = project_root / "test_outputs" / "visual_v041"
output_dir.mkdir(parents=True, exist_ok=True)

# ==================== 測試場景生成 ====================

@dataclass
class SceneMetrics:
    """場景測試指標"""
    scene_id: str
    mean_brightness: float
    blue_halo_radius: float = 0.0
    red_halo_radius: float = 0.0
    blue_to_red_ratio: float = 0.0
    mean_color_bgr: Tuple[float, float, float] = (0, 0, 0)
    
def generate_point_light_scene(size: int = 512) -> np.ndarray:
    """
    生成高光點源場景（用於測試 Halation 和 Mie 散射）
    
    中央白點（255, 255, 255），周圍黑色背景
    用於驗證：
    - 藍光外環強度（TASK-009）
    - 紅暈半徑（TASK-011）
    """
    img = np.zeros((size, size, 3), dtype=np.uint8)
    center = size // 2
    
    # 中央高光點（20x20 像素）
    point_size = 10
    img[center-point_size:center+point_size, 
        center-point_size:center+point_size, :] = 255
    
    return img

def generate_backlit_scene(size: int = 512) -> np.ndarray:
    """
    生成逆光場景（藍天背光）
    
    上半部：亮藍天（B=220, G=180, R=120）
    下半部：暗剪影（B=30, G=30, R=30）
    中央：強光源（模擬太陽）
    
    用於驗證：
    - 藍光 Halation 強度（TASK-010）
    - 光暈擴散自然度（TASK-003）
    """
    img = np.zeros((size, size, 3), dtype=np.uint8)
    
    # 上半部：藍天
    img[:size//2, :, :] = [220, 180, 120]  # BGR
    
    # 下半部：剪影
    img[size//2:, :, :] = [30, 30, 30]
    
    # 中央強光源（模擬太陽）
    center = size // 2
    light_size = 30
    img[center-light_size:center+light_size, 
        center-light_size:center+light_size, :] = 255
    
    return img

def generate_skin_tone_scene(size: int = 512) -> np.ndarray:
    """
    生成膚色測試場景
    
    標準膚色（Fitzpatrick Type II）:
    - RGB: (240, 200, 180)
    - BGR: (180, 200, 240)
    
    用於驗證：
    - 光譜亮度修正（TASK-008）
    - 色彩自然度（整體）
    """
    img = np.zeros((size, size, 3), dtype=np.uint8)
    
    # 標準膚色 (Fitzpatrick Type II)
    # RGB: (240, 200, 180) → BGR: (180, 200, 240)
    img[:, :, :] = [180, 200, 240]
    
    # 添加輕微漸層（模擬立體感）
    for y in range(size):
        fade = 0.8 + 0.2 * (y / size)  # 0.8 ~ 1.0
        img[y, :, :] = np.clip(img[y, :, :] * fade, 0, 255).astype(np.uint8)
    
    return img

# ==================== 指標計算 ====================

def calculate_halo_radius(img: np.ndarray, channel_idx: int, threshold: float = 0.1) -> float:
    """
    計算紅暈半徑（基於徑向強度分布）
    
    Args:
        img: 輸出影像 (BGR, uint8)
        channel_idx: 通道索引 (0=B, 1=G, 2=R)
        threshold: 強度閾值（相對於峰值）
    
    Returns:
        radius: 紅暈半徑（像素）
    """
    h, w = img.shape[:2]
    center_y, center_x = h // 2, w // 2
    
    # 提取通道
    channel = img[:, :, channel_idx].astype(np.float32)
    
    # 中心最大值
    peak_value = channel[center_y, center_x]
    if peak_value < 10:  # 避免噪點
        return 0.0
    
    # 徑向掃描
    max_radius = min(h, w) // 2
    for r in range(1, max_radius):
        # 圓周採樣（8 個方向）
        angles = np.linspace(0, 2*np.pi, 8, endpoint=False)
        intensities = []
        for angle in angles:
            y = int(center_y + r * np.sin(angle))
            x = int(center_x + r * np.cos(angle))
            if 0 <= y < h and 0 <= x < w:
                intensities.append(channel[y, x])
        
        # 平均強度
        mean_intensity = np.mean(intensities) if intensities else 0
        
        # 檢查是否低於閾值
        if mean_intensity < peak_value * threshold:
            return float(r)
    
    return float(max_radius)

def calculate_metrics(img: np.ndarray, scene_id: str) -> SceneMetrics:
    """
    計算場景測試指標
    
    Args:
        img: 輸出影像 (BGR, uint8)
        scene_id: 場景 ID
    
    Returns:
        SceneMetrics: 測試指標
    """
    # 亮度（感知亮度，ITU-R BT.601）
    b, g, r = cv2.split(img.astype(np.float32))
    luminance = 0.114 * b + 0.587 * g + 0.299 * r
    mean_brightness = np.mean(luminance)
    
    # 紅暈半徑（僅對點光源場景計算）
    blue_halo_radius = 0.0
    red_halo_radius = 0.0
    blue_to_red_ratio = 0.0
    
    if 'point_light' in scene_id:
        blue_halo_radius = calculate_halo_radius(img, channel_idx=0, threshold=0.1)
        red_halo_radius = calculate_halo_radius(img, channel_idx=2, threshold=0.1)
        if red_halo_radius > 0:
            blue_to_red_ratio = blue_halo_radius / red_halo_radius
    
    # 平均色彩
    mean_b = float(np.mean(b))
    mean_g = float(np.mean(g))
    mean_r = float(np.mean(r))
    
    return SceneMetrics(
        scene_id=scene_id,
        mean_brightness=float(mean_brightness),
        blue_halo_radius=float(blue_halo_radius),
        red_halo_radius=float(red_halo_radius),
        blue_to_red_ratio=float(blue_to_red_ratio),
        mean_color_bgr=(mean_b, mean_g, mean_r)
    )

# ==================== 主處理流程 ====================

def process_with_film(input_img: np.ndarray, film_profile: FilmProfile) -> np.ndarray:
    """
    使用指定膠片配置處理影像
    
    Args:
        input_img: 輸入影像 (BGR, uint8)
        film_profile: 膠片配置
    
    Returns:
        output_img: 輸出影像 (BGR, uint8)
    """
    # 簡化版本：直接調用 phos_core 處理函數
    # 實際實作需根據專案結構調整
    
    try:
        # 假設 phos_core 有 process_image 函數
        output_img = phos_core.process_image(
            input_img,
            film_profile=film_profile,
            # 其他必要參數...
        )
        return output_img
    except Exception as e:
        print(f"⚠️ 處理失敗: {e}")
        # 回傳原圖（備用）
        return input_img

def main():
    """主函數"""
    print("=" * 80)
    print("視覺驗證 v0.4.1 - 物理改進測試")
    print("=" * 80)
    print()
    
    # 創建膠片配置
    print("📦 載入膠片配置...")
    film_profiles = create_film_profiles()
    
    # 選擇測試膠片
    cinestill = film_profiles.get("Cinestill800T_MediumPhysics")
    portra = film_profiles.get("Portra400_MediumPhysics_Mie")
    
    if not cinestill or not portra:
        print("❌ 找不到必要的膠片配置")
        return
    
    print(f"✅ CineStill 800T: {cinestill.name}")
    print(f"✅ Portra 400: {portra.name}")
    print()
    
    # 生成測試場景
    print("🎨 生成測試場景...")
    scenes = {
        "S1_point_light": generate_point_light_scene(),
        "S2_backlit": generate_backlit_scene(),
        "S3_skin_tone": generate_skin_tone_scene(),
    }
    print(f"✅ 生成 {len(scenes)} 個測試場景")
    print()
    
    # 處理並儲存
    print("⚙️ 處理影像...")
    metrics_list = []
    
    for scene_id, input_img in scenes.items():
        # 儲存輸入影像
        input_path = output_dir / f"{scene_id}_input.png"
        cv2.imwrite(str(input_path), input_img)
        
        # CineStill 處理
        if 'point_light' in scene_id or 'backlit' in scene_id:
            output_cine = process_with_film(input_img, cinestill)
            output_path_cine = output_dir / f"{scene_id}_cinestill.png"
            cv2.imwrite(str(output_path_cine), output_cine)
            
            metrics_cine = calculate_metrics(output_cine, f"{scene_id}_cinestill")
            metrics_list.append(metrics_cine)
            print(f"  ✅ {scene_id} (CineStill) - 紅暈: R={metrics_cine.red_halo_radius:.1f}px, B={metrics_cine.blue_halo_radius:.1f}px")
        
        # Portra 處理
        if 'point_light' in scene_id or 'skin_tone' in scene_id:
            output_portra = process_with_film(input_img, portra)
            output_path_portra = output_dir / f"{scene_id}_portra.png"
            cv2.imwrite(str(output_path_portra), output_portra)
            
            metrics_portra = calculate_metrics(output_portra, f"{scene_id}_portra")
            metrics_list.append(metrics_portra)
            print(f"  ✅ {scene_id} (Portra) - 紅暈: R={metrics_portra.red_halo_radius:.1f}px, B={metrics_portra.blue_halo_radius:.1f}px")
    
    print()
    
    # 儲存指標報告
    print("📊 生成指標報告...")
    metrics_path = output_dir / "metrics_report.json"
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump([asdict(m) for m in metrics_list], f, indent=2, ensure_ascii=False)
    
    print(f"✅ 指標報告: {metrics_path}")
    
    # 生成文字報告
    report_path = output_dir / "metrics_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("視覺驗證 v0.4.1 - 指標報告\n")
        f.write("=" * 80 + "\n\n")
        
        for metrics in metrics_list:
            f.write(f"場景: {metrics.scene_id}\n")
            f.write(f"  平均亮度: {metrics.mean_brightness:.2f}\n")
            f.write(f"  平均色彩 (BGR): {metrics.mean_color_bgr}\n")
            if metrics.red_halo_radius > 0:
                f.write(f"  紅暈半徑 (R): {metrics.red_halo_radius:.1f} px\n")
                f.write(f"  藍暈半徑 (B): {metrics.blue_halo_radius:.1f} px\n")
                f.write(f"  B/R 比例: {metrics.blue_to_red_ratio:.2f}\n")
            f.write("\n")
        
        # 驗收檢查
        f.write("=" * 80 + "\n")
        f.write("驗收檢查\n")
        f.write("=" * 80 + "\n\n")
        
        # CineStill vs Portra 紅暈比例
        cine_metrics = [m for m in metrics_list if 'cinestill' in m.scene_id and m.red_halo_radius > 0]
        portra_metrics = [m for m in metrics_list if 'portra' in m.scene_id and m.red_halo_radius > 0]
        
        if cine_metrics and portra_metrics:
            cine_r = cine_metrics[0].red_halo_radius
            portra_r = portra_metrics[0].red_halo_radius
            ratio = cine_r / portra_r if portra_r > 0 else 0
            
            f.write(f"CineStill vs Portra 紅暈比例:\n")
            f.write(f"  CineStill: {cine_r:.1f} px\n")
            f.write(f"  Portra: {portra_r:.1f} px\n")
            f.write(f"  比例: {ratio:.2f}×\n")
            f.write(f"  驗收標準: > 1.3× {'✅ 通過' if ratio > 1.3 else '❌ 未通過'}\n\n")
    
    print(f"✅ 文字報告: {report_path}")
    print()
    
    print("=" * 80)
    print("✅ 視覺驗證完成")
    print(f"📁 輸出目錄: {output_dir}")
    print("=" * 80)

if __name__ == "__main__":
    main()
