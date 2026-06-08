package fhir_test

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/kraionyx/fhir-adapter/internal/fhir"
)

func TestCreateDocumentReferenceWithBackoff(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Location", "https://example.com/fhir/DocumentReference/doc-123")
		w.WriteHeader(http.StatusCreated)
		w.Write([]byte(`{"id":"doc-123"}`))
	}))
	defer ts.Close()

	client := fhir.NewSecureClient(ts.URL, "")

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
