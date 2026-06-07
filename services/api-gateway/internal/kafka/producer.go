// Package kafka provides a Kafka producer for the API Gateway service,
// built on top of franz-go. It handles publishing audio chunks and audit
// events with LZ4 compression and session-based partitioning.
package kafka

import (
	"context"

	"encoding/json"
	"fmt"
	"log/slog"

	"github.com/kraionyx/shared/pkg/models"
	"github.com/twmb/franz-go/pkg/kgo"
)

const (
	// TopicAudioChunks is the Kafka topic for raw encrypted audio data.
	TopicAudioChunks = "audio.raw.chunks"
	// TopicAuditEvents is the Kafka topic for HIPAA audit trail events.
	TopicAuditEvents = "audit.events"
	// TopicPipelineErrors is the Kafka topic for pipeline error dead-letter events.
	TopicPipelineErrors = "pipeline.errors"
)

// Producer wraps a franz-go Kafka client configured for the API Gateway's
// publishing needs: audio chunks, audit events, and pipeline errors.
type Producer struct {
	client *kgo.Client
	logger *slog.Logger
}

// NewProducer creates a new Kafka producer connected to the given broker addresses.
// It configures LZ4 compression, idempotent production, and async error logging.
func NewProducer(brokers []string, logger *slog.Logger) (*Producer, error) {
	if len(brokers) == 0 {
		return nil, fmt.Errorf("kafka: at least one broker address is required")
	}


	client, err := kgo.NewClient(
		kgo.SeedBrokers(brokers...),
		kgo.DialTLS(),
		kgo.ProducerLinger(0),
		kgo.ProducerBatchCompression(kgo.Lz4Compression()),
		kgo.AllowAutoTopicCreation(),
	)
	if err != nil {
		return nil, fmt.Errorf("kafka: failed to create producer: %w", err)
	}

	return &Producer{
		client: client,
		logger: logger.With(slog.String("component", "kafka_producer")),
	}, nil
}

// PublishAudioChunk serializes and publishes an AudioChunkMessage to the
// audio.raw.chunks topic. The session_id is used as the partition key to
// ensure ordered delivery of chunks within a session.
func (p *Producer) PublishAudioChunk(ctx context.Context, msg models.AudioChunkMessage) error {
	data, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("kafka: failed to marshal audio chunk: %w", err)
	}

	record := &kgo.Record{
		Topic: TopicAudioChunks,
		Key:   []byte(msg.SessionID),
		Value: data,
	}

	p.client.Produce(ctx, record, func(r *kgo.Record, err error) {
		if err != nil {
			p.logger.Error("failed to produce audio chunk",
				slog.String("session_id", msg.SessionID),
				slog.Int("chunk_index", msg.ChunkIndex),
				slog.String("topic", TopicAudioChunks),
				slog.String("error", err.Error()),
			)
		} else {
			p.logger.Debug("produced audio chunk",
				slog.String("session_id", msg.SessionID),
				slog.Int("chunk_index", msg.ChunkIndex),
				slog.Int64("offset", r.Offset),
				slog.Int("partition", int(r.Partition)),
			)
		}
	})

	return nil
}

// PublishAuditEvent serializes and publishes an AuditEvent to the audit.events
// topic. The user_id is used as the partition key.
func (p *Producer) PublishAuditEvent(ctx context.Context, event models.AuditEvent) error {
	data, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("kafka: failed to marshal audit event: %w", err)
	}

	record := &kgo.Record{
		Topic: TopicAuditEvents,
		Key:   []byte(event.UserID),
		Value: data,
	}

	p.client.Produce(ctx, record, func(r *kgo.Record, err error) {
		if err != nil {
			p.logger.Error("failed to produce audit event",
				slog.String("event_id", event.EventID),
				slog.String("topic", TopicAuditEvents),
				slog.String("error", err.Error()),
			)
		}
	})

	return nil
}

// PublishPipelineError serializes and publishes a PipelineError to the
// pipeline.errors dead-letter topic.
func (p *Producer) PublishPipelineError(ctx context.Context, pErr models.PipelineError) error {
	data, err := json.Marshal(pErr)
	if err != nil {
		return fmt.Errorf("kafka: failed to marshal pipeline error: %w", err)
	}

	record := &kgo.Record{
		Topic: TopicPipelineErrors,
		Key:   []byte(pErr.SessionID),
		Value: data,
	}

	p.client.Produce(ctx, record, func(r *kgo.Record, err error) {
		if err != nil {
			p.logger.Error("failed to produce pipeline error",
				slog.String("session_id", pErr.SessionID),
				slog.String("topic", TopicPipelineErrors),
				slog.String("error", err.Error()),
			)
		}
	})

	return nil
}

// Client returns the underlying franz-go client, useful for passing to the
// shared audit logger which needs a raw *kgo.Client.
func (p *Producer) Client() *kgo.Client {
	return p.client
}

// Close flushes pending records and closes the Kafka producer.
func (p *Producer) Close() {
	p.logger.Info("closing kafka producer")
	p.client.Close()
}
