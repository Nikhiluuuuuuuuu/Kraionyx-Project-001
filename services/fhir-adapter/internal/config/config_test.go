package config

import (
	"os"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	os.Setenv("FHIR_SERVER_URL", "http://fhir.example.com")
	os.Setenv("FHIR_CLIENT_ID", "client-id")
	os.Setenv("KAFKA_BROKERS", "localhost:9092,localhost:9093")

	defer func() {
		os.Unsetenv("FHIR_SERVER_URL")
		os.Unsetenv("FHIR_CLIENT_ID")
		os.Unsetenv("KAFKA_BROKERS")
	}()

	cfg, err := Load()
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if cfg.FHIRServerURL != "http://fhir.example.com" {
		t.Errorf("expected http://fhir.example.com, got %s", cfg.FHIRServerURL)
	}
	if len(cfg.KafkaBrokers) != 2 {
		t.Errorf("expected 2 brokers, got %d", len(cfg.KafkaBrokers))
	}
}
