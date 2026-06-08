package middleware

import (
	"fmt"
	"github.com/gofiber/fiber/v2"
	"github.com/kraionyx/shared/pkg/audit"
)

func AuditMiddleware(logger *audit.Logger) fiber.Handler {
	return func(c *fiber.Ctx) error {
		err := c.Next()

		userID := "anonymous"
		if uid, ok := c.Locals("user_id").(string); ok && uid != "" {
			userID = uid
		}

		detail := fmt.Sprintf("method=%s path=%s status=%d", c.Method(), c.Path(), c.Response().StatusCode())

		switch c.Method() {
		case fiber.MethodGet, fiber.MethodHead, fiber.MethodOptions:
			logger.LogAccess(c.Context(), userID, "HTTP_ENDPOINT", c.Path(), detail, c.IP())
		case fiber.MethodPost, fiber.MethodPut, fiber.MethodPatch:
			logger.LogModification(c.Context(), userID, audit.ActionUpdate, "HTTP_ENDPOINT", c.Path(), detail, c.IP())
		case fiber.MethodDelete:
			logger.LogDeletion(c.Context(), userID, "HTTP_ENDPOINT", c.Path(), detail, c.IP())
		default:
			logger.LogAccess(c.Context(), userID, "HTTP_ENDPOINT", c.Path(), detail, c.IP())
		}

		return err
	}
}
