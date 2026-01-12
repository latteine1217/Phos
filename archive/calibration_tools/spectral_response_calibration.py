"""
光譜響應係數校正工具

目的：
1. 分析當前係數矩陣的問題
2. 提供多種校正策略
3. 生成校正後的係數矩陣
4. 驗證校正效果

校正目標：
- 減少色偏（< 0.15）
- 灰階中性（純白不偏色）
- 能量守恆（行和歸一化）
- 保持光譜分離度（對角線主導）
"""

import numpy as np
from typing import Dict, Tuple, List
from dataclasses import dataclass


@dataclass
class SpectralResponseMatrix:
    """光譜響應係數矩陣"""
    r_r: float  # Red layer response to R input
    r_g: float
    r_b: float
    g_r: float  # Green layer response to R input
    g_g: float
    g_b: float
    b_r: float  # Blue layer response to R input
    b_g: float
    b_b: float
    t_r: float  # Total (panchromatic) response to R input
    t_g: float
    t_b: float
    
    def to_tuple(self) -> Tuple[float, ...]:
        """轉換為 12 元素 tuple"""
        return (
            self.r_r, self.r_g, self.r_b,
            self.g_r, self.g_g, self.g_b,
            self.b_r, self.b_g, self.b_b,
            self.t_r, self.t_g, self.t_b
        )
    
    def get_rgb_matrix(self) -> np.ndarray:
        """獲取 RGB 層的 3×3 矩陣"""
        return np.array([
            [self.r_r, self.r_g, self.r_b],
            [self.g_r, self.g_g, self.g_b],
            [self.b_r, self.b_g, self.b_b]
        ])
    
    def row_sums(self) -> Dict[str, float]:
        """計算行和（每層的總響應）"""
        return {
            "Red": self.r_r + self.r_g + self.r_b,
            "Green": self.g_r + self.g_g + self.g_b,
            "Blue": self.b_r + self.b_g + self.b_b,
            "Total": self.t_r + self.t_g + self.t_b
        }
    
    def col_sums(self) -> Dict[str, float]:
        """計算列和（每個輸入通道的總影響）"""
        return {
            "Input_R": self.r_r + self.g_r + self.b_r,
            "Input_G": self.r_g + self.g_g + self.b_g,
            "Input_B": self.r_b + self.g_b + self.b_b
        }
    
    def diagonal_dominance(self) -> float:
        """計算對角線主導比"""
        diag_sum = self.r_r + self.g_g + self.b_b
        off_diag_sum = (self.r_g + self.r_b + self.g_r + 
                        self.g_b + self.b_r + self.b_g)
        return diag_sum / (off_diag_sum + 1e-8)


# ==================== 當前係數矩陣（待校正）====================

CURRENT_MATRICES = {
    "Portra400": SpectralResponseMatrix(
        r_r=0.82, r_g=0.10, r_b=0.15,
        g_r=0.06, g_g=0.88, g_b=0.20,
        b_r=0.05, b_g=0.08, b_b=0.90,
        t_r=0.28, t_g=0.40, t_b=0.30
    ),
    "Ektar100": SpectralResponseMatrix(
        r_r=0.85, r_g=0.08, r_b=0.12,
        g_r=0.05, g_g=0.90, g_b=0.18,
        b_r=0.04, b_g=0.06, b_b=0.95,
        t_r=0.30, t_g=0.38, t_b=0.32
    ),
    "Velvia50": SpectralResponseMatrix(
        r_r=0.88, r_g=0.05, r_b=0.10,
        g_r=0.03, g_g=0.92, g_b=0.15,
        b_r=0.02, b_g=0.04, b_b=0.98,
        t_r=0.25, t_g=0.40, t_b=0.35
    ),
}


# ==================== 校正策略 ====================

def calibration_strategy_1_normalize_rows(matrix: SpectralResponseMatrix, 
                                          target_sum: float = 1.0) -> SpectralResponseMatrix:
    """
    策略 1: 行歸一化（能量守恆）
    
    確保每層的總響應相等（行和 = target_sum）
    保持交叉響應的比例不變
    
    優點: 消除灰階色偏
    缺點: 可能降低對角線主導性
    """
    row_sums = matrix.row_sums()
    
    # 歸一化各層
    r_scale = target_sum / row_sums["Red"]
    g_scale = target_sum / row_sums["Green"]
    b_scale = target_sum / row_sums["Blue"]
    t_scale = target_sum / row_sums["Total"]
    
    return SpectralResponseMatrix(
        r_r=matrix.r_r * r_scale, r_g=matrix.r_g * r_scale, r_b=matrix.r_b * r_scale,
        g_r=matrix.g_r * g_scale, g_g=matrix.g_g * g_scale, g_b=matrix.g_b * g_scale,
        b_r=matrix.b_r * b_scale, b_g=matrix.b_g * b_scale, b_b=matrix.b_b * b_scale,
        t_r=matrix.t_r * t_scale, t_g=matrix.t_g * t_scale, t_b=matrix.t_b * t_scale
    )


def calibration_strategy_2_enhance_diagonal(matrix: SpectralResponseMatrix, 
                                            strength: float = 0.2) -> SpectralResponseMatrix:
    """
    策略 2: 增強對角線主導
    
    增加對角線元素，減少非對角元素（交叉響應）
    保持行和不變
    
    Args:
        strength: 增強強度 (0-1)，0 = 不變，1 = 完全對角矩陣
    
    優點: 減少色偏，提高色彩準確度
    缺點: 失去膠片的光譜交叉特性
    """
    # 計算當前行和
    row_sums = matrix.row_sums()
    
    # 對角線增強
    r_r_new = matrix.r_r + (row_sums["Red"] - matrix.r_r) * strength
    g_g_new = matrix.g_g + (row_sums["Green"] - matrix.g_g) * strength
    b_b_new = matrix.b_b + (row_sums["Blue"] - matrix.b_b) * strength
    
    # 非對角線按比例縮減
    r_off_scale = (row_sums["Red"] - r_r_new) / (matrix.r_g + matrix.r_b + 1e-8)
    g_off_scale = (row_sums["Green"] - g_g_new) / (matrix.g_r + matrix.g_b + 1e-8)
    b_off_scale = (row_sums["Blue"] - b_b_new) / (matrix.b_r + matrix.b_g + 1e-8)
    
    return SpectralResponseMatrix(
        r_r=r_r_new, 
        r_g=matrix.r_g * r_off_scale, 
        r_b=matrix.r_b * r_off_scale,
        g_r=matrix.g_r * g_off_scale, 
        g_g=g_g_new, 
        g_b=matrix.g_b * g_off_scale,
        b_r=matrix.b_r * b_off_scale, 
        b_g=matrix.b_g * b_off_scale, 
        b_b=b_b_new,
        t_r=matrix.t_r, 
        t_g=matrix.t_g, 
        t_b=matrix.t_b
    )


def calibration_strategy_3_hybrid(matrix: SpectralResponseMatrix, 
                                  normalize: bool = True,
                                  enhance_diagonal: float = 0.15,
                                  target_sum: float = 1.0) -> SpectralResponseMatrix:
    """
    策略 3: 混合策略（推薦）
    
    結合行歸一化 + 適度增強對角線
    平衡色彩準確度與膠片特性
    
    Args:
        normalize: 是否行歸一化
        enhance_diagonal: 對角線增強強度 (0-1)
        target_sum: 目標行和
    
    優點: 平衡色偏校正與膠片風格
    缺點: 需要調整參數
    """
    result = matrix
    
    # 步驟 1: 行歸一化
    if normalize:
        result = calibration_strategy_1_normalize_rows(result, target_sum)
    
    # 步驟 2: 增強對角線
    if enhance_diagonal > 0:
        result = calibration_strategy_2_enhance_diagonal(result, enhance_diagonal)
    
    return result


def calibration_strategy_4_reference_based(film_type: str = "portra") -> SpectralResponseMatrix:
    """
    策略 4: 基於參考值（文獻/測量數據）
    
    使用實際膠片的光譜敏感度曲線
    
    參考來源:
    - Kodak Portra: 根據 Kodak 技術文檔（近似）
    - Fuji Velvia: 根據 Fuji 公開數據（近似）
    - Kodak Ektar: 高飽和度專業負片
    
    注意: 這些是基於公開資料的近似值，非實測數據
    """
    if film_type.lower() == "portra":
        # Portra 400: 中性色彩，輕微暖調
        # 特點: 細膩膚色，低對比，適度飽和
        return SpectralResponseMatrix(
            r_r=0.88, r_g=0.06, r_b=0.06,  # 紅層：主要響應紅光，極低交叉
            g_r=0.04, g_g=0.88, g_b=0.08,  # 綠層：主要響應綠光
            b_r=0.03, b_g=0.05, b_b=0.92,  # 藍層：主要響應藍光
            t_r=0.30, t_g=0.40, t_b=0.30   # 全色層：略偏綠（人眼敏感）
        )
    
    elif film_type.lower() == "ektar":
        # Ektar 100: 極高飽和度，鮮豔色彩
        # 特點: 風光攝影，高對比，高銳度
        return SpectralResponseMatrix(
            r_r=0.90, r_g=0.05, r_b=0.05,  # 更強的紅色分離
            g_r=0.03, g_g=0.92, g_b=0.05,  # 更強的綠色分離
            b_r=0.02, b_g=0.03, b_b=0.95,  # 更強的藍色分離
            t_r=0.30, t_g=0.40, t_b=0.30
        )
    
    elif film_type.lower() == "velvia":
        # Velvia 50: 極端飽和度，風光專用
        # 特點: 鮮豔紅、綠、藍，高對比
        return SpectralResponseMatrix(
            r_r=0.92, r_g=0.04, r_b=0.04,  # 極高紅色純度
            g_r=0.02, g_g=0.94, g_b=0.04,  # 極高綠色純度
            b_r=0.01, b_g=0.02, b_b=0.97,  # 極高藍色純度
            t_r=0.28, t_g=0.42, t_b=0.30   # 偏綠（強調植物）
        )
    
    else:
        raise ValueError(f"未知膠片類型: {film_type}")


# ==================== 評估與比較 ====================

def evaluate_matrix(matrix: SpectralResponseMatrix, name: str = "") -> Dict:
    """
    評估係數矩陣的品質
    
    Returns:
        評估指標字典
    """
    row_sums = matrix.row_sums()
    col_sums = matrix.col_sums()
    diag_dom = matrix.diagonal_dominance()
    
    # 計算色偏（模擬純白輸入）
    white_input = np.array([1.0, 1.0, 1.0])
    rgb_matrix = matrix.get_rgb_matrix()
    white_output = rgb_matrix @ white_input
    
    # 計算灰階偏差
    gray_deviation = white_output.max() - white_output.min()
    
    # 行和不平衡度
    row_sum_values = list(row_sums.values())[:3]  # RGB 層
    row_imbalance = (max(row_sum_values) - min(row_sum_values)) / np.mean(row_sum_values)
    
    return {
        "name": name,
        "row_sums": row_sums,
        "col_sums": col_sums,
        "diagonal_dominance": diag_dom,
        "gray_deviation": gray_deviation,
        "row_imbalance": row_imbalance,
        "white_output": white_output,
    }


def compare_matrices(matrices: Dict[str, SpectralResponseMatrix]):
    """
    比較多個係數矩陣
    
    Args:
        matrices: {名稱: 矩陣} 字典
    """
    print("=" * 100)
    print(" " * 35 + "光譜響應係數矩陣比較")
    print("=" * 100)
    print()
    
    evaluations = {}
    for name, matrix in matrices.items():
        evaluations[name] = evaluate_matrix(matrix, name)
    
    # 顯示比較表格
    print(f"{'矩陣名稱':<25s} | 對角主導 | 灰階偏差 | 行不平衡 | 純白輸出 (R, G, B)")
    print("-" * 100)
    
    for name, eval_data in evaluations.items():
        white_out = eval_data["white_output"]
        print(f"{name:<25s} | {eval_data['diagonal_dominance']:8.2f} | "
              f"{eval_data['gray_deviation']:8.3f} | "
              f"{eval_data['row_imbalance']:8.1%} | "
              f"({white_out[0]:.3f}, {white_out[1]:.3f}, {white_out[2]:.3f})")
    
    print("\n評估標準:")
    print("  - 對角主導: > 5.0 (良好), > 10.0 (優秀)")
    print("  - 灰階偏差: < 0.05 (優秀), < 0.10 (良好)")
    print("  - 行不平衡: < 5% (優秀), < 10% (良好)")
    print("  - 純白輸出: 理想為 (1.0, 1.0, 1.0) ± 0.05")
    print("=" * 100)


# ==================== 生成校正後的係數 ====================

def generate_calibrated_matrices():
    """
    生成所有膠片的校正係數
    
    Returns:
        {膠片名: 校正後矩陣} 字典
    """
    calibrated = {}
    
    for film_name, original in CURRENT_MATRICES.items():
        print(f"\n{'=' * 80}")
        print(f"校正: {film_name}")
        print(f"{'=' * 80}")
        
        # 策略 1: 行歸一化
        strategy1 = calibration_strategy_1_normalize_rows(original)
        
        # 策略 2: 增強對角線
        strategy2 = calibration_strategy_2_enhance_diagonal(original, strength=0.2)
        
        # 策略 3: 混合（推薦）
        strategy3 = calibration_strategy_3_hybrid(
            original, 
            normalize=True, 
            enhance_diagonal=0.15,
            target_sum=1.0
        )
        
        # 策略 4: 參考值
        film_type_map = {
            "Portra400": "portra",
            "Ektar100": "ektar",
            "Velvia50": "velvia"
        }
        strategy4 = calibration_strategy_4_reference_based(film_type_map.get(film_name, "portra"))
        
        # 比較所有策略
        compare_matrices({
            "原始": original,
            "策略1-行歸一化": strategy1,
            "策略2-增強對角": strategy2,
            "策略3-混合(推薦)": strategy3,
            "策略4-參考值": strategy4,
        })
        
        # 選擇推薦策略
        calibrated[film_name] = {
            "original": original,
            "strategy1": strategy1,
            "strategy2": strategy2,
            "strategy3_recommended": strategy3,
            "strategy4_reference": strategy4,
        }
    
    return calibrated


def export_to_code(matrices: Dict[str, SpectralResponseMatrix], strategy: str = "strategy3_recommended"):
    """
    導出為可直接用於 film_models.py 的代碼
    
    Args:
        matrices: {膠片名: {策略名: 矩陣}} 字典
        strategy: 要導出的策略
    """
    print("\n" + "=" * 80)
    print(" " * 25 + "導出校正後的係數矩陣")
    print("=" * 80)
    print()
    print("複製以下代碼到 film_models.py 中替換原有係數:")
    print()
    
    for film_name, strategies in matrices.items():
        matrix = strategies[strategy]
        print(f"# {film_name} - {strategy}")
        print(f"red_layer = EmulsionLayer(")
        print(f"    r_response_weight={matrix.r_r:.3f}, g_response_weight={matrix.r_g:.3f}, b_response_weight={matrix.r_b:.3f},")
        print(f"    ...")
        print(f")")
        print(f"green_layer = EmulsionLayer(")
        print(f"    r_response_weight={matrix.g_r:.3f}, g_response_weight={matrix.g_g:.3f}, b_response_weight={matrix.g_b:.3f},")
        print(f"    ...")
        print(f")")
        print(f"blue_layer = EmulsionLayer(")
        print(f"    r_response_weight={matrix.b_r:.3f}, g_response_weight={matrix.b_g:.3f}, b_response_weight={matrix.b_b:.3f},")
        print(f"    ...")
        print(f")")
        print(f"panchromatic_layer = EmulsionLayer(")
        print(f"    r_response_weight={matrix.t_r:.3f}, g_response_weight={matrix.t_g:.3f}, b_response_weight={matrix.t_b:.3f},")
        print(f"    ...")
        print(f")")
        print()
    
    print("=" * 80)


# ==================== 主程式 ====================

if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "Phos 光譜響應係數校正工具" + " " * 32 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # 生成校正後的矩陣
    calibrated_matrices = generate_calibrated_matrices()
    
    # 導出代碼
    print("\n\n")
    export_to_code(calibrated_matrices, strategy="strategy3_recommended")
    
    print("\n")
    print("✓ 校正完成！")
    print("\n建議:")
    print("  1. 使用「策略3-混合」作為主要校正方案（平衡準確度與風格）")
    print("  2. 使用「策略4-參考值」作為備選方案（極致色彩分離）")
    print("  3. 保留原始係數作為「經典模式」供用戶選擇")
    print()
