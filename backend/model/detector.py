import os

# ── CPU 스레드 최적화  ──────────────
_N_THREADS = os.cpu_count() or 4
os.environ["OMP_NUM_THREADS"]  = str(_N_THREADS)
os.environ["MKL_NUM_THREADS"]  = str(_N_THREADS)
os.environ["OPENBLAS_NUM_THREADS"] = str(_N_THREADS)

import torch
torch.set_num_threads(_N_THREADS)

import pickle
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Any
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"

MODEL_CONFIG = {
    0: {
        "name": "small",
        "embed_model": "intfloat/multilingual-e5-small",
        "clf_path": ARTIFACTS_DIR / "small" / "detector_model.pkl"
    },
    1: {
        "name": "large",
        "embed_model": "intfloat/multilingual-e5-large",
        "clf_path": ARTIFACTS_DIR / "large" / "detector_model_large.pkl"
    }
}

class MaliciousPromptDetector:
    def __init__(self):
        # 모델 및 임베더 캐싱을 위한 딕셔너리
        self._models: Dict[int, Any] = {}
        self._embedders: Dict[int, SentenceTransformer] = {}

    def _load_resources(self, model_type: int):
        if model_type not in self._models:
            config = MODEL_CONFIG.get(model_type)
            if not config:
                raise ValueError(f"지원하지 않는 모델 타입입니다: {model_type} (0: Small, 1: Large)")

            if not config["clf_path"].exists():
                raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {config['clf_path']}")

            print(f"[{config['name']}] 리소스 로딩 중...")
            
            # 머신러닝 모델(LightGBM) 로드
            with open(config["clf_path"], "rb") as f:
                self._models[model_type] = pickle.load(f)
            
            # 임베딩 모델(SentenceTransformer) 로드
            self._embedders[model_type] = SentenceTransformer(config["embed_model"])
            
            print(f"[{config['name']}] 로드 완료.")

        return self._embedders[model_type], self._models[model_type]

    def analyze(self, prompt: str, model_type: int = 0) -> Tuple[bool, int]:
        """
        프롬프트를 분석하여 악성 여부와 위험도 점수를 반환합니다.
        
        Args:
            prompt (str): 사용자 입력 텍스트
            model_type (int): 0 (Small), 1 (Large)
            
        Returns:
            Tuple[bool, int]: (악성 여부, 위험도 점수 0-100)
        """
        try:
            embedder, classifier = self._load_resources(model_type)
            
            # 1. 전처리: 모델 학습 시와 동일하게 "query: " 접두사 추가
            # (E5 모델 계열은 retrieval task에서 query: 또는 passage: 접두사가 권장됨)
            formatted_prompt = f"query: {prompt}"
            
            # 2. 임베딩 벡터 생성
            embedding = embedder.encode([formatted_prompt], show_progress_bar=False)
            
            # 3. 모델 추론 (확률 값 반환)
            # LightGBM의 predict는 binary objective에서 확률(0~1)을 반환합니다.
            prob = classifier.predict(embedding)[0]
            
            # 4. 결과 가공
            is_malicious = bool(prob >= 0.5)
            risk_score = int(prob * 100)
            
            return is_malicious, risk_score
            
        except Exception as e:
            print(f"분석 중 오류 발생: {e}")
            # 에러 발생 시 안전하게 '정상'으로 처리하거나 예외를 던질 수 있음
            return False, 0

_detector_instance = MaliciousPromptDetector()

def analyze_prompt(prompt: str, model_type: int = 0) -> Tuple[bool, int]:
    """외부에서 호출할 메인 함수"""
    return _detector_instance.analyze(prompt, model_type)

if __name__ == "__main__":
    import sys
    print("\n" + "="*50)
    print("   Malicious Prompt Detector Interactive Test")
    print("="*50)
    
    # 모델 타입 선택
    m_type_str = input("Select Model Type (0: Small, 1: Large) [default: 0]: ").strip()
    m_type = int(m_type_str) if m_type_str in ["0", "1"] else 0
    
    print(f"\nUsing {'LARGE' if m_type == 1 else 'SMALL'} model.")
    print("Type 'exit' or 'quit' to stop.\n")
    
    while True:
        user_input = input("Prompt >>> ").strip()
        
        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit"]:
            break
            
        is_mal, score = analyze_prompt(user_input, model_type=m_type)
        
        status = " [!] MALICIOUS" if is_mal else " [v] NORMAL"
        print(f"Result: {status} | Risk Score: {score}/100")
        print("-" * 30)
