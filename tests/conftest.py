"""
Pytest 配置文件
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_image():
    """創建測試用的樣本圖像 (100x100 RGB)"""
    np.random.seed(42)
    return np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)


@pytest.fixture
def sample_image_float():
    """創建測試用的浮點數圖像 (100x100, 0-1 範圍)"""
    np.random.seed(42)
    return np.random.rand(100, 100).astype(np.float32)


@pytest.fixture
def black_image():
    """全黑圖像"""
    return np.zeros((100, 100, 3), dtype=np.uint8)


@pytest.fixture
def white_image():
    """全白圖像"""
    return np.ones((100, 100, 3), dtype=np.uint8) * 255


@pytest.fixture
def gradient_image():
    """漸變圖像（用於測試 tone mapping）"""
    gradient = np.linspace(0, 1, 100).astype(np.float32)
    return np.tile(gradient, (100, 1))


@pytest.fixture
def all_film_types():
    """所有支援的胶片類型"""
    return ["NC200", "AS100", "FS200", "Portra400", "Ektar100", "HP5Plus400", "Cinestill800T"]
