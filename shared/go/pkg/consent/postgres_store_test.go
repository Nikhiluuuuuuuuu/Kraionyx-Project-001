package consent

import (
	"context"
	"database/sql"
	"errors"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestPostgresStore_GrantConsent(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	store := NewPostgresStore(db)
	ctx := context.Background()

	now := time.Now().UTC()
	record := &ConsentRecord{
		ID:                 "test-id",
		PatientID:          "patient-1",
		GrantedToApp:       "app-1",
		Type:               ConsentTypeMedicalRecords,
		Status:             ConsentStatusActive,
		GrantedAt:          now,
		PurposeDescription: "test purpose",
		IPAddress:          "127.0.0.1",
		UserAgent:          "test-agent",
	}

	mock.ExpectExec("INSERT INTO consents").
		WithArgs(
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
		).
		WillReturnResult(sqlmock.NewResult(1, 1))

	err = store.GrantConsent(ctx, record)
	assert.NoError(t, err)
	assert.NoError(t, mock.ExpectationsWereMet())
}

func TestPostgresStore_RevokeConsent(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	store := NewPostgresStore(db)
	ctx := context.Background()
	id := "test-id"

	// Success case
	mock.ExpectExec("UPDATE consents").
		WithArgs(ConsentStatusRevoked, sqlmock.AnyArg(), id, ConsentStatusActive).
		WillReturnResult(sqlmock.NewResult(1, 1))

	err = store.RevokeConsent(ctx, id)
	assert.NoError(t, err)
	assert.NoError(t, mock.ExpectationsWereMet())

	// Not found or already revoked
	mock.ExpectExec("UPDATE consents").
		WithArgs(ConsentStatusRevoked, sqlmock.AnyArg(), id, ConsentStatusActive).
		WillReturnResult(sqlmock.NewResult(1, 0))

	err = store.RevokeConsent(ctx, id)
	assert.ErrorContains(t, err, "consent record not found or already revoked")
	assert.NoError(t, mock.ExpectationsWereMet())
}

func TestPostgresStore_GetConsent(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	store := NewPostgresStore(db)
	ctx := context.Background()
	id := "test-id"
	now := time.Now().UTC()

	rows := sqlmock.NewRows([]string{"id", "patient_id", "granted_to_app", "type", "status", "granted_at", "expires_at", "revoked_at", "purpose_description", "ip_address", "user_agent"}).
		AddRow(id, "patient-1", "app-1", string(ConsentTypeMedicalRecords), string(ConsentStatusActive), now, nil, nil, "purpose", "127.0.0.1", "agent")

	mock.ExpectQuery("SELECT id, patient_id").
		WithArgs(id).
		WillReturnRows(rows)

	rec, err := store.GetConsent(ctx, id)
	assert.NoError(t, err)
	assert.NotNil(t, rec)
	assert.Equal(t, id, rec.ID)
	assert.Equal(t, "patient-1", rec.PatientID)
	assert.NoError(t, mock.ExpectationsWereMet())

	// Not found
	mock.ExpectQuery("SELECT id, patient_id").
		WithArgs(id).
		WillReturnError(sql.ErrNoRows)

	rec, err = store.GetConsent(ctx, id)
	assert.ErrorContains(t, err, "consent record not found")
	assert.Nil(t, rec)
	assert.NoError(t, mock.ExpectationsWereMet())
}

func TestPostgresStore_ListActiveConsents(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	store := NewPostgresStore(db)
	ctx := context.Background()
	patientID := "patient-1"
	now := time.Now().UTC()

	rows := sqlmock.NewRows([]string{"id", "patient_id", "granted_to_app", "type", "status", "granted_at", "expires_at", "revoked_at", "purpose_description", "ip_address", "user_agent"}).
		AddRow("id1", patientID, "app-1", string(ConsentTypeMedicalRecords), string(ConsentStatusActive), now, nil, nil, "purpose", "127.0.0.1", "agent").
		AddRow("id2", patientID, "app-2", string(ConsentTypeBilling), string(ConsentStatusActive), now, nil, nil, "purpose2", "127.0.0.2", "agent2")

	mock.ExpectQuery("SELECT id, patient_id").
		WithArgs(patientID, ConsentStatusActive).
		WillReturnRows(rows)

	recs, err := store.ListActiveConsents(ctx, patientID)
	assert.NoError(t, err)
	assert.Len(t, recs, 2)
	assert.Equal(t, "id1", recs[0].ID)
	assert.Equal(t, "id2", recs[1].ID)
	assert.NoError(t, mock.ExpectationsWereMet())

	// Error case
	mock.ExpectQuery("SELECT id, patient_id").
		WithArgs(patientID, ConsentStatusActive).
		WillReturnError(errors.New("db error"))

	recs, err = store.ListActiveConsents(ctx, patientID)
	assert.ErrorContains(t, err, "db error")
	assert.Nil(t, recs)
	assert.NoError(t, mock.ExpectationsWereMet())
}
