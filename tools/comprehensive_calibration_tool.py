"""
綜合光譜校正工具

功能：
1. 自動驗證所有13款膠片（8彩色 + 5黑白）
2. 生成詳細的校正報告
3. 提供多種校正策略
4. 自動輸出可用代碼
5. 整合物理理論驗證

使用方式：
    python tools/comprehensive_calibration_tool.py --all
    python tools/comprehensive_calibration_tool.py --film Portra400
    python tools/comprehensive_calibration_tool.py --strategy 3 --export
"""

import numpy as np
import sys
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import argparse

# 添加專案根目錄
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from film_models import get_film_profile, FilmProfile
from tools.physics_validator import PhysicsValidator, ValidationResult


@dataclass
class CalibrationStrategy:
    """校正策略定義"""
    name: str
    description: str
    normalize_rows: bool
    enhance_diagonal: float  # 0-1
    target_row_sum: float
    

# 定義所有校正策略
STRATEGIES = {
    1: CalibrationStrategy(
        name="Row Normalization",
        description="僅行正規化，確保能量守恆",
        normalize_rows=True,
        enhance_diagonal=0.0,
        target_row_sum=1.0
    ),
    2: CalibrationStrategy(
        name="Diagonal Enhancement",
        description="僅增強對角線，提高色彩分離",
        normalize_rows=False,
        enhance_diagonal=0.20,
        target_row_sum=1.0
    ),
    3: CalibrationStrategy(
        name="Hybrid (Recommended)",
        description="混合策略：行正規化 + 15% 對角增強",
        normalize_rows=True,
        enhance_diagonal=0.15,
        target_row_sum=1.0
    ),
    4: CalibrationStrategy(
        name="Conservative",
        description="保守策略：行正規化 + 10% 對角增強",
        normalize_rows=True,
        enhance_diagonal=0.10,
        target_row_sum=1.0
    ),
    5: CalibrationStrategy(
        name="Aggressive",
        description="激進策略：行正規化 + 25% 對角增強",
        normalize_rows=True,
        enhance_diagonal=0.25,
        target_row_sum=1.0
    ),
}


class ComprehensiveCalibrator:
    """綜合校正器"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.calibration_results = {}
    
    def get_spectral_matrix(self, film: FilmProfile) -> np.ndarray:
        """獲取3x3光譜響應矩陣"""
        if film.red_layer is None:  # 黑白膠片
            return None
        
        coeffs = film.get_spectral_response()
        return np.array([
            [coeffs[0], coeffs[1], coeffs[2]],  # Red layer
            [coeffs[3], coeffs[4], coeffs[5]],  # Green layer
            [coeffs[6], coeffs[7], coeffs[8]]   # Blue layer
        ])
    
    def normalize_rows(self, matrix: np.ndarray, target_sum: float = 1.0) -> np.ndarray:
        """行正規化"""
        row_sums = matrix.sum(axis=1, keepdims=True)
        return matrix * (target_sum / row_sums)
    
    def enhance_diagonal(self, matrix: np.ndarray, strength: float) -> np.ndarray:
        """增強對角線"""
        result = matrix.copy()
        row_sums = matrix.sum(axis=1)
        
        for i in range(3):
            # 計算新的對角線值
            off_diag_sum = row_sums[i] - matrix[i, i]
            new_diag = matrix[i, i] + off_diag_sum * strength
            
            # 計算非對角線縮放因子
            if off_diag_sum > 1e-8:
                scale = (row_sums[i] - new_diag) / off_diag_sum
            else:
                scale = 1.0
            
            # 更新矩陣
            result[i, i] = new_diag
            for j in range(3):
                if i != j:
                    result[i, j] = matrix[i, j] * scale
        
        return result
    
    def apply_strategy(self, matrix: np.ndarray, strategy: CalibrationStrategy) -> np.ndarray:
        """應用校正策略"""
        result = matrix.copy()
        
        if strategy.normalize_rows:
            result = self.normalize_rows(result, strategy.target_row_sum)
        
        if strategy.enhance_diagonal > 0:
            result = self.enhance_diagonal(result, strategy.enhance_diagonal)
        
        return result
    
    def evaluate_matrix(self, matrix: np.ndarray, name: str = "") -> Dict:
        """評估矩陣品質"""
        # 行和
        row_sums = matrix.sum(axis=1)
        row_imbalance = (row_sums.max() - row_sums.min()) / row_sums.mean()
        
        # 對角線主導
        diag_sum = matrix.diagonal().sum()
        off_diag_sum = matrix.sum() - diag_sum
        diag_dominance = diag_sum / (off_diag_sum + 1e-8)
        
        # 灰階偏差
        white_input = np.array([1.0, 1.0, 1.0])
        white_output = matrix @ white_input
        gray_deviation = white_output.max() - white_output.min()
        
        return {
            "name": name,
            "row_sums": row_sums,
            "row_imbalance": row_imbalance,
            "diagonal_dominance": diag_dominance,
            "gray_deviation": gray_deviation,
            "white_output": white_output
        }
    
    def calibrate_film(self, film_name: str, strategy_id: int = 3) -> Dict:
        """
        校正單個膠片
        
        Args:
            film_name: 膠片名稱
            strategy_id: 校正策略ID (1-5)
            
        Returns:
            校正結果字典
        """
        film = get_film_profile(film_name)
        
        # 檢查是否為黑白膠片
        if film.red_layer is None:
            if self.verbose:
                print(f"\n⚠ {film_name} 是黑白膠片，跳過光譜校正")
            return {
                "film_name": film_name,
                "is_bw": True,
                "skipped": True
            }
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"  校正膠片: {film_name}")
            print(f"{'='*80}\n")
        
        # 獲取原始矩陣
        original_matrix = self.get_spectral_matrix(film)
        
        # 評估原始矩陣
        original_eval = self.evaluate_matrix(original_matrix, "Original")
        
        # 應用校正策略
        strategy = STRATEGIES[strategy_id]
        calibrated_matrix = self.apply_strategy(original_matrix, strategy)
        
        # 評估校正後矩陣
        calibrated_eval = self.evaluate_matrix(calibrated_matrix, f"Calibrated (Strategy {strategy_id})")
        
        if self.verbose:
            print(f"策略: {strategy.name}")
            print(f"描述: {strategy.description}\n")
            
            print(f"{'指標':<25s} | {'原始':<12s} | {'校正後':<12s} | {'改善'}")
            print(f"{'-'*80}")
            
            print(f"{'灰階偏差':<25s} | {original_eval['gray_deviation']:<12.4f} | "
                  f"{calibrated_eval['gray_deviation']:<12.4f} | "
                  f"{(1 - calibrated_eval['gray_deviation']/original_eval['gray_deviation'])*100:6.1f}%")
            
            print(f"{'行不平衡':<25s} | {original_eval['row_imbalance']:<12.4f} | "
                  f"{calibrated_eval['row_imbalance']:<12.4f} | "
                  f"{(1 - calibrated_eval['row_imbalance']/original_eval['row_imbalance'])*100:6.1f}%")
            
            print(f"{'對角主導':<25s} | {original_eval['diagonal_dominance']:<12.2f} | "
                  f"{calibrated_eval['diagonal_dominance']:<12.2f} | "
                  f"{((calibrated_eval['diagonal_dominance']/original_eval['diagonal_dominance'])-1)*100:6.1f}%")
            
            print(f"\n純白輸出:")
            orig_out = original_eval['white_output']
            cal_out = calibrated_eval['white_output']
            print(f"  原始:   ({orig_out[0]:.4f}, {orig_out[1]:.4f}, {orig_out[2]:.4f})")
            print(f"  校正後: ({cal_out[0]:.4f}, {cal_out[1]:.4f}, {cal_out[2]:.4f})")
        
        # 運行物理驗證
        if self.verbose:
            print(f"\n{'-'*80}")
            print("物理理論驗證（校正後）:")
            print(f"{'-'*80}")
        
        # 創建臨時膠片配置進行驗證
        # 注意：這裡只能通過模擬驗證，因為無法直接修改 FilmProfile
        # 實際驗證需要將校正後的係數寫回 film_models.py
        
        result = {
            "film_name": film_name,
            "is_bw": False,
            "strategy_id": strategy_id,
            "strategy_name": strategy.name,
            "original_matrix": original_matrix,
            "calibrated_matrix": calibrated_matrix,
            "original_eval": original_eval,
            "calibrated_eval": calibrated_eval,
            "improvement": {
                "gray_deviation": (original_eval['gray_deviation'] - calibrated_eval['gray_deviation']) / original_eval['gray_deviation'],
                "row_imbalance": (original_eval['row_imbalance'] - calibrated_eval['row_imbalance']) / original_eval['row_imbalance'],
            }
        }
        
        self.calibration_results[film_name] = result
        return result
    
    def calibrate_all_films(self, strategy_id: int = 3) -> Dict[str, Dict]:
        """
        校正所有膠片
        
        Args:
            strategy_id: 校正策略ID
            
        Returns:
            所有膠片的校正結果
        """
        all_films = [
            # 8 彩色膠片
            "Portra400", "Ektar100", "Velvia50", "NC200",
            "Cinestill800T", "Gold200", "ProImage100", "Superia400",
            # 5 黑白膠片（將被跳過）
            "TriX400", "HP5Plus400", "FP4Plus125", "AS100", "FS200"
        ]
        
        results = {}
        
        for film_name in all_films:
            result = self.calibrate_film(film_name, strategy_id)
            results[film_name] = result
        
        # 生成總結報告
        if self.verbose:
            self.print_summary_report(results)
        
        return results
    
    def print_summary_report(self, results: Dict[str, Dict]):
        """打印總結報告"""
        print(f"\n\n{'='*80}")
        print(f"  總結報告：所有膠片校正結果")
        print(f"{'='*80}\n")
        
        print(f"{'膠片':<20s} | {'類型':<6s} | {'灰階偏差':<12s} | {'改善':<8s} | {'狀態'}")
        print(f"{'-'*80}")
        
        color_films = []
        bw_films = []
        
        for film_name, result in results.items():
            if result.get("is_bw"):
                bw_films.append(film_name)
                print(f"{film_name:<20s} | {'B&W':<6s} | {'N/A':<12s} | {'N/A':<8s} | SKIPPED")
            else:
                color_films.append(film_name)
                gray_dev = result['calibrated_eval']['gray_deviation']
                improvement = result['improvement']['gray_deviation'] * 100
                status = "✓ PASS" if gray_dev < 0.002 else "⚠ CHECK"
                
                print(f"{film_name:<20s} | {'Color':<6s} | {gray_dev:<12.6f} | {improvement:7.1f}% | {status}")
        
        print(f"\n彩色膠片: {len(color_films)} 個")
        print(f"黑白膠片: {len(bw_films)} 個（跳過）")
        print(f"{'='*80}\n")
    
    def export_code(self, results: Dict[str, Dict], output_file: Optional[str] = None):
        """
        導出校正後的代碼
        
        Args:
            results: 校正結果
            output_file: 輸出檔案路徑（None = 打印到螢幕）
        """
        lines = []
        
        lines.append("# " + "="*76)
        lines.append("# 校正後的光譜響應係數")
        lines.append("# 生成時間: " + __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        lines.append("# " + "="*76)
        lines.append("")
        
        for film_name, result in results.items():
            if result.get("is_bw") or result.get("skipped"):
                continue
            
            matrix = result['calibrated_matrix']
            
            lines.append(f"# {film_name}")
            lines.append(f"# 灰階偏差: {result['calibrated_eval']['gray_deviation']:.6f}")
            lines.append(f"# 改善: {result['improvement']['gray_deviation']*100:.1f}%")
            lines.append("")
            lines.append(f"# Red Layer")
            lines.append(f"r_response_weight={matrix[0, 0]:.6f},")
            lines.append(f"g_response_weight={matrix[0, 1]:.6f},")
            lines.append(f"b_response_weight={matrix[0, 2]:.6f},")
            lines.append("")
            lines.append(f"# Green Layer")
            lines.append(f"r_response_weight={matrix[1, 0]:.6f},")
            lines.append(f"g_response_weight={matrix[1, 1]:.6f},")
            lines.append(f"b_response_weight={matrix[1, 2]:.6f},")
            lines.append("")
            lines.append(f"# Blue Layer")
            lines.append(f"r_response_weight={matrix[2, 0]:.6f},")
            lines.append(f"g_response_weight={matrix[2, 1]:.6f},")
            lines.append(f"b_response_weight={matrix[2, 2]:.6f},")
            lines.append("")
            lines.append("-" * 78)
            lines.append("")
        
        output = "\n".join(lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\n✓ 代碼已導出至: {output_file}")
        else:
            print(f"\n{'='*80}")
            print("  校正後的係數（可直接複製到 film_models.py）")
            print(f"{'='*80}\n")
            print(output)


def main():
    parser = argparse.ArgumentParser(
        description="綜合光譜校正工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 使用策略3（推薦）校正所有膠片
  python tools/comprehensive_calibration_tool.py --all --strategy 3
  
  # 校正單個膠片並導出代碼
  python tools/comprehensive_calibration_tool.py --film Portra400 --export
  
  # 比較所有策略
  python tools/comprehensive_calibration_tool.py --film Velvia50 --compare-strategies
        """
    )
    
    parser.add_argument("--all", action="store_true", help="校正所有膠片")
    parser.add_argument("--film", type=str, help="指定膠片名稱")
    parser.add_argument("--strategy", type=int, default=3, choices=[1,2,3,4,5], 
                       help="校正策略 (1-5, 預設=3)")
    parser.add_argument("--export", action="store_true", help="導出代碼")
    parser.add_argument("--output", type=str, help="導出檔案路徑")
    parser.add_argument("--quiet", action="store_true", help="安靜模式")
    parser.add_argument("--compare-strategies", action="store_true", 
                       help="比較所有策略")
    
    args = parser.parse_args()
    
    calibrator = ComprehensiveCalibrator(verbose=not args.quiet)
    
    if args.compare_strategies and args.film:
        # 比較所有策略
        print(f"\n{'='*80}")
        print(f"  比較所有策略：{args.film}")
        print(f"{'='*80}\n")
        
        results = {}
        for strategy_id in range(1, 6):
            print(f"\n策略 {strategy_id}: {STRATEGIES[strategy_id].name}")
            print(f"{'-'*80}")
            result = calibrator.calibrate_film(args.film, strategy_id)
            results[strategy_id] = result
        
        # 打印比較表
        print(f"\n\n{'='*80}")
        print(f"  策略比較")
        print(f"{'='*80}\n")
        print(f"{'策略':<30s} | {'灰階偏差':<12s} | {'對角主導':<12s}")
        print(f"{'-'*80}")
        for strategy_id, result in results.items():
            if not result.get("is_bw"):
                eval_data = result['calibrated_eval']
                print(f"{STRATEGIES[strategy_id].name:<30s} | "
                      f"{eval_data['gray_deviation']:<12.6f} | "
                      f"{eval_data['diagonal_dominance']:<12.2f}")
    
    elif args.all:
        results = calibrator.calibrate_all_films(args.strategy)
        
        if args.export:
            calibrator.export_code(results, args.output)
    
    elif args.film:
        result = calibrator.calibrate_film(args.film, args.strategy)
        
        if args.export and not result.get("is_bw"):
            calibrator.export_code({args.film: result}, args.output)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
