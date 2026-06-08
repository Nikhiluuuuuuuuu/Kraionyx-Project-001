import pytest
from unittest.mock import MagicMock, patch
from src.config import Config
from src.consumer import Consumer
from src.producer import Producer

@pytest.fixture
def mock_config():
    config = Config()
    config.kafka_brokers = "test_broker:9092"
    return config

@patch("src.consumer.KafkaConsumer")
def test_stt_consumer_init(mock_kafka, mock_config):
    consumer = Consumer(mock_config)
    mock_kafka.assert_called_once()
    
@patch("src.producer.KafkaProducer")
def test_stt_producer_init(mock_kafka, mock_config):
    producer = Producer(mock_config)
    mock_kafka.assert_called_once()
