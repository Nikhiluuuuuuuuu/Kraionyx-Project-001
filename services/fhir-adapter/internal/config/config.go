package config

import "os"

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
}

func Load() (*Config, error) {
	return &Config{
		FHIRServerURL: os.Getenv("FHIR_SERVER_URL"),
	}, nil
}
