import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from src.config import Config
from src.consumer import AudioConsumer
from src.producer import AudioProducer
from kraionyx_common.models import AudioChunkMessage

@pytest.fixture
def mock_config():
    config = Config()
    config.kafka_brokers = "test_broker:9092"
    config.encryption_key = "dummy_key_in_base64"
    return config

@patch("src.consumer.Consumer")
def test_audio_consumer_init(mock_kafka, mock_config):
    consumer = AudioConsumer(mock_config)
    mock_kafka.assert_called_once()


@patch("src.producer.Producer")
def test_audio_producer_produce(mock_kafka, mock_config):
    producer = AudioProducer(mock_config)
    mock_kafka.assert_called_once()
    
    # Mock produce
    producer.produce("test_topic", "test_key", {"data": "test"})
    producer._producer.produce.assert_called_once()

def test_audio_chunk_message_serialization():
    msg = AudioChunkMessage(
        session_id="session_123",
        chunk_index=0,
        timestamp_ms=1000,
        audio_data="encrypted_data",
        format="pcm_s16le",
        sample_rate=16000,
        channels=1
    )
    serialized = msg.to_dict()
    assert serialized["session_id"] == "session_123"
    
    deserialized = AudioChunkMessage.from_dict(serialized)
    assert deserialized.session_id == msg.session_id
