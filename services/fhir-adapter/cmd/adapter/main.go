package main

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"log/slog"
	"os"

	"github.com/svaani/fhir-adapter/internal/config"
	"github.com/svaani/fhir-adapter/internal/kafka"
	"github.com/svaani/shared/pkg/secrets"
	"github.com/svaani/shared/pkg/telemetry"
)

func main() {
	ctx := context.Background()
	slog.Info("Starting FHIR Adapter")

	cfg, err := config.Load()
	if err != nil {
		slog.Error("failed to load config", "error", err)
		os.Exit(1)
	}

	tp, err := telemetry.InitTracer(ctx, "fhir-adapter", "otel-collector:4317")
	if err != nil {
		slog.Error("failed to init tracer", "error", err)
	} else {
		defer func() { _ = tp.Shutdown(ctx) }()
	}
	
	// Start metrics server for Prometheus
	telemetry.StartMetricsServer(":9090")

	vaultClient, err := secrets.NewVaultClient(cfg.VaultAddress, cfg.VaultToken)
	if err != nil {
		slog.Error("failed to connect to vault", "error", err)
	} else if cfg.EncryptionKey == "" || cfg.FHIRClientSecret == "" {
		secret, err := vaultClient.GetSecret(ctx, "secret/data/fhir-adapter")
		if err == nil && secret != nil {
			if key, ok := secret["ENCRYPTION_KEY"].(string); ok {
				cfg.EncryptionKey = key
			}
			if fhirSec, ok := secret["FHIR_CLIENT_SECRET"].(string); ok {
				cfg.FHIRClientSecret = fhirSec
			}
		} else {
			slog.Warn("could not fetch secrets from vault", "error", err)
		}
	}

	clientCert, err := tls.LoadX509KeyPair(cfg.ClientCertFile, cfg.ClientKeyFile)
	if err != nil {
		slog.Warn("could not load client certificates, mTLS might fail", "error", err)
	}
	caCert, err := os.ReadFile(cfg.CACertFile)
	if err != nil {
		slog.Warn("could not load CA cert", "error", err)
	}
	caCertPool := x509.NewCertPool()
	caCertPool.AppendCertsFromPEM(caCert)

	tlsConfig := &tls.Config{
		Certificates: []tls.Certificate{clientCert},
		RootCAs:      caCertPool,
		MinVersion:   tls.VersionTLS13,
	}

	consumer, err := kafka.NewConsumer(cfg.KafkaBrokers, cfg.KafkaConsumerGroup, "fhir.dlq", tlsConfig)
	if err != nil {
		slog.Error("failed to create consumer", "error", err)
		os.Exit(1)
	}

	slog.Info("Consumer started, waiting for messages...")
	consumer.Consume(ctx, func(c context.Context, msg []byte) error {
		// Mock handler
		slog.Info("Received message", "size", len(msg))
		return nil
	})
}
