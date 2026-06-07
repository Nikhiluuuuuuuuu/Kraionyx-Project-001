package main

import (
	"crypto/tls"
	"log/slog"
	"os"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/contrib/websocket"
	"github.com/kraionyx/api-gateway/internal/config"
	"github.com/kraionyx/api-gateway/internal/handler"
	"github.com/kraionyx/api-gateway/internal/kafka"
	"github.com/kraionyx/api-gateway/internal/middleware"
	"github.com/kraionyx/api-gateway/internal/session"
	"github.com/redis/go-redis/v9"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		slog.Error("failed to load config", "error", err)
		os.Exit(1)
	}

	app := fiber.New()
	app.Use(middleware.AuditMiddleware())
	app.Use(middleware.RateLimitMiddleware())

	app.Get("/health", handler.HealthCheck)
	app.Get("/health/ready", handler.ReadyCheck)

	// Auth uses JWT
	// Redis Client
	rdb := redis.NewClient(&redis.Options{
		Addr:     cfg.RedisURL,
		Password: cfg.RedisPassword,
	})
	sessionMgr := session.NewManager(rdb, 24*time.Hour)

	// Kafka Producer
	producer, err := kafka.NewProducer(cfg.KafkaBrokers, slog.Default())
	if err != nil {
		slog.Error("failed to create kafka producer", "error", err)
	}

	wsHandler := handler.NewWebSocketHandler(sessionMgr, producer, []byte(cfg.EncryptionKey), slog.Default())
	
	// Register WebSocket middleware and handler
	app.Use("/ws", wsHandler.Upgrade())
	app.Get("/ws/audio", websocket.New(wsHandler.HandleAudioStream()))

	// Enforce TLS 1.3
	cert, err := tls.LoadX509KeyPair(cfg.TLSCertFile, cfg.TLSKeyFile)
	if err != nil {
		slog.Error("failed to load tls certificates", "error", err)
		os.Exit(1)
	}

	tlsConfig := &tls.Config{
		MinVersion:   tls.VersionTLS13,
		Certificates: []tls.Certificate{cert},
		CurvePreferences: []tls.CurveID{
			tls.X25519,
			tls.CurveP256,
		},
	}

	ln, err := tls.Listen("tcp", ":"+cfg.Port, tlsConfig)
	if err != nil {
		slog.Error("failed to listen on tls", "error", err)
		os.Exit(1)
	}

	if err := app.Listener(ln); err != nil {
		slog.Error("server error", "error", err)
	}
}
