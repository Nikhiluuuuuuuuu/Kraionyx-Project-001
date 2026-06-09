package middleware

import (
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/limiter"
)

func RateLimitMiddleware(store fiber.Storage) fiber.Handler {
	return limiter.New(limiter.Config{
		Max:        100,             // max 100 requests
		Expiration: 1 * time.Minute, // per minute
		Storage:    store,
		KeyGenerator: func(c *fiber.Ctx) string {
			if tenantID := c.Locals("tenant_id"); tenantID != nil {
				return tenantID.(string)
			}
			if userID := c.Locals("user_id"); userID != nil {
				return userID.(string)
			}
			return c.IP()
		},
		LimitReached: func(c *fiber.Ctx) error {
			return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
				"error": "too many requests, quota exceeded",
			})
		},
	})
}
