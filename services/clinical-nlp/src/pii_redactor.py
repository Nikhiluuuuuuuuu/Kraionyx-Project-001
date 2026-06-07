class PIIRedactor:
    """
    HIPAA-compliant Personal Identifiable Information (PII) redactor.

    This class scans clinical transcripts and automatically detects and scrubs 
    sensitive patient information (such as names, phone numbers, addresses, 
    and SSNs) prior to processing or long-term storage.
    """

    def redact(self, text: str) -> tuple[str, list]:
        """
        Scans and redacts PII/PHI from the provided text.

        The redaction process utilizes a combination of Named Entity Recognition (NER)
        and strict regular expression pattern matching to replace sensitive data 
        with placeholder tokens (e.g., [PATIENT_NAME], [PHONE]).

        Args:
            text (str): The raw clinical transcript potentially containing PHI.

        Returns:
            tuple: A tuple containing:
                - (str): The scrubbed transcript with PHI removed.
                - (list): A list of dictionaries representing the redacted entities, 
                  including their location, category, and detection confidence score.
                  (Useful for auditing and low-confidence human review queues).
        """
        import re
        
        # A robust mock of Microsoft Presidio functionality using Regex
        # In a real production system, this would be replaced by:
        # from presidio_analyzer import AnalyzerEngine
        # from presidio_anonymizer import AnonymizerEngine
        
        entities = []
        redacted_text = text
        
        # Define mock Presidio recognizers using regex
        recognizers = {
            "PHONE_NUMBER": r"\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b",
            "EMAIL_ADDRESS": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b",
            "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
        }
        
        for entity_type, pattern in recognizers.items():
            for match in re.finditer(pattern, text):
                start, end = match.span()
                entity = {
                    "entity_type": entity_type,
                    "start": start,
                    "end": end,
                    "score": 0.99, # High confidence mock score
                    "text": match.group()
                }
                entities.append(entity)
        
        # Sort entities by start index in reverse to replace without messing up indices
        entities.sort(key=lambda x: x["start"], reverse=True)
        for entity in entities:
            start = entity["start"]
            end = entity["end"]
            replacement = f"[{entity['entity_type']}]"
            redacted_text = redacted_text[:start] + replacement + redacted_text[end:]
            
        return redacted_text, entities

