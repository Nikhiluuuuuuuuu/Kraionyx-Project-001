// Package config provides environment-based configuration loading for the
// API Gateway service. All configuration values are read from environment
// variables with sensible defaults for local development.
package config

import (
	"errors"
	"os"
	"strings"
)

// Config holds all configuration values for the API Gateway service.
type Config struct {
	// Port is the HTTPS listen port (default: "8443").
	Port string
	// TLSCertFile is the path to the TLS certificate file.
	TLSCertFile string
	// TLSKeyFile is the path to the TLS private key file.
	TLSKeyFile string
	// RedisURL is the Redis connection URL (default: "localhost:6379").
	RedisURL string
	// RedisPassword is the Redis authentication password.
	RedisPassword string
	// KafkaBrokers is a comma-separated list of Kafka broker addresses.
	KafkaBrokers []string
	// EncryptionKey is the base64-encoded 32-byte AES-256 encryption key.
	EncryptionKey string
	// JWTSecret is the secret used for JWT token verification.
	JWTSecret string
	// APIKey is the expected API key for X-API-Key authentication.
	APIKey string
	// Environment is the deployment environment ("development", "staging", "production").
	Environment string
	// LogLevel is the slog log level ("debug", "info", "warn", "error").
	LogLevel string
}

// Load reads configuration from environment variables and returns a validated
// Config. It returns an error if required values are missing.
func Load() (*Config, error) {
	cfg := &Config{
		Port:          getEnvOrDefault("PORT", "8443"),
		TLSCertFile:   getEnvOrDefault("TLS_CERT_FILE", "certs/server.crt"),
		TLSKeyFile:    getEnvOrDefault("TLS_KEY_FILE", "certs/server.key"),
		RedisURL:      getEnvOrDefault("REDIS_URL", "localhost:6379"),
		RedisPassword: os.Getenv("REDIS_PASSWORD"),
		KafkaBrokers:  strings.Split(getEnvOrDefault("KAFKA_BROKERS", "localhost:9092"), ","),
		EncryptionKey: os.Getenv("ENCRYPTION_KEY"),
		JWTSecret:     os.Getenv("JWT_SECRET"),
		APIKey:        os.Getenv("API_KEY"),
		Environment:   getEnvOrDefault("ENVIRONMENT", "development"),
		LogLevel:      getEnvOrDefault("LOG_LEVEL", "info"),
	}

	if err := cfg.validate(); err != nil {
		return nil, err
	}

	return cfg, nil
}

// validate checks that all required configuration fields are set.
func (c *Config) validate() error {
	if c.EncryptionKey == "" {
		return errors.New("config: ENCRYPTION_KEY environment variable is required")
	}
	if c.APIKey == "" {
		return errors.New("config: API_KEY environment variable is required")
	}
	if len(c.KafkaBrokers) == 0 || c.KafkaBrokers[0] == "" {
		return errors.New("config: KAFKA_BROKERS environment variable is required")
	}
	return nil
}

// IsDevelopment returns true if the environment is "development".
func (c *Config) IsDevelopment() bool {
	return c.Environment == "development"
}

// getEnvOrDefault returns the environment variable value or the default if unset.
func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
