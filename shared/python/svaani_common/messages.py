from pydantic import BaseModel

class AudioChunkMessage(BaseModel):
    session_id: str
    audio: list[float]
    sample_rate: int = 16000
    chunk_index: int
