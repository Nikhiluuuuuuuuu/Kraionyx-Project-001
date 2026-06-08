package kafka

import (
	"context"
	"crypto/tls"
	"fmt"
	"log/slog"

	"github.com/twmb/franz-go/pkg/kgo"
)

type Consumer struct {
	client   *kgo.Client
	dlqTopic string
}

func NewConsumer(brokers []string, group, dlqTopic string, tlsConfig *tls.Config) (*Consumer, error) {
	opts := []kgo.Opt{
		kgo.SeedBrokers(brokers...),
		kgo.ConsumerGroup(group),
	}

	if tlsConfig != nil {
		opts = append(opts, kgo.DialTLSConfig(tlsConfig))
	}

	client, err := kgo.NewClient(opts...)
	if err != nil {
		return nil, fmt.Errorf("failed to create kafka consumer: %w", err)
	}

	return &Consumer{client: client, dlqTopic: dlqTopic}, nil
}

func (c *Consumer) Consume(ctx context.Context, handler func(context.Context, []byte) error) {
	for {
		fetches := c.client.PollFetches(ctx)
		if fetches.IsClientClosed() || ctx.Err() != nil {
			return
		}

		fetches.EachError(func(t string, p int32, err error) {
			slog.Error("kafka fetch error", "topic", t, "partition", p, "error", err)
		})

		fetches.EachRecord(func(record *kgo.Record) {
			err := handler(ctx, record.Value)
			if err != nil {
				slog.Error("failed to process record, sending to DLQ", "error", err)
				errDLQ := c.sendToDLQ(ctx, record, err)
				if errDLQ != nil {
					slog.Error("failed to send to DLQ", "error", errDLQ)
				}
			}
		})
	}
}

func (c *Consumer) sendToDLQ(ctx context.Context, record *kgo.Record, procErr error) error {
	if c.dlqTopic == "" {
		return fmt.Errorf("DLQ topic not configured")
	}
	dlqRecord := &kgo.Record{
		Topic: c.dlqTopic,
		Key:   record.Key,
		Value: record.Value,
		Headers: append(record.Headers, kgo.RecordHeader{
			Key:   "error",
			Value: []byte(procErr.Error()),
		}),
	}
	
	return c.client.ProduceSync(ctx, dlqRecord).FirstErr()
}
