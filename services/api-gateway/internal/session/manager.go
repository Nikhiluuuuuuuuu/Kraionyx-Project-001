// Package session provides a Redis-backed session manager for tracking
// active audio recording sessions. Sessions are stored as Redis hashes
// with a configurable TTL to ensure automatic cleanup of abandoned sessions.
package session

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

const (
	// keyPrefix is the Redis key namespace for sessions.
	keyPrefix = "session:"
)

var (
	// ErrSessionNotFound is returned when the requested session does not exist in Redis.
	ErrSessionNotFound = errors.New("session: not found")
	// ErrSessionClosed is returned when attempting to modify a session that has already been closed.
	ErrSessionClosed = errors.New("session: already closed")
)

// Session represents an active audio recording session.
type Session struct {
	// ID is the unique session identifier (UUID v4).
	ID string `json:"id"`
	// PatientID is the internal patient reference identifier.
	PatientID string `json:"patient_id"`
	// PractitionerID is the internal practitioner reference identifier.
	PractitionerID string `json:"practitioner_id"`
	// EncounterID is the clinical encounter identifier.
	EncounterID string `json:"encounter_id"`
	// Status is the session state: "active", "closed", or "error".
	Status string `json:"status"`
	// ChunkCount tracks the number of audio chunks received.
	ChunkCount int `json:"chunk_count"`
	// StartedAt is the time the session was created.
	StartedAt time.Time `json:"started_at"`
	// ClosedAt is the time the session was closed, nil if still active.
	ClosedAt *time.Time `json:"closed_at,omitempty"`
}

// Manager provides Redis-backed session lifecycle management.
type Manager struct {
	client *redis.Client
	ttl    time.Duration
}

// NewManager creates a new session Manager backed by the given Redis client.
// Sessions expire after the specified TTL to prevent stale data accumulation.
func NewManager(redisClient *redis.Client, ttl time.Duration) *Manager {
	return &Manager{
		client: redisClient,
		ttl:    ttl,
	}
}

// CreateSession initializes a new recording session in Redis and returns the
// created Session. The session is assigned a UUID v4 identifier and starts
// with status "active" and zero chunk count.
func (m *Manager) CreateSession(ctx context.Context, patientID, practitionerID, encounterID string) (*Session, error) {
	sess := &Session{
		ID:             uuid.New().String(),
		PatientID:      patientID,
		PractitionerID: practitionerID,
		EncounterID:    encounterID,
		Status:         "active",
		ChunkCount:     0,
		StartedAt:      time.Now().UTC(),
	}

	key := keyPrefix + sess.ID
	fields := map[string]interface{}{
		"id":              sess.ID,
		"patient_id":      sess.PatientID,
		"practitioner_id": sess.PractitionerID,
		"encounter_id":    sess.EncounterID,
		"status":          sess.Status,
		"chunk_count":     "0",
		"started_at":      sess.StartedAt.Format(time.RFC3339Nano),
	}

	pipe := m.client.Pipeline()
	pipe.HSet(ctx, key, fields)
	pipe.Expire(ctx, key, m.ttl)
	if _, err := pipe.Exec(ctx); err != nil {
		return nil, fmt.Errorf("session: failed to create session in redis: %w", err)
	}

	return sess, nil
}

// GetSession retrieves a session by its ID from Redis. Returns ErrSessionNotFound
// if the session does not exist or has expired.
func (m *Manager) GetSession(ctx context.Context, sessionID string) (*Session, error) {
	key := keyPrefix + sessionID
	result, err := m.client.HGetAll(ctx, key).Result()
	if err != nil {
		return nil, fmt.Errorf("session: redis error: %w", err)
	}
	if len(result) == 0 {
		return nil, ErrSessionNotFound
	}

	return parseSession(result)
}

// IncrementChunkCount atomically increments the chunk counter for the given session
// and returns the new count. Returns ErrSessionNotFound if the session does not exist.
func (m *Manager) IncrementChunkCount(ctx context.Context, sessionID string) (int, error) {
	key := keyPrefix + sessionID

	script := `
		if redis.call("EXISTS", KEYS[1]) == 1 then
			local count = redis.call("HINCRBY", KEYS[1], "chunk_count", 1)
			redis.call("EXPIRE", KEYS[1], ARGV[1])
			return count
		else
			return -1
		end
	`

	val, err := m.client.Eval(ctx, script, []string{key}, int(m.ttl.Seconds())).Result()
	if err != nil {
		return 0, fmt.Errorf("session: redis error: %w", err)
	}

	newCount, ok := val.(int64)
	if !ok {
		return 0, fmt.Errorf("session: unexpected return type from lua script")
	}

	if newCount == -1 {
		return 0, ErrSessionNotFound
	}

	return int(newCount), nil
}

// CloseSession marks a session as "closed" and records the closure timestamp.
// Returns the updated Session. Returns ErrSessionNotFound if the session does
// not exist, and ErrSessionClosed if already closed.
func (m *Manager) CloseSession(ctx context.Context, sessionID string) (*Session, error) {
	key := keyPrefix + sessionID

	sess, err := m.GetSession(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	if sess.Status == "closed" {
		return nil, ErrSessionClosed
	}

	now := time.Now().UTC()
	pipe := m.client.Pipeline()
	pipe.HSet(ctx, key, map[string]interface{}{
		"status":    "closed",
		"closed_at": now.Format(time.RFC3339Nano),
	})
	// Keep closed sessions for a shorter retention period for reference.
	pipe.Expire(ctx, key, m.ttl)
	if _, err := pipe.Exec(ctx); err != nil {
		return nil, fmt.Errorf("session: failed to close session in redis: %w", err)
	}

	sess.Status = "closed"
	sess.ClosedAt = &now
	return sess, nil
}

// ToJSON serializes the session to JSON bytes. This is used for API responses.
func (s *Session) ToJSON() ([]byte, error) {
	data, err := json.Marshal(s)
	if err != nil {
		return nil, fmt.Errorf("session: failed to marshal session: %w", err)
	}
	return data, nil
}

// parseSession converts a Redis hash map to a Session struct.
func parseSession(fields map[string]string) (*Session, error) {
	sess := &Session{
		ID:             fields["id"],
		PatientID:      fields["patient_id"],
		PractitionerID: fields["practitioner_id"],
		EncounterID:    fields["encounter_id"],
		Status:         fields["status"],
	}

	if cc, ok := fields["chunk_count"]; ok {
		count, err := strconv.Atoi(cc)
		if err != nil {
			return nil, fmt.Errorf("session: invalid chunk_count: %w", err)
		}
		sess.ChunkCount = count
	}

	if sa, ok := fields["started_at"]; ok && sa != "" {
		t, err := time.Parse(time.RFC3339Nano, sa)
		if err != nil {
			return nil, fmt.Errorf("session: invalid started_at: %w", err)
		}
		sess.StartedAt = t
	}

	if ca, ok := fields["closed_at"]; ok && ca != "" {
		t, err := time.Parse(time.RFC3339Nano, ca)
		if err != nil {
			return nil, fmt.Errorf("session: invalid closed_at: %w", err)
		}
		sess.ClosedAt = &t
	}

	return sess, nil
}
