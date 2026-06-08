package consent

import (
	"context"
	"errors"
	"sync"
	"time"

	"github.com/google/uuid"
)

// ConsentType defines the nature of the data sharing consent.
type ConsentType string

const (
	ConsentTypeMedicalRecords ConsentType = "MEDICAL_RECORDS"
	ConsentTypeResearch       ConsentType = "RESEARCH"
	ConsentTypeBilling        ConsentType = "BILLING"
)

// ConsentStatus defines the current state of a consent grant.
type ConsentStatus string

const (
	ConsentStatusActive  ConsentStatus = "ACTIVE"
	ConsentStatusRevoked ConsentStatus = "REVOKED"
	ConsentStatusExpired ConsentStatus = "EXPIRED"
)

// ConsentRecord represents a HIPAA/DPDPA compliant patient consent record.
type ConsentRecord struct {
	ID                 string        `json:"id"`
	PatientID          string        `json:"patient_id"`
	GrantedToApp       string        `json:"granted_to_app"`
	Type               ConsentType   `json:"type"`
	Status             ConsentStatus `json:"status"`
	GrantedAt          time.Time     `json:"granted_at"`
	ExpiresAt          *time.Time    `json:"expires_at,omitempty"`
	RevokedAt          *time.Time    `json:"revoked_at,omitempty"`
	PurposeDescription string        `json:"purpose_description"`
	IPAddress          string        `json:"ip_address,omitempty"`
	UserAgent          string        `json:"user_agent,omitempty"`
}

// Store defines the interface for persisting and retrieving consent records.
// In a real application, this would be backed by an audited, encrypted DB.
type Store interface {
	GrantConsent(ctx context.Context, record *ConsentRecord) error
	RevokeConsent(ctx context.Context, id string) error
	GetConsent(ctx context.Context, id string) (*ConsentRecord, error)
	ListActiveConsents(ctx context.Context, patientID string) ([]*ConsentRecord, error)
}

// Service provides operations for managing patient consents.
type Service struct {
	store Store
}

// NewService creates a new consent Service.
func NewService(store Store) *Service {
	return &Service{
		store: store,
	}
}

// Grant creates a new active consent grant for a patient.
func (s *Service) Grant(ctx context.Context, patientID, appID string, cType ConsentType, purpose string, duration time.Duration) (*ConsentRecord, error) {
	if patientID == "" || appID == "" {
		return nil, errors.New("patientID and appID are required")
	}

	record := &ConsentRecord{
		ID:                 uuid.New().String(),
		PatientID:          patientID,
		GrantedToApp:       appID,
		Type:               cType,
		Status:             ConsentStatusActive,
		GrantedAt:          time.Now().UTC(),
		PurposeDescription: purpose,
	}

	if duration > 0 {
		expires := record.GrantedAt.Add(duration)
		record.ExpiresAt = &expires
	}

	if err := s.store.GrantConsent(ctx, record); err != nil {
		return nil, err
	}

	return record, nil
}

// Revoke cancels an existing active consent.
func (s *Service) Revoke(ctx context.Context, consentID string) error {
	return s.store.RevokeConsent(ctx, consentID)
}

// CheckAccess verifies if a patient has granted active consent for a specific app and type.
func (s *Service) CheckAccess(ctx context.Context, patientID, appID string, cType ConsentType) (bool, error) {
	records, err := s.store.ListActiveConsents(ctx, patientID)
	if err != nil {
		return false, err
	}

	now := time.Now().UTC()
	for _, rec := range records {
		if rec.GrantedToApp == appID && rec.Type == cType && rec.Status == ConsentStatusActive {
			if rec.ExpiresAt != nil && now.After(*rec.ExpiresAt) {
				continue // Expired
			}
			return true, nil
		}
	}

	return false, nil
}

// InMemoryStore provides a basic thread-safe implementation of Store for testing.
type InMemoryStore struct {
	mu      sync.RWMutex
	records map[string]*ConsentRecord
}

func NewInMemoryStore() *InMemoryStore {
	return &InMemoryStore{
		records: make(map[string]*ConsentRecord),
	}
}

func (s *InMemoryStore) GrantConsent(ctx context.Context, record *ConsentRecord) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.records[record.ID] = record
	return nil
}

func (s *InMemoryStore) RevokeConsent(ctx context.Context, id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if record, exists := s.records[id]; exists {
		record.Status = ConsentStatusRevoked
		now := time.Now().UTC()
		record.RevokedAt = &now
		return nil
	}
	return errors.New("consent record not found")
}

func (s *InMemoryStore) GetConsent(ctx context.Context, id string) (*ConsentRecord, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if record, exists := s.records[id]; exists {
		return record, nil
	}
	return nil, errors.New("consent record not found")
}

func (s *InMemoryStore) ListActiveConsents(ctx context.Context, patientID string) ([]*ConsentRecord, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	
	var active []*ConsentRecord
	for _, rec := range s.records {
		if rec.PatientID == patientID && rec.Status == ConsentStatusActive {
			active = append(active, rec)
		}
	}
	return active, nil
}
