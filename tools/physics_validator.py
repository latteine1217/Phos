"""
物理理論驗證套件

驗證光譜響應係數矩陣是否符合物理理論：
1. 能量守恆（Energy Conservation）
2. 單調性（Monotonicity）
3. 線性疊加（Linearity）
4. 非負性（Non-negativity）
5. 灰階中性（Grayscale Neutrality）

使用來源：
- Energy Conservation: Judd, Wright & Pitt (1964) "Color Vision and Colorimetry"
- Monotonicity: Hunt (2004) "The Reproduction of Colour"
- Linearity: Grassmann's Laws (1853)
"""

import numpy as np
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
import sys
import os

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from film_models import get_film_profile, FilmProfile


@dataclass
class ValidationResult:
    """驗證結果"""
    test_name: str
    passed: bool
    value: float
    threshold: float
    message: str
    severity: str = "error"  # "error", "warning", "info"
    
    def __repr__(self):
        status = "✓" if self.passed else "✗"
        return f"{status} {self.test_name}: {self.message}"


class PhysicsValidator:
    """物理理論驗證器"""
    
    def __init__(self, film: FilmProfile, verbose: bool = True):
        """
        初始化驗證器
        
        Args:
            film: 膠片配置
            verbose: 是否顯示詳細訊息
        """
        self.film = film
        self.verbose = verbose
        
        # 獲取光譜響應係數
        coeffs = film.get_spectral_response()
        self.r_r, self.r_g, self.r_b = coeffs[0], coeffs[1], coeffs[2]
        self.g_r, self.g_g, self.g_b = coeffs[3], coeffs[4], coeffs[5]
        self.b_r, self.b_g, self.b_b = coeffs[6], coeffs[7], coeffs[8]
        self.t_r, self.t_g, self.t_b = coeffs[9], coeffs[10], coeffs[11]
        
        # 構建矩陣
        self.rgb_matrix = np.array([
            [self.r_r, self.r_g, self.r_b],
            [self.g_r, self.g_g, self.g_b],
            [self.b_r, self.b_g, self.b_b]
        ])
        
        self.results: List[ValidationResult] = []
    
    def validate_energy_conservation(self, tolerance: float = 0.02) -> ValidationResult:
        """
        驗證能量守恆
        
        原理：對於灰階輸入（R=G=B），輸出也應該是灰階（R'=G'=B'）
        數學表達：若 I_in = (L, L, L)，則 I_out = (L', L', L')，即 R'=G'=B'
        
        物理依據：真實膠片對灰階輸入不應產生色偏
        
        Args:
            tolerance: 允許的最大偏差（0-1 範圍）
            
        Returns:
            ValidationResult
        """
        # 測試純白輸入
        white_input = np.array([1.0, 1.0, 1.0])
        white_output = self.rgb_matrix @ white_input
        
        # 計算偏差
        max_val = white_output.max()
        min_val = white_output.min()
        deviation = max_val - min_val
        
        passed = deviation < tolerance
        severity = "error" if not passed else "info"
        
        result = ValidationResult(
            test_name="Energy Conservation (Grayscale Neutrality)",
            passed=passed,
            value=deviation,
            threshold=tolerance,
            message=f"White (1,1,1) → ({white_output[0]:.4f}, {white_output[1]:.4f}, {white_output[2]:.4f}), deviation={deviation:.4f}",
            severity=severity
        )
        
        self.results.append(result)
        return result
    
    def validate_row_normalization(self, tolerance: float = 0.02) -> List[ValidationResult]:
        """
        驗證行正規化（能量守恆的另一種表達）
        
        原理：每層的總響應應該相等（行和 = 1.0）
        數學表達：Σ(M[i,j]) = 1.0 for each row i
        
        物理依據：每層感光材料應該接收相同的總能量
        
        Args:
            tolerance: 允許的行和偏差
            
        Returns:
            List[ValidationResult]
        """
        results = []
        row_sums = self.rgb_matrix.sum(axis=1)
        
        for i, (row_sum, layer_name) in enumerate(zip(row_sums, ["Red", "Green", "Blue"])):
            deviation = abs(row_sum - 1.0)
            passed = deviation < tolerance
            severity = "error" if not passed else "info"
            
            result = ValidationResult(
                test_name=f"Row Normalization ({layer_name} Layer)",
                passed=passed,
                value=row_sum,
                threshold=1.0,
                message=f"Row sum = {row_sum:.4f}, deviation from 1.0 = {deviation:.4f}",
                severity=severity
            )
            
            results.append(result)
            self.results.append(result)
        
        return results
    
    def validate_non_negativity(self) -> List[ValidationResult]:
        """
        驗證非負性
        
        原理：光譜響應係數必須 >= 0（不能有負值光響應）
        數學表達：M[i,j] >= 0 for all i, j
        
        物理依據：光子只能被吸收（增加響應），不能產生負響應
        
        Returns:
            List[ValidationResult]
        """
        results = []
        
        all_coeffs = [
            ("Red-R", self.r_r), ("Red-G", self.r_g), ("Red-B", self.r_b),
            ("Green-R", self.g_r), ("Green-G", self.g_g), ("Green-B", self.g_b),
            ("Blue-R", self.b_r), ("Blue-G", self.b_g), ("Blue-B", self.b_b),
        ]
        
        for name, coeff in all_coeffs:
            passed = coeff >= 0.0
            severity = "error" if not passed else "info"
            
            result = ValidationResult(
                test_name=f"Non-negativity ({name})",
                passed=passed,
                value=coeff,
                threshold=0.0,
                message=f"Coefficient = {coeff:.4f}",
                severity=severity
            )
            
            results.append(result)
            self.results.append(result)
        
        return results
    
    def validate_diagonal_dominance(self, min_ratio: float = 5.0) -> ValidationResult:
        """
        驗證對角線主導性
        
        原理：對角線元素應該遠大於非對角線元素（色彩分離）
        數學表達：Σ(M[i,i]) / Σ(M[i,j], i≠j) > min_ratio
        
        物理依據：每層主要響應對應波長的光（紅層主要響應紅光）
        
        Args:
            min_ratio: 最小對角/非對角比值
            
        Returns:
            ValidationResult
        """
        diag_sum = self.rgb_matrix.diagonal().sum()
        off_diag_sum = self.rgb_matrix.sum() - diag_sum
        
        ratio = diag_sum / (off_diag_sum + 1e-8)
        
        passed = ratio >= min_ratio
        severity = "warning" if not passed else "info"
        
        result = ValidationResult(
            test_name="Diagonal Dominance",
            passed=passed,
            value=ratio,
            threshold=min_ratio,
            message=f"Diagonal/Off-diagonal ratio = {ratio:.2f} (target >= {min_ratio:.1f})",
            severity=severity
        )
        
        self.results.append(result)
        return result
    
    def validate_monotonicity(self) -> List[ValidationResult]:
        """
        驗證單調性
        
        原理：增加輸入亮度，輸出亮度也應該增加（無逆轉）
        數學表達：若 I1 < I2，則 O1 < O2（分量比較）
        
        物理依據：更多光子 → 更多響應（Beer-Lambert Law）
        
        Returns:
            List[ValidationResult]
        """
        results = []
        
        # 測試灰階序列
        gray_levels = np.linspace(0, 1, 11)  # 0.0, 0.1, ..., 1.0
        
        for channel_idx, channel_name in enumerate(["Red", "Green", "Blue"]):
            outputs = []
            
            for level in gray_levels:
                input_vec = np.array([level, level, level])
                output = self.rgb_matrix @ input_vec
                outputs.append(output[channel_idx])
            
            # 檢查是否單調遞增
            is_monotonic = all(outputs[i] <= outputs[i+1] for i in range(len(outputs)-1))
            
            # 計算逆轉次數
            reversals = sum(1 for i in range(len(outputs)-1) if outputs[i] > outputs[i+1])
            
            passed = is_monotonic
            severity = "error" if not passed else "info"
            
            result = ValidationResult(
                test_name=f"Monotonicity ({channel_name} Output)",
                passed=passed,
                value=float(reversals),
                threshold=0.0,
                message=f"{'Monotonic' if is_monotonic else f'{reversals} reversals detected'}",
                severity=severity
            )
            
            results.append(result)
            self.results.append(result)
        
        return results
    
    def validate_linearity(self, tolerance: float = 0.05) -> ValidationResult:
        """
        驗證線性疊加（Grassmann's Laws）
        
        原理：M(aI1 + bI2) = aM(I1) + bM(I2)
        數學表達：矩陣運算滿足線性
        
        物理依據：光的疊加原理（低曝光量下）
        
        Args:
            tolerance: 允許的非線性誤差
            
        Returns:
            ValidationResult
        """
        # 測試兩個輸入
        I1 = np.array([0.3, 0.5, 0.7])
        I2 = np.array([0.2, 0.4, 0.6])
        a, b = 0.6, 0.4
        
        # 方法1：先疊加再轉換
        combined_input = a * I1 + b * I2
        output_combined = self.rgb_matrix @ combined_input
        
        # 方法2：先轉換再疊加
        output_I1 = self.rgb_matrix @ I1
        output_I2 = self.rgb_matrix @ I2
        output_linear = a * output_I1 + b * output_I2
        
        # 計算誤差
        error = np.abs(output_combined - output_linear).max()
        
        passed = error < tolerance
        severity = "warning" if not passed else "info"
        
        result = ValidationResult(
            test_name="Linearity (Grassmann's Laws)",
            passed=passed,
            value=error,
            threshold=tolerance,
            message=f"Max linearity error = {error:.6f}",
            severity=severity
        )
        
        self.results.append(result)
        return result
    
    def validate_cross_response_range(self, max_cross: float = 0.25) -> List[ValidationResult]:
        """
        驗證交叉響應範圍
        
        原理：非對角線元素（交叉響應）應該受限
        過高：色彩混淆
        過低：失去膠片風格
        
        物理依據：真實膠片有 5-20% 的交叉響應
        
        Args:
            max_cross: 最大允許交叉響應
            
        Returns:
            List[ValidationResult]
        """
        results = []
        
        off_diag_elements = [
            ("Red layer → G input", self.r_g),
            ("Red layer → B input", self.r_b),
            ("Green layer → R input", self.g_r),
            ("Green layer → B input", self.g_b),
            ("Blue layer → R input", self.b_r),
            ("Blue layer → G input", self.b_g),
        ]
        
        for name, value in off_diag_elements:
            passed = value <= max_cross
            severity = "warning" if not passed else "info"
            
            result = ValidationResult(
                test_name=f"Cross-response Range ({name})",
                passed=passed,
                value=value,
                threshold=max_cross,
                message=f"Cross-response = {value:.4f} (max {max_cross:.2f})",
                severity=severity
            )
            
            results.append(result)
            self.results.append(result)
        
        return results
    
    def run_all_validations(self) -> Dict[str, any]:
        """
        運行所有驗證測試
        
        Returns:
            驗證摘要字典
        """
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"  物理理論驗證：{self.film.name}")
            print(f"{'='*80}\n")
        
        # 清空之前的結果
        self.results = []
        
        # 執行所有驗證
        self.validate_energy_conservation()
        self.validate_row_normalization()
        self.validate_non_negativity()
        self.validate_diagonal_dominance()
        self.validate_monotonicity()
        self.validate_linearity()
        self.validate_cross_response_range()
        
        # 統計結果
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        errors = [r for r in self.results if not r.passed and r.severity == "error"]
        warnings = [r for r in self.results if not r.passed and r.severity == "warning"]
        
        # 顯示結果
        if self.verbose:
            for result in self.results:
                print(result)
            
            print(f"\n{'-'*80}")
            print(f"測試總數: {total_tests}")
            print(f"通過測試: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
            print(f"錯誤: {len(errors)}")
            print(f"警告: {len(warnings)}")
            
            if len(errors) == 0 and len(warnings) == 0:
                print(f"\n✓ 所有測試通過！物理理論完全正確。")
            elif len(errors) == 0:
                print(f"\n⚠ 存在 {len(warnings)} 個警告，但無嚴重錯誤。")
            else:
                print(f"\n✗ 存在 {len(errors)} 個嚴重錯誤，需要修正。")
            
            print(f"{'='*80}\n")
        
        return {
            "film_name": self.film.name,
            "total_tests": total_tests,
            "passed": passed_tests,
            "errors": len(errors),
            "warnings": len(warnings),
            "all_passed": len(errors) == 0,
            "results": self.results
        }


def validate_film(film_name: str, verbose: bool = True) -> Dict:
    """
    驗證單個膠片
    
    Args:
        film_name: 膠片名稱
        verbose: 是否顯示詳細訊息
        
    Returns:
        驗證摘要
    """
    film = get_film_profile(film_name)
    validator = PhysicsValidator(film, verbose=verbose)
    return validator.run_all_validations()


def validate_all_films(verbose: bool = True) -> Dict[str, Dict]:
    """
    驗證所有彩色膠片
    
    Args:
        verbose: 是否顯示詳細訊息
        
    Returns:
        所有膠片的驗證摘要
    """
    color_films = [
        "Portra400", "Ektar100", "Velvia50", "NC200",
        "Cinestill800T", "Gold200", "ProImage100", "Superia400"
    ]
    
    results = {}
    
    for film_name in color_films:
        results[film_name] = validate_film(film_name, verbose=verbose)
    
    # 總結報告
    if verbose:
        print(f"\n{'='*80}")
        print(f"  總結報告：所有膠片物理驗證")
        print(f"{'='*80}\n")
        
        print(f"{'膠片':<20s} | 測試數 | 通過 | 錯誤 | 警告 | 狀態")
        print(f"{'-'*80}")
        
        for film_name, summary in results.items():
            status = "✓ PASS" if summary["all_passed"] else "✗ FAIL"
            print(f"{film_name:<20s} | {summary['total_tests']:6d} | "
                  f"{summary['passed']:4d} | {summary['errors']:4d} | "
                  f"{summary['warnings']:4d} | {status}")
        
        total_films = len(results)
        passed_films = sum(1 for s in results.values() if s["all_passed"])
        
        print(f"\n總計：{passed_films}/{total_films} 膠片通過所有測試 "
              f"({passed_films/total_films*100:.1f}%)")
        print(f"{'='*80}\n")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="物理理論驗證工具")
    parser.add_argument("--film", type=str, help="指定膠片名稱（不指定則驗證所有）")
    parser.add_argument("--quiet", action="store_true", help="安靜模式（僅顯示摘要）")
    
    args = parser.parse_args()
    
    if args.film:
        validate_film(args.film, verbose=not args.quiet)
    else:
        validate_all_films(verbose=not args.quiet)
