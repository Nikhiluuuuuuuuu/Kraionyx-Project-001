import pytest
from unittest.mock import MagicMock, patch
from src.config import Config
from src.consumer import ClinicalConsumer
from src.producer import ClinicalProducer
from src.agents import ClinicalWorkflow

@pytest.fixture
def mock_config():
    config = Config()
    config.kafka_brokers = "test_broker:9092"
    return config

@patch("src.consumer.KafkaConsumer")
def test_clinical_consumer_init(mock_kafka, mock_config):
    consumer = ClinicalConsumer(mock_config)
    mock_kafka.assert_called_once()
    assert consumer.topic == mock_config.kafka_input_topic
    
@patch("src.producer.KafkaProducer")
def test_clinical_producer_produce(mock_kafka, mock_config):
    producer = ClinicalProducer(mock_config)
    mock_kafka.assert_called_once()
    
    producer.produce("test_topic", {"data": "test"})
    producer.producer.produce.assert_called_once()

@patch("src.llm.LLMBackend.generate")
def test_clinical_workflow(mock_generate, workflow):
    mock_generate.side_effect = [
        '{"symptoms": ["headache"]}', # Extract
        '{"subjective": "Headache", "objective": "Normal", "assessment": "Migraine", "plan": "Rest"}', # Synthesize
        '{"status": "APPROVED"}' # Verify
    ]
    result = workflow.process_transcript("patient_1", "Doctor: how are you? Patient: I am fine.")
    assert result["status"] == "APPROVED"
    assert "soap_note" in result
    assert "subjective" in result["soap_note"]
    assert "objective" in result["soap_note"]
    assert "assessment" in result["soap_note"]
    assert "plan" in result["soap_note"]

# minor clinical-nlp test update
