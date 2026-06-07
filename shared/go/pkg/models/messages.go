// Package models defines shared Kafka message schemas for the Kraionyx
// medical STT and EHR integration pipeline. These types are used across
// all microservices for serialization and deserialization of messages
// flowing through the Kafka topic topology.
package models

// AudioChunkMessage represents a chunk of encrypted audio data published
// to the "audio.raw.chunks" Kafka topic by the API Gateway.
type AudioChunkMessage struct {
	// SessionID uniquely identifies the recording session.
	SessionID string `json:"session_id"`
	// ChunkIndex is the zero-based sequential index of this chunk within the session.
	ChunkIndex int `json:"chunk_index"`
	// TimestampMS is the Unix timestamp in milliseconds when the chunk was received.
	TimestampMS int64 `json:"timestamp_ms"`
	// AudioData is the base64-encoded AES-256-GCM encrypted audio payload.
	AudioData string `json:"audio_data"`
	// Format indicates the audio encoding format (e.g., "pcm_16khz", "opus", "wav").
	Format string `json:"format"`
	// SampleRate is the audio sample rate in Hz (e.g., 16000).
	SampleRate int `json:"sample_rate"`
	// Channels is the number of audio channels (1=mono, 2=stereo).
	Channels int `json:"channels"`
}

// SpeakerSegment represents a segment of transcribed speech attributed to
// a specific speaker, as identified by the diarization pipeline.
type SpeakerSegment struct {
	// SpeakerLabel identifies the speaker (e.g., "doctor", "patient", "speaker_0").
	SpeakerLabel string `json:"speaker_label"`
	// StartTime is the segment start time in seconds from the beginning of the recording.
	StartTime float64 `json:"start_time"`
	// EndTime is the segment end time in seconds from the beginning of the recording.
	EndTime float64 `json:"end_time"`
	// Text is the transcribed text for this segment.
	Text string `json:"text"`
	// Confidence is the transcription confidence score between 0.0 and 1.0.
	Confidence float32 `json:"confidence"`
}

// TranscriptionResultMessage represents the output of the STT engine, published
// to the "transcription.results" Kafka topic.
type TranscriptionResultMessage struct {
	// SessionID links this result back to the originating recording session.
	SessionID string `json:"session_id"`
	// Segments contains speaker-diarized transcript segments.
	Segments []SpeakerSegment `json:"segments"`
	// FullTranscript is the concatenated transcript text across all segments.
	FullTranscript string `json:"full_transcript"`
	// Language is the detected or configured language code (e.g., "en-US").
	Language string `json:"language"`
	// OverallConfidence is the aggregate confidence score for the entire transcription.
	OverallConfidence float32 `json:"overall_confidence"`
	// ProcessedAtMS is the Unix timestamp in milliseconds when STT processing completed.
	ProcessedAtMS int64 `json:"processed_at_ms"`
}

// SOAPNote represents a structured clinical note following the SOAP format
// (Subjective, Objective, Assessment, Plan).
type SOAPNote struct {
	// Subjective contains the patient's reported symptoms, history, and complaints.
	Subjective string `json:"subjective"`
	// Objective contains measurable clinical findings and observations.
	Objective string `json:"objective"`
	// Assessment contains the clinician's diagnosis or clinical impression.
	Assessment string `json:"assessment"`
	// Plan contains the treatment plan, medications, follow-up instructions.
	Plan string `json:"plan"`
	// ConfidenceScore indicates the NLP model's confidence in the generated note (0.0-1.0).
	ConfidenceScore float32 `json:"confidence_score"`
}

// ClinicalNoteMessage represents a generated clinical note published to the
// "clinical.notes.created" Kafka topic by the Clinical NLP service.
type ClinicalNoteMessage struct {
	// SessionID links this note to the originating recording session.
	SessionID string `json:"session_id"`
	// PatientID is the internal patient identifier (not PHI — it's a UUID reference).
	PatientID string `json:"patient_id"`
	// PractitionerID is the internal practitioner identifier.
	PractitionerID string `json:"practitioner_id"`
	// EncounterID is the clinical encounter identifier.
	EncounterID string `json:"encounter_id"`
	// SOAPNote is the structured SOAP note content.
	SOAPNote SOAPNote `json:"soap_note"`
	// RedactedTranscript is the full transcript with PHI/PII redacted.
	RedactedTranscript string `json:"redacted_transcript"`
	// Metadata contains optional key-value pairs for extensibility.
	Metadata map[string]string `json:"metadata,omitempty"`
	// CreatedAtMS is the Unix timestamp in milliseconds when the note was created.
	CreatedAtMS int64 `json:"created_at_ms"`
}

// FHIRPushMessage represents a FHIR resource to be pushed to an external EHR,
// published to the "fhir.outbound" Kafka topic by the FHIR Adapter.
type FHIRPushMessage struct {
	// SessionID links this push to the originating session.
	SessionID string `json:"session_id"`
	// ResourceType is the FHIR resource type (e.g., "DocumentReference", "DiagnosticReport").
	ResourceType string `json:"resource_type"`
	// FHIRJson is the serialized FHIR R4 JSON resource.
	FHIRJson string `json:"fhir_json"`
	// TargetEHRURL is the base URL of the target EHR FHIR server.
	TargetEHRURL string `json:"target_ehr_url"`
	// PatientFHIRID is the patient's FHIR resource ID on the target server.
	PatientFHIRID string `json:"patient_fhir_id"`
	// EncounterFHIRID is the encounter's FHIR resource ID on the target server.
	EncounterFHIRID string `json:"encounter_fhir_id"`
}

// PipelineError represents an error event published to the "pipeline.errors"
// dead-letter topic for investigation and reprocessing.
type PipelineError struct {
	// SessionID identifies the session where the error occurred.
	SessionID string `json:"session_id"`
	// Stage identifies the pipeline stage that produced the error (e.g., "stt", "nlp", "fhir").
	Stage string `json:"stage"`
	// ErrorMessage is a human-readable description of the error (must not contain PHI).
	ErrorMessage string `json:"error_message"`
	// OriginalData optionally contains the message payload that caused the error.
	OriginalData string `json:"original_data,omitempty"`
	// TimestampMS is the Unix timestamp in milliseconds when the error occurred.
	TimestampMS int64 `json:"timestamp_ms"`
}

// AuditEvent represents a HIPAA-compliant audit log entry published to the
// "audit.events" Kafka topic for compliance and forensic review.
type AuditEvent struct {
	// EventID is the unique identifier for this audit event.
	EventID string `json:"event_id"`
	// Timestamp is the ISO 8601 timestamp of the event.
	Timestamp string `json:"timestamp"`
	// UserID identifies the user or service that performed the action.
	UserID string `json:"user_id"`
	// Action describes what was done (e.g., "READ", "CREATE", "UPDATE", "DELETE", "LOGIN").
	Action string `json:"action"`
	// ResourceType is the type of resource acted upon (e.g., "Session", "ClinicalNote").
	ResourceType string `json:"resource_type"`
	// ResourceID is the identifier of the specific resource.
	ResourceID string `json:"resource_id"`
	// Outcome indicates success or failure (e.g., "success", "failure").
	Outcome string `json:"outcome"`
	// Detail provides additional context about the event (must not contain PHI).
	Detail string `json:"detail,omitempty"`
	// SourceIP is the IP address from which the action originated.
	SourceIP string `json:"source_ip,omitempty"`
}
