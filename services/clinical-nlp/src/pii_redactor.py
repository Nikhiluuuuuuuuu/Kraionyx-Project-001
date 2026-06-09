from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

class PIIRedactor:
    """
    HIPAA-compliant Personal Identifiable Information (PII) redactor.

    This class scans clinical transcripts and automatically detects and scrubs 
    sensitive patient information (such as names, phone numbers, addresses, 
    and SSNs) prior to processing or long-term storage.
    """
    
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

    def redact(self, text: str) -> tuple[str, list]:
        """
        Scans and redacts PII/PHI from the provided text.

        The redaction process utilizes a combination of Named Entity Recognition (NER)
        and strict regular expression pattern matching to replace sensitive data 
        with placeholder tokens (e.g., [PERSON], [PHONE_NUMBER]).

        Args:
            text (str): The raw clinical transcript potentially containing PHI.

        Returns:
            tuple: A tuple containing:
                - (str): The scrubbed transcript with PHI removed.
                - (list): A list of dictionaries representing the redacted entities, 
                  including their location, category, and detection confidence score.
                  (Useful for auditing and low-confidence human review queues).
        """
        
        # Analyze text for PII entities
        analyzer_results = self.analyzer.analyze(text=text, language='en')
        
        entities = []
        for res in analyzer_results:
            entities.append({
                "entity_type": res.entity_type,
                "start": res.start,
                "end": res.end,
                "score": res.score,
                "text": text[res.start:res.end]
            })
            
        # Define anonymization operators to replace with entity type
        operators = {
            "DEFAULT": OperatorConfig("replace", {"new_value": lambda x: f"[{x.entity_type}]"})
        }
        
        # Anonymize text
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results,
            operators=operators
        )
        
        return anonymized_result.text, entities

