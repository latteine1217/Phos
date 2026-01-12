#!/usr/bin/env python3
"""驗證 UI 重構的完整性"""

import sys
import ast
from pathlib import Path

def check_function_exists(file_path, func_name):
    """檢查函數是否存在"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=file_path)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                return True
        return False
    except Exception as e:
        print(f"❌ 錯誤檢查 {file_path}: {e}")
        return False

def main():
    print("=" * 60)
    print("Phos UI 重構驗證檢查")
    print("=" * 60)
    
    # 檢查文件存在
    print("\n📁 文件存在性檢查:")
    files_to_check = [
        ('Phos.py', '主應用文件'),
        ('ui_components.py', 'UI 組件模組'),
        ('film_models.py', '底片模型'),
        ('phos_core.py', '核心處理'),
    ]
    
    all_files_exist = True
    for file_name, description in files_to_check:
        exists = Path(file_name).exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {file_name} ({description})")
        if not exists:
            all_files_exist = False
    
    if not all_files_exist:
        print("\n❌ 部分文件缺失！")
        return 1
    
    # 檢查 UI 組件函數
    print("\n🎨 UI 組件函數檢查:")
    ui_functions = [
        'apply_custom_styles',
        'render_sidebar',
        'render_single_image_result',
        'render_batch_processing_ui',
        'render_welcome_page',
    ]
    
    all_ui_functions_exist = True
    for func in ui_functions:
        exists = check_function_exists('ui_components.py', func)
        status = "✅" if exists else "❌"
        print(f"  {status} {func}()")
        if not exists:
            all_ui_functions_exist = False
    
    # 檢查 Phos.py 核心函數
    print("\n⚙️  核心處理函數檢查:")
    core_functions = [
        'get_cached_film_profile',
        'standardize',
        'spectral_response',
        'optical_processing',
        'process_image',
    ]
    
    all_core_functions_exist = True
    for func in core_functions:
        exists = check_function_exists('Phos.py', func)
        status = "✅" if exists else "❌"
        print(f"  {status} {func}()")
        if not exists:
            all_core_functions_exist = False
    
    # 檢查導入
    print("\n📦 導入語句檢查:")
    with open('Phos.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    imports_to_check = [
        ('from ui_components import', 'UI 組件導入'),
        ('apply_custom_styles', 'CSS 樣式函數'),
        ('render_sidebar', '側邊欄函數'),
        ('render_single_image_result', '單張結果顯示'),
        ('render_batch_processing_ui', '批量處理 UI'),
        ('render_welcome_page', '歡迎頁面'),
    ]
    
    all_imports_ok = True
    for import_text, description in imports_to_check:
        exists = import_text in content
        status = "✅" if exists else "❌"
        print(f"  {status} {description}")
        if not exists:
            all_imports_ok = False
    
    # 總結
    print("\n" + "=" * 60)
    if all_files_exist and all_ui_functions_exist and all_core_functions_exist and all_imports_ok:
        print("✅ 所有檢查通過！重構結構完整。")
        print("\n📋 下一步:")
        print("  1. 執行: streamlit run Phos.py")
        print("  2. 進行手動 UI 測試（參見 /tmp/UI_TEST_PLAN.md）")
        print("  3. 如測試通過，合併到 main 分支")
        return 0
    else:
        print("❌ 部分檢查失敗！請檢查上述項目。")
        return 1

if __name__ == '__main__':
    sys.exit(main())
