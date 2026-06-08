package main

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"log/slog"
	"os"
	"time"

	"github.com/ansrivas/fiberprometheus/v2"
	"github.com/gofiber/contrib/otelfiber/v2"
	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"github.com/kraionyx/api-gateway/internal/config"
	"github.com/kraionyx/api-gateway/internal/handler"
	"github.com/kraionyx/api-gateway/internal/kafka"
	"github.com/kraionyx/api-gateway/internal/middleware"
	"github.com/kraionyx/api-gateway/internal/session"
	"github.com/kraionyx/shared/pkg/audit"
	"github.com/kraionyx/shared/pkg/auth"
	"github.com/kraionyx/shared/pkg/secrets"
	"github.com/redis/go-redis/v9"
	"database/sql"
	_ "github.com/lib/pq"
)

func main() {
	ctx := context.Background()
	cfg, err := config.Load()
	if err != nil {
		slog.Error("failed to load config", "error", err)
		os.Exit(1)
	}

	vaultClient, err := secrets.NewVaultClient(cfg.VaultAddress, cfg.VaultToken)
	if err != nil {
		slog.Error("failed to connect to vault", "error", err)
	} else if cfg.EncryptionKey == "" {
		// Fetch encryption key from Vault if not provided
		secret, err := vaultClient.GetSecret(ctx, "secret/data/api-gateway")
		if err == nil && secret != nil {
			if key, ok := secret["ENCRYPTION_KEY"].(string); ok {
				cfg.EncryptionKey = key
			}
			if pwd, ok := secret["REDIS_PASSWORD"].(string); ok {
				cfg.RedisPassword = pwd
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

	producer, err := kafka.NewProducer(cfg.KafkaBrokers, tlsConfig, slog.Default())
	if err != nil {
		slog.Error("failed to create kafka producer", "error", err)
	}

	var auditLogger *audit.Logger
	if producer != nil {
		auditLogger = audit.NewLogger(producer.Client(), slog.Default(), "api-gateway")
	} else {
		auditLogger = audit.NewLogger(nil, slog.Default(), "api-gateway")
	}

	app := fiber.New()
	
	prom := fiberprometheus.New("api_gateway")
	prom.RegisterAt(app, "/metrics")
	app.Use(prom.Middleware)

	app.Use(otelfiber.Middleware())
	app.Use(middleware.AuditMiddleware(auditLogger))
	app.Use(middleware.RateLimitMiddleware())

	app.Get("/health", handler.HealthCheck)
	app.Get("/health/ready", handler.ReadyCheck)

	oidcValidator, err := auth.NewOIDCValidator(ctx, cfg.KeycloakIssuer, cfg.KeycloakClientID)
	if err != nil {
		slog.Error("failed to init oidc validator", "error", err)
		os.Exit(1)
	}

	// Protect WS routes
	app.Use("/ws", middleware.AuthMiddleware(oidcValidator))

	rdb := redis.NewClient(&redis.Options{
		Addr:      cfg.RedisURL,
		Password:  cfg.RedisPassword,
		TLSConfig: tlsConfig,
	})
	sessionMgr := session.NewManager(rdb, 24*time.Hour)

	db, err := sql.Open("postgres", cfg.PostgresURL)
	if err != nil {
		slog.Error("failed to connect to postgres", "error", err)
	} else if err = db.Ping(); err != nil {
		slog.Error("failed to ping postgres", "error", err)
	} else {
		_, _ = db.Exec(`CREATE TABLE IF NOT EXISTS patient_consents (
			patient_id VARCHAR(255) PRIMARY KEY,
			data_processing BOOLEAN NOT NULL DEFAULT false,
			ai_training BOOLEAN NOT NULL DEFAULT false,
			updated_at TIMESTAMP NOT NULL
		)`)
	}

	consentHandler := handler.NewConsentHandler(db, auditLogger, slog.Default())
	consentHandler.SetupRoutes(app)

	wsHandler := handler.NewWebSocketHandler(sessionMgr, producer, []byte(cfg.EncryptionKey), slog.Default())

	app.Use("/ws", wsHandler.Upgrade())
	app.Get("/ws/audio", websocket.New(wsHandler.HandleAudioStream()))

	cert, err := tls.LoadX509KeyPair(cfg.TLSCertFile, cfg.TLSKeyFile)
	if err != nil {
		slog.Error("failed to load tls certificates", "error", err)
		os.Exit(1)
	}

	serverTLSConfig := &tls.Config{
		MinVersion:   tls.VersionTLS13,
		Certificates: []tls.Certificate{cert},
		CurvePreferences: []tls.CurveID{
			tls.X25519,
			tls.CurveP256,
		},
	}

	ln, err := tls.Listen("tcp", ":"+cfg.Port, serverTLSConfig)
	if err != nil {
		slog.Error("failed to listen on tls", "error", err)
		os.Exit(1)
	}

	if err := app.Listener(ln); err != nil {
		slog.Error("server error", "error", err)
	}
}

