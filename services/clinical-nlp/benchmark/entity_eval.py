import json
import structlog
import os
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger(__name__)

def evaluate_extraction(test_cases: List[Dict]) -> Dict:
    results = []
    total_f1 = 0.0
    
    for case in test_cases:
        expected = set(case["expected_entities"])
        extracted = set(case["extracted_entities"])
        
        true_positives = len(expected.intersection(extracted))
        false_positives = len(extracted - expected)
        false_negatives = len(expected - extracted)
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        results.append({
            "id": case.get("id", "unknown"),
            "transcript": case["transcript"],
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "missing_entities": list(expected - extracted),
            "extra_entities": list(extracted - expected)
        })
        total_f1 += f1_score
        
    avg_f1 = total_f1 / len(test_cases) if test_cases else 0.0
    
    return {
        "average_f1_score": avg_f1,
        "details": results
    }

if __name__ == "__main__":
    # Sample Medical NLP Benchmarks
    test_cases = [
        {
            "id": "test_nlp_1",
            "transcript": "patient presents with acute myocardial infarction and requires immediate nitroglycerin",
            "expected_entities": ["acute myocardial infarction", "nitroglycerin"],
            "extracted_entities": ["acute myocardial infarction", "nitroglycerin"]
        },
        {
            "id": "test_nlp_2",
            "transcript": "administer fifty milligrams of metoprolol orally twice a day",
            "expected_entities": ["metoprolol", "50mg", "BID"],
            "extracted_entities": ["metoprolol", "fifty milligrams"]
        },
        {
            "id": "test_nlp_3",
            "transcript": "patient reports severe headache and photophobia, suspect migraine.",
            "expected_entities": ["headache", "photophobia", "migraine"],
            "extracted_entities": ["severe headache", "photophobia", "migraine"]
        }
    ]
    
    logger.info("Running Clinical Entity Extraction Evaluation...")
    report = evaluate_extraction(test_cases)
    
    logger.info(f"Average F1 Score: {report['average_f1_score']:.4f}")
    
    os.makedirs("results", exist_ok=True)
    with open("results/nlp_validation_results.json", "w") as f:
        json.dump(report, f, indent=4)
        
    logger.info("Saved validation results to results/nlp_validation_results.json")
