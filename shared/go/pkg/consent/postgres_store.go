package consent

import (
	"context"
	"database/sql"
	"errors"
	"time"
)

// PostgresStore provides a durable, HIPAA-compliant implementation of Store.
type PostgresStore struct {
	db *sql.DB
}

// NewPostgresStore creates a new Postgres-backed consent store.
func NewPostgresStore(db *sql.DB) *PostgresStore {
	return &PostgresStore{
		db: db,
	}
}

// GrantConsent inserts a new consent record.
func (s *PostgresStore) GrantConsent(ctx context.Context, record *ConsentRecord) error {
	query := `
		INSERT INTO consents (id, patient_id, granted_to_app, type, status, granted_at, expires_at, revoked_at, purpose_description, ip_address, user_agent)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
	`
	_, err := s.db.ExecContext(ctx, query,
		record.ID,
		record.PatientID,
		record.GrantedToApp,
		record.Type,
		record.Status,
		record.GrantedAt,
		record.ExpiresAt,
		record.RevokedAt,
		record.PurposeDescription,
		record.IPAddress,
		record.UserAgent,
	)
	return err
}

// RevokeConsent revokes an active consent record.
func (s *PostgresStore) RevokeConsent(ctx context.Context, id string) error {
	query := `
		UPDATE consents
		SET status = $1, revoked_at = $2
		WHERE id = $3 AND status = $4
	`
	now := time.Now().UTC()
	res, err := s.db.ExecContext(ctx, query, ConsentStatusRevoked, now, id, ConsentStatusActive)
	if err != nil {
		return err
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if rows == 0 {
		return errors.New("consent record not found or already revoked")
	}
	return nil
}

// GetConsent retrieves a consent record by ID.
func (s *PostgresStore) GetConsent(ctx context.Context, id string) (*ConsentRecord, error) {
	query := `
		SELECT id, patient_id, granted_to_app, type, status, granted_at, expires_at, revoked_at, purpose_description, ip_address, user_agent
		FROM consents
		WHERE id = $1
	`
	row := s.db.QueryRowContext(ctx, query, id)
	var rec ConsentRecord
	var expiresAt, revokedAt sql.NullTime
	var ipAddress, userAgent sql.NullString

	err := row.Scan(
		&rec.ID,
		&rec.PatientID,
		&rec.GrantedToApp,
		&rec.Type,
		&rec.Status,
		&rec.GrantedAt,
		&expiresAt,
		&revokedAt,
		&rec.PurposeDescription,
		&ipAddress,
		&userAgent,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, errors.New("consent record not found")
		}
		return nil, err
	}
	
	if expiresAt.Valid {
		rec.ExpiresAt = &expiresAt.Time
	}
	if revokedAt.Valid {
		rec.RevokedAt = &revokedAt.Time
	}
	rec.IPAddress = ipAddress.String
	rec.UserAgent = userAgent.String

	return &rec, nil
}

// ListActiveConsents retrieves all active consents for a patient.
func (s *PostgresStore) ListActiveConsents(ctx context.Context, patientID string) ([]*ConsentRecord, error) {
	query := `
		SELECT id, patient_id, granted_to_app, type, status, granted_at, expires_at, revoked_at, purpose_description, ip_address, user_agent
		FROM consents
		WHERE patient_id = $1 AND status = $2
	`
	rows, err := s.db.QueryContext(ctx, query, patientID, ConsentStatusActive)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var active []*ConsentRecord
	for rows.Next() {
		var rec ConsentRecord
		var expiresAt, revokedAt sql.NullTime
		var ipAddress, userAgent sql.NullString

		err := rows.Scan(
			&rec.ID,
			&rec.PatientID,
			&rec.GrantedToApp,
			&rec.Type,
			&rec.Status,
			&rec.GrantedAt,
			&expiresAt,
			&revokedAt,
			&rec.PurposeDescription,
			&ipAddress,
			&userAgent,
		)
		if err != nil {
			return nil, err
		}
		
		if expiresAt.Valid {
			rec.ExpiresAt = &expiresAt.Time
		}
		if revokedAt.Valid {
			rec.RevokedAt = &revokedAt.Time
		}
		rec.IPAddress = ipAddress.String
		rec.UserAgent = userAgent.String

		active = append(active, &rec)
	}
	if err = rows.Err(); err != nil {
		return nil, err
	}
	return active, nil
}
