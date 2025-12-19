"""
Phos 0.1.1 - 改進版本示例

展示如何使用 film_models 模組同時保持向後兼容
"""

# 在主程序開頭添加這段代碼：

from film_models import get_film_profile, FilmProfile

# 添加一個適配器函數，將 FilmProfile 轉換為原有格式
def film_profile_to_legacy_params(film: FilmProfile):
    """
    將 FilmProfile 對象轉換為原有的 37 個參數格式
    
    這個函數作為過渡期使用，讓新的數據結構可以與舊代碼兼容
    
    Args:
        film: FilmProfile 對象
        
    Returns:
        tuple: 包含所有原有參數的元組
    """
    # 獲取光譜響應
    r_r, r_g, r_b, g_r, g_g, g_b, b_r, b_g, b_b, t_r, t_g, t_b = film.get_spectral_response()
    
    # 獲取各層參數
    if film.color_type == "color" and film.red_layer and film.green_layer and film.blue_layer:
        d_r = film.red_layer.diffuse_weight
        l_r = film.red_layer.direct_weight
        x_r = film.red_layer.response_curve
        n_r = film.red_layer.grain_intensity
        
        d_g = film.green_layer.diffuse_weight
        l_g = film.green_layer.direct_weight
        x_g = film.green_layer.response_curve
        n_g = film.green_layer.grain_intensity
        
        d_b = film.blue_layer.diffuse_weight
        l_b = film.blue_layer.direct_weight
        x_b = film.blue_layer.response_curve
        n_b = film.blue_layer.grain_intensity
        
        d_l = None
        l_l = None
        x_l = None
        n_l = film.panchromatic_layer.grain_intensity
    else:
        d_r = 0
        l_r = 0
        x_r = 0
        n_r = 0
        
        d_g = 0
        l_g = 0
        x_g = 0
        n_g = 0
        
        d_b = 0
        l_b = 0
        x_b = 0
        n_b = 0
        
        d_l = film.panchromatic_layer.diffuse_weight
        l_l = film.panchromatic_layer.direct_weight
        x_l = film.panchromatic_layer.response_curve
        n_l = film.panchromatic_layer.grain_intensity
    
    # 獲取 tone mapping 參數
    gamma = film.tone_params.gamma
    A = film.tone_params.shoulder_strength
    B = film.tone_params.linear_strength
    C = film.tone_params.linear_angle
    D = film.tone_params.toe_strength
    E = film.tone_params.toe_numerator
    F = film.tone_params.toe_denominator
    
    color_type = film.color_type
    sens_factor = film.sensitivity_factor
    
    return (r_r, r_g, r_b, g_r, g_g, g_b, b_r, b_g, b_b, t_r, t_g, t_b,
            color_type, sens_factor,
            d_r, l_r, x_r, n_r,
            d_g, l_g, x_g, n_g,
            d_b, l_b, x_b, n_b,
            d_l, l_l, x_l, n_l,
            gamma, A, B, C, D, E, F)


# 然後替換原有的 film_choose 函數：
def film_choose(film_type):
    """
    選取胶片類型（改進版）
    
    現在使用 FilmProfile 對象，然後轉換為原有格式
    這樣保持了向後兼容，同時使用了更好的數據結構
    """
    try:
        film = get_film_profile(film_type)
        return film_profile_to_legacy_params(film)
    except ValueError as e:
        # 如果胶片類型不存在，返回默認值（NC200）
        print(f"警告: {e}, 使用默認胶片 NC200")
        film = get_film_profile("NC200")
        return film_profile_to_legacy_params(film)


# 使用示例：
if __name__ == "__main__":
    # 測試新的 film_choose 函數
    params = film_choose("NC200")
    print(f"NC200 參數數量: {len(params)}")
    print(f"色彩類型: {params[12]}")  # color_type
    print(f"敏感係數: {params[13]}")  # sens_factor
    
    # 也可以直接使用 FilmProfile 對象
    film = get_film_profile("AS100")
    print(f"\\n{film.name} 胶片:")
    print(f"  類型: {film.color_type}")
    print(f"  Gamma: {film.tone_params.gamma}")
    print(f"  全色層藍光吸收: {film.panchromatic_layer.b_response_weight}")
