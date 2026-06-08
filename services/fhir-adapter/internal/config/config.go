package config

import (
	"os"
	"strings"
)

type Config struct {
	KafkaBrokers       []string
	KafkaConsumerGroup string
	KafkaInputTopic    string
	FHIRServerURL      string
	FHIRClientID       string
	FHIRClientSecret   string
	EncryptionKey      string
	Environment        string
	LogLevel           string

	VaultAddress string
	VaultToken   string

	ClientCertFile string
	ClientKeyFile  string
	CACertFile     string
}

func getEnvOrDefault(key, def string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return def
}

func Load() (*Config, error) {
	return &Config{
		KafkaBrokers:       strings.Split(getEnvOrDefault("KAFKA_BROKERS", "localhost:9092"), ","),
		KafkaConsumerGroup: getEnvOrDefault("KAFKA_CONSUMER_GROUP", "fhir-adapter-group"),
		KafkaInputTopic:    getEnvOrDefault("KAFKA_INPUT_TOPIC", "structured.data"),
		FHIRServerURL:      os.Getenv("FHIR_SERVER_URL"),
		FHIRClientID:       os.Getenv("FHIR_CLIENT_ID"),
		FHIRClientSecret:   os.Getenv("FHIR_CLIENT_SECRET"),
		EncryptionKey:      os.Getenv("ENCRYPTION_KEY"),
		Environment:        getEnvOrDefault("ENVIRONMENT", "development"),
		LogLevel:           getEnvOrDefault("LOG_LEVEL", "info"),
		VaultAddress:       getEnvOrDefault("VAULT_ADDR", "http://localhost:8200"),
		VaultToken:         os.Getenv("VAULT_TOKEN"),
		ClientCertFile:     getEnvOrDefault("CLIENT_CERT_FILE", "certs/client.crt"),
		ClientKeyFile:      getEnvOrDefault("CLIENT_KEY_FILE", "certs/client.key"),
		CACertFile:         getEnvOrDefault("CA_CERT_FILE", "certs/ca.crt"),
	}, nil
}
