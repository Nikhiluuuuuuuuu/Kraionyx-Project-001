import json
import jiwer
import logging
import os
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fallback basic WER function if jiwer isn't installed properly
def basic_wer(reference: str, hypothesis: str) -> float:
    r = reference.split()
    h = hypothesis.split()
    
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        for j in range(len(h) + 1):
            if i == 0:
                d[0][j] = j
            elif j == 0:
                d[i][0] = i
    
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            if r[i - 1] == h[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                substitution = d[i - 1][j - 1] + 1
                insertion = d[i][j - 1] + 1
                deletion = d[i - 1][j] + 1
                d[i][j] = min(substitution, insertion, deletion)
                
    return d[len(r)][len(h)] / max(len(r), 1)

def evaluate_wer(test_cases: List[Dict[str, str]]) -> Dict:
    results = []
    total_wer = 0.0
    
    for case in test_cases:
        ref = case["reference"]
        hyp = case["hypothesis"]
        
        try:
            wer_score = jiwer.wer(ref, hyp)
        except Exception as e:
            logger.warning(f"jiwer failed, using basic_wer: {e}")
            wer_score = basic_wer(ref, hyp)
            
        results.append({
            "id": case.get("id", "unknown"),
            "reference": ref,
            "hypothesis": hyp,
            "wer": wer_score
        })
        total_wer += wer_score
        
    avg_wer = total_wer / len(test_cases) if test_cases else 0.0
    
    return {
        "average_wer": avg_wer,
        "details": results
    }

if __name__ == "__main__":
    # Sample Medical STT Benchmarks
    test_cases = [
        {
            "id": "test_1",
            "reference": "patient presents with acute myocardial infarction and requires immediate nitroglycerin",
            "hypothesis": "patient presents with acute myocardial infraction and requires immediate nitroglycerin"
        },
        {
            "id": "test_2",
            "reference": "administer fifty milligrams of metoprolol orally twice a day",
            "hypothesis": "administer fifteen milligrams of metoprolol orally twice a day"
        },
        {
            "id": "test_3",
            "reference": "the patient was prescribed amoxicillin for a suspected upper respiratory tract infection",
            "hypothesis": "the patient was prescribed amoxicillin for a suspected upper respiratory tract infection"
        }
    ]
    
    logger.info("Running WER Evaluation on STT Engine Outputs...")
    report = evaluate_wer(test_cases)
    
    logger.info(f"Average WER: {report['average_wer']:.4f}")
    
    os.makedirs("results", exist_ok=True)
    with open("results/stt_validation_results.json", "w") as f:
        json.dump(report, f, indent=4)
        
    logger.info("Saved validation results to results/stt_validation_results.json")
