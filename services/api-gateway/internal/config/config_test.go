package config

import (
	"os"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	os.Setenv("ENCRYPTION_KEY", "test-key")
	os.Setenv("API_KEY", "test-api")
	os.Setenv("KAFKA_BROKERS", "localhost:9092")

	defer func() {
		os.Unsetenv("ENCRYPTION_KEY")
		os.Unsetenv("API_KEY")
		os.Unsetenv("KAFKA_BROKERS")
	}()

	cfg, err := Load()
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if cfg.EncryptionKey != "test-key" {
		t.Errorf("expected test-key, got %s", cfg.EncryptionKey)
	}
}
