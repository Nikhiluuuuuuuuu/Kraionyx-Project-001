package middleware

import (
	"context"
	"strings"

	"github.com/gofiber/fiber/v2"
	sharedAuth "github.com/svaani/shared/pkg/auth"
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

		var claims map[string]interface{}
		if err := token.Claims(&claims); err == nil {
			var tenantID string
			if tid, ok := claims["tenant_id"].(string); ok {
				tenantID = tid
			} else if tid, ok := claims["tid"].(string); ok { // Azure AD uses 'tid'
				tenantID = tid
			}
			
			if tenantID != "" {
				c.Locals("tenant_id", tenantID)
				ctx := context.WithValue(c.UserContext(), sharedAuth.TenantIDKey, tenantID)
				c.SetUserContext(ctx)
			}
		}

		return c.Next()
	}
}

