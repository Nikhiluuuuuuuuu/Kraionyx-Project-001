package fhir_test

import (
	"context"
	"testing"
	"time"

	"github.com/kraionyx/fhir-adapter/internal/fhir"
)

func TestCreateDocumentReferenceWithBackoff(t *testing.T) {
	client := fhir.NewSecureClient("https://mock-ehr.example.com/fhir", "")

	// Synthetic data for test
	doc := &fhir.DocumentReference{
		ResourceType: "DocumentReference",
		Status:       "current",
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	id, err := client.CreateDocumentReference(ctx, doc)
	if err != nil {
		t.Fatalf("expected success, got error: %v", err)
	}

	if id != "doc-123" {
		t.Errorf("expected doc-123, got %s", id)
	}
}
