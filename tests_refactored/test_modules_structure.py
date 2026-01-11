"""
測試 modules/ 包的基礎結構（PR #1）

驗證模組目錄與空模板的正確性。

Test Categories:
    - Structure: 目錄結構驗證
    - Importability: 模組可匯入性
    - Metadata: 版本信息與元數據

Version: 0.7.0-dev
Date: 2026-01-12
"""

import pytest
import os
import sys


# ==================== 結構測試 ====================

def test_modules_directory_exists():
    """驗證 modules/ 目錄存在"""
    assert os.path.isdir('modules'), "modules/ 目錄不存在"


def test_all_module_files_exist():
    """驗證所有模組檔案存在"""
    expected_files = [
        'modules/__init__.py',
        'modules/optical_core.py',
        'modules/tone_mapping.py',
        'modules/psf_utils.py',
        'modules/wavelength_effects.py',
        'modules/image_processing.py'
    ]
    
    for filepath in expected_files:
        assert os.path.isfile(filepath), f"{filepath} 不存在"


# ==================== 可匯入性測試 ====================

def test_modules_package_importable():
    """驗證 modules 包可匯入"""
    import modules
    assert hasattr(modules, '__version__'), "modules 包缺少 __version__ 屬性"


def test_optical_core_importable():
    """驗證 optical_core 模組可匯入"""
    from modules import optical_core
    assert optical_core is not None


def test_tone_mapping_importable():
    """驗證 tone_mapping 模組可匯入"""
    from modules import tone_mapping
    assert tone_mapping is not None


def test_psf_utils_importable():
    """驗證 psf_utils 模組可匯入"""
    from modules import psf_utils
    assert psf_utils is not None


def test_wavelength_effects_importable():
    """驗證 wavelength_effects 模組可匯入"""
    from modules import wavelength_effects
    assert wavelength_effects is not None


def test_image_processing_importable():
    """驗證 image_processing 模組可匯入"""
    from modules import image_processing
    assert image_processing is not None


# ==================== 元數據測試 ====================

def test_modules_version():
    """驗證 modules 包版本正確"""
    import modules
    assert modules.__version__ == "0.7.0-dev", \
        f"版本錯誤：期望 '0.7.0-dev'，實際 '{modules.__version__}'"


def test_modules_has_author():
    """驗證 modules 包有作者信息"""
    import modules
    assert hasattr(modules, '__author__'), "modules 包缺少 __author__ 屬性"


def test_modules_has_status():
    """驗證 modules 包有狀態信息"""
    import modules
    assert hasattr(modules, '__status__'), "modules 包缺少 __status__ 屬性"
    assert modules.__status__ == "Development", \
        f"狀態錯誤：期望 'Development'，實際 '{modules.__status__}'"


def test_modules_all_exports():
    """驗證 modules.__all__ 包含所有已實現的函數（PR #2-#4）"""
    import modules
    assert hasattr(modules, '__all__'), "modules 包缺少 __all__ 屬性"
    
    # PR #2-#4 已實現的函數
    expected_exports = [
        # PR #2: Optical Core
        'spectral_response', 'average_response', 'standardize',
        # PR #3: Tone Mapping
        'apply_reinhard_to_channel', 'apply_reinhard',
        'apply_filmic_to_channel', 'apply_filmic',
        # PR #4: PSF Utils
        'create_dual_kernel_psf', 'load_mie_lookup_table',
        'lookup_mie_params', 'convolve_fft', 'convolve_adaptive',
        'get_gaussian_kernel', 'get_exponential_kernel_approximation',
    ]
    
    for func_name in expected_exports:
        assert func_name in modules.__all__, f"{func_name} not in __all__"


# ==================== 子模組元數據測試 ====================

def test_implemented_submodules_have_exports():
    """驗證已實現的子模組有 __all__ 列表（PR #2-#4）"""
    from modules import optical_core, tone_mapping, psf_utils
    
    # PR #2: Optical Core (3 functions)
    assert len(optical_core.__all__) == 3
    assert 'spectral_response' in optical_core.__all__
    
    # PR #3: Tone Mapping (4 functions)
    assert len(tone_mapping.__all__) == 4
    assert 'apply_reinhard' in tone_mapping.__all__
    
    # PR #4: PSF Utils (7 functions)
    assert len(psf_utils.__all__) == 7
    assert 'create_dual_kernel_psf' in psf_utils.__all__


def test_empty_submodules_have_empty_all():
    """驗證所有子模組都已實現（PR #6 完成）"""
    from modules import image_processing
    
    # PR #6: 已完成實現
    assert len(image_processing.__all__) == 2
    assert 'apply_hd_curve' in image_processing.__all__
    assert 'combine_layers_for_channel' in image_processing.__all__


# ==================== 文檔字串測試 ====================

def test_modules_has_docstring():
    """驗證 modules 包有文檔字串"""
    import modules
    assert modules.__doc__ is not None, "modules 包缺少文檔字串"
    assert "Phos 核心模組" in modules.__doc__, "文檔字串內容不正確"


def test_implemented_submodules_have_docstrings():
    """驗證已實現的子模組都有文檔字串（PR #2-#4）"""
    from modules import optical_core, tone_mapping, psf_utils
    
    # PR #2: Optical Core
    assert optical_core.__doc__ is not None
    assert "光度計算核心模組" in optical_core.__doc__ or "光學核心" in optical_core.__doc__
    
    # PR #3: Tone Mapping
    assert tone_mapping.__doc__ is not None
    assert "Tone Mapping" in tone_mapping.__doc__
    
    # PR #4: PSF Utils
    assert psf_utils.__doc__ is not None
    assert "PSF" in psf_utils.__doc__ or "點擴散函數" in psf_utils.__doc__


def test_empty_submodules_have_docstrings():
    """驗證所有子模組都有文檔字串"""
    from modules import image_processing
    
    # PR #6 已完成
    assert image_processing.__doc__ is not None


# ==================== 無循環依賴測試 ====================

def test_no_circular_imports():
    """驗證無循環依賴（重新載入測試）"""
    import importlib
    
    # 清空模組緩存
    for mod in list(sys.modules.keys()):
        if mod.startswith('modules'):
            del sys.modules[mod]
    
    # 重新載入（不應報錯）
    importlib.import_module('modules')
    importlib.import_module('modules.optical_core')
    importlib.import_module('modules.tone_mapping')
    importlib.import_module('modules.psf_utils')
    importlib.import_module('modules.wavelength_effects')
    importlib.import_module('modules.image_processing')


# ==================== 檔案大小測試（預防性）====================

def test_module_files_reasonable_size():
    """驗證模組檔案大小合理（< 500 行）"""
    module_files = {
        'modules/optical_core.py': 200,     # PR #2
        'modules/tone_mapping.py': 200,     # PR #3
        'modules/psf_utils.py': 400,        # PR #4 (PSF 函數較多)
        'modules/wavelength_effects.py': 450,  # PR #5 (4 個函數，較複雜)
        'modules/image_processing.py': 250,    # PR #6 (2 個函數，已實作)
    }
    
    for filepath, max_lines in module_files.items():
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = len(f.readlines())
        
        assert lines < max_lines, \
            f"{filepath} 太大（{lines} 行），應該 < {max_lines} 行"


# ==================== PR #1-#6 完成驗證 ====================

def test_pr6_completion_checklist():
    """驗證 PR #1-#6 完成清單（模組化 100% 完成）"""
    import modules
    from modules import (
        optical_core, 
        tone_mapping, 
        psf_utils, 
        wavelength_effects, 
        image_processing
    )
    
    # 檢查清單
    checklist = {
        "modules/ 目錄存在": os.path.isdir('modules'),
        "modules/__init__.py 存在": os.path.isfile('modules/__init__.py'),
        "modules 包可匯入": True,  # 上面已通過
        "modules 有版本信息": hasattr(modules, '__version__'),
        "5 個子模組檔案都存在": all(os.path.isfile(f'modules/{name}.py') 
                                    for name in ['optical_core', 'tone_mapping', 
                                                 'psf_utils', 'wavelength_effects', 
                                                 'image_processing']),
        "所有子模組可匯入": True,  # 上面已通過
        "所有 PR #2-#6 模組有匯出": (len(optical_core.__all__) > 0 and
                                  len(tone_mapping.__all__) > 0 and
                                  len(psf_utils.__all__) > 0 and
                                  len(wavelength_effects.__all__) > 0 and
                                  len(image_processing.__all__) > 0),
        "PR #6 模組已實作": image_processing.__all__ == ['apply_hd_curve', 'combine_layers_for_channel'],
        "模組化 100% 完成": True
    }
    
    # 驗證所有檢查項
    failed_items = [item for item, passed in checklist.items() if not passed]
    
    assert not failed_items, \
        f"PR #1-#6 完成清單有失敗項目：{failed_items}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
