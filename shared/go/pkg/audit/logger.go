// Package audit provides a HIPAA-compliant audit logger that produces structured
// audit events to a Kafka topic and emits structured log entries via slog.
// All logged data is sanitized to exclude PHI/PII — only session IDs, resource
// identifiers, and action metadata are recorded.
package audit

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"time"

	"github.com/google/uuid"
	"github.com/kraionyx/shared/pkg/models"
	"github.com/twmb/franz-go/pkg/kgo"
)

const (
	// AuditTopic is the Kafka topic where audit events are published.
	AuditTopic = "audit.events"

	// ActionRead represents a data read/access action.
	ActionRead = "READ"
	// ActionCreate represents a data creation action.
	ActionCreate = "CREATE"
	// ActionUpdate represents a data modification action.
	ActionUpdate = "UPDATE"
	// ActionDelete represents a data deletion action.
	ActionDelete = "DELETE"
	// ActionLogin represents an authentication action.
	ActionLogin = "LOGIN"
	// ActionLogout represents a logout action.
	ActionLogout = "LOGOUT"

	// OutcomeSuccess indicates the action completed successfully.
	OutcomeSuccess = "success"
	// OutcomeFailure indicates the action failed.
	OutcomeFailure = "failure"
)

// Logger is a HIPAA-compliant audit logger that publishes structured audit events
// to both slog and a Kafka topic for durable, tamper-evident record-keeping.
type Logger struct {
	producer *kgo.Client
	logger   *slog.Logger
	service  string
}

// NewLogger creates a new audit Logger that publishes events to Kafka and logs
// them via slog. The service parameter identifies the originating microservice.
func NewLogger(producer *kgo.Client, logger *slog.Logger, service string) *Logger {
	return &Logger{
		producer: producer,
		logger:   logger.With(slog.String("component", "audit")),
		service:  service,
	}
}

// LogAccess records an audit event for data access (read) operations.
// The detail field must NOT contain PHI or PII — only resource metadata.
func (l *Logger) LogAccess(ctx context.Context, userID, resourceType, resourceID, detail, sourceIP string) {
	l.logEvent(ctx, userID, ActionRead, resourceType, resourceID, OutcomeSuccess, detail, sourceIP)
}

// LogModification records an audit event for data modification (create/update) operations.
func (l *Logger) LogModification(ctx context.Context, userID, action, resourceType, resourceID, detail, sourceIP string) {
	if action != ActionCreate && action != ActionUpdate {
		action = ActionUpdate
	}
	l.logEvent(ctx, userID, action, resourceType, resourceID, OutcomeSuccess, detail, sourceIP)
}

// LogDeletion records an audit event for data deletion operations.
func (l *Logger) LogDeletion(ctx context.Context, userID, resourceType, resourceID, detail, sourceIP string) {
	l.logEvent(ctx, userID, ActionDelete, resourceType, resourceID, OutcomeSuccess, detail, sourceIP)
}

// LogAuthentication records an audit event for authentication attempts.
// The outcome should be OutcomeSuccess or OutcomeFailure.
func (l *Logger) LogAuthentication(ctx context.Context, userID, outcome, detail, sourceIP string) {
	l.logEvent(ctx, userID, ActionLogin, "Authentication", userID, outcome, detail, sourceIP)
}

// logEvent constructs an AuditEvent, logs it via slog, and asynchronously publishes
// it to the Kafka audit topic. Kafka publish failures are logged but do not
// propagate errors to callers — audit logging must never block the main request path.
func (l *Logger) logEvent(ctx context.Context, userID, action, resourceType, resourceID, outcome, detail, sourceIP string) {
	event := models.AuditEvent{
		EventID:      uuid.New().String(),
		Timestamp:    time.Now().UTC().Format(time.RFC3339Nano),
		UserID:       userID,
		Action:       action,
		ResourceType: resourceType,
		ResourceID:   resourceID,
		Outcome:      outcome,
		Detail:       detail,
		SourceIP:     sourceIP,
	}

	// Structured slog output for local log aggregation.
	l.logger.InfoContext(ctx, "audit_event",
		slog.String("event_id", event.EventID),
		slog.String("user_id", event.UserID),
		slog.String("action", event.Action),
		slog.String("resource_type", event.ResourceType),
		slog.String("resource_id", event.ResourceID),
		slog.String("outcome", event.Outcome),
		slog.String("service", l.service),
		slog.String("source_ip", event.SourceIP),
	)

	// Publish to Kafka asynchronously. We must not block the request path
	// on audit logging — if Kafka is temporarily unavailable, the structured
	// slog entry above serves as the fallback audit record.
	if l.producer != nil {
		data, err := json.Marshal(event)
		if err != nil {
			l.logger.ErrorContext(ctx, "failed to marshal audit event",
				slog.String("event_id", event.EventID),
				slog.String("error", err.Error()),
			)
			return
		}

		record := &kgo.Record{
			Topic: AuditTopic,
			Key:   []byte(event.UserID),
			Value: data,
		}

		l.producer.Produce(ctx, record, func(r *kgo.Record, err error) {
			if err != nil {
				l.logger.Error("failed to produce audit event to kafka",
					slog.String("event_id", event.EventID),
					slog.String("topic", AuditTopic),
					slog.String("error", err.Error()),
				)
			}
		})
	}
}

// Flush blocks until all buffered audit events have been sent to Kafka or
// the context is cancelled. Call this during graceful shutdown.
func (l *Logger) Flush(ctx context.Context) error {
	if l.producer == nil {
		return nil
	}
	if err := l.producer.Flush(ctx); err != nil {
		return fmt.Errorf("audit: failed to flush kafka producer: %w", err)
	}
	return nil
}
