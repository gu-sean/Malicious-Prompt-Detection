import sys
from pathlib import Path
from typing import Tuple

# 프로젝트 루트를 Python path에 추가하여 backend 모듈을 찾을 수 있게 함
BASE_DIR = Path(__file__).parent.parent.parent.parent
backend_dir = str(BASE_DIR)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

try:
    from backend.model.detector import analyze_prompt, preload_all_models
except ImportError:
    # 모듈을 찾지 못할 경우를 대비한 대체 로직 (또는 에러 처리)
    analyze_prompt = None
    preload_all_models = None

def analyze_prompt_threat(prompt: str, model_type: int = 0) -> Tuple[bool, int]:
    """
    AI 모델을 사용하여 프롬프트의 위험을 분석합니다.
    
    Args:
        prompt (str): 사용자의 입력 프롬프트
        model_type (int): 사용할 모델 타입 (0: Small, 1: Large)
        
    Returns:
        Tuple[bool, int]: (악성 여부 True/False, 위험도 점수 0 ~ 100)
    """
    if analyze_prompt:
        return analyze_prompt(prompt, model_type)
    
    # 모델 로드 실패 시 기본값 (안전을 위해 False 반환)
    print("Warning: MaliciousPromptDetector not found. Returning default values.")
    return False, 0
