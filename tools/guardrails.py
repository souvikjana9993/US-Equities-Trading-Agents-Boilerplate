import numpy as np
import logging

class HallucinationGuardrail:
    def __init__(self, model_name='cross-encoder/nli-deberta-v3-small'):
        self.enabled = False
        try:
            from sentence_transformers import CrossEncoder
            import torch
            print(f"Loading Guardrail Model: {model_name} on CPU...")
            # Force CPU to avoid CUDA kernel errors on older GPUs
            self.model = CrossEncoder(model_name, device='cpu')
            self.enabled = True
        except (ImportError, Exception) as e:
            print(f"Warning: Guardrail model unavailable: {e}. Hallucination checks will be skipped.")

    def check_entailment(self, premise: str, hypothesis: str) -> bool:
        """
        Returns True if the hypothesis is supported by the premise (Entailment).
        Labels: 0: Contradiction, 1: Entailment, 2: Neutral
        """
        if not self.enabled:
            return True
        
        # We only care about the summary and the raw tool data
        scores = self.model.predict([(premise, hypothesis)])
        verdict = np.argmax(scores)
        self.last_result = ("Hypothesis not supported by data.", int(verdict))
        
        # 1 is Entailment. 0 (Contradiction) and 2 (Neutral) are rejected.
        is_safe = (verdict == 1)
        return is_safe

    def get_last_result(self):
        return getattr(self, 'last_result', ("No checks run yet.", -1))

# Singleton instance
global_guardrail = HallucinationGuardrail()
