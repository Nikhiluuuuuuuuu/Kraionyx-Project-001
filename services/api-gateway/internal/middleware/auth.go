package middleware

import (
	"strings"

	"github.com/gofiber/fiber/v2"
	sharedAuth "github.com/kraionyx/shared/pkg/auth"
)

func AuthMiddleware(validator *sharedAuth.OIDCValidator) fiber.Handler {
	return func(c *fiber.Ctx) error {
		authHeader := c.Get("Authorization")
		if authHeader == "" {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "unauthorized"})
		}

		parts := strings.Split(authHeader, " ")
		if len(parts) != 2 || parts[0] != "Bearer" {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "invalid token format"})
		}

		tokenString := parts[1]
		
		token, err := validator.ValidateToken(c.Context(), tokenString)
		if err != nil {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "unauthorized"})
		}

		c.Locals("user_id", token.Subject)

		return c.Next()
	}
}
