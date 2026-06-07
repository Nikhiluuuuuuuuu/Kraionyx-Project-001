package middleware

import (
	"github.com/gofiber/fiber/v2"
	"log/slog"
	"time"
)

func AuditMiddleware() fiber.Handler {
	return func(c *fiber.Ctx) error {
		start := time.Now()
		err := c.Next()
		slog.Info("Audit Log",
			"method", c.Method(),
			"path", c.Path(),
			"ip", c.IP(),
			"status", c.Response().StatusCode(),
			"duration", time.Since(start),
		)
		return err
	}
}
