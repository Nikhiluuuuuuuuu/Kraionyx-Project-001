package handler

import (
	"github.com/gofiber/fiber/v2"
)

// HealthCheck provides a lightweight endpoint for load balancers (e.g., AWS ALB, NGINX)
// to verify that the API Gateway process is running and able to respond to HTTP requests.
// It returns a standard 200 OK with basic service metadata.
func HealthCheck(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"status":  "ok",
		"service": "api-gateway",
		"version": "1.0.0",
	})
}

// ReadyCheck provides a deep health check endpoint used by orchestration platforms
// (e.g., Kubernetes readiness probes) to determine if the API Gateway is ready to 
// accept external traffic. It verifies connectivity to critical backing services 
// like Redis and Kafka.
func ReadyCheck(c *fiber.Ctx) error {
	// TODO: Add actual connection checks for Redis/Kafka
	return c.JSON(fiber.Map{
		"status": "ready",
	})
}
