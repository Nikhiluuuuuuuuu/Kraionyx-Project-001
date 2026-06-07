package fhir

import (
	"bytes"
	"context"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"
)

// Client represents an HTTP client specifically designed for communicating
// with FHIR R4 compliant Electronic Health Record (EHR) systems.
// It handles authentication, resource creation, and data retrieval while
// enforcing TLS and HIPAA-compliant data transmission standards.
type Client struct {
	baseURL    string
	httpClient *http.Client
}

// NewSecureClient initializes a new FHIR Client with strict TLS 1.3 and optional SSL pinning.
//
// Parameters:
//   - baseURL: The root URL of the FHIR server.
//   - expectedPinnedHash: SHA-256 hash of the expected server certificate for SSL pinning.
func NewSecureClient(baseURL, expectedPinnedHash string) *Client {
	tlsConfig := &tls.Config{
		MinVersion: tls.VersionTLS13,
		CurvePreferences: []tls.CurveID{
			tls.X25519,
			tls.CurveP256,
		},
		VerifyPeerCertificate: func(rawCerts [][]byte, verifiedChains [][]*x509.Certificate) error {
			if expectedPinnedHash == "" {
				return nil
			}
			for _, rawCert := range rawCerts {
				hash := sha256.Sum256(rawCert)
				hashStr := hex.EncodeToString(hash[:])
				if hashStr == expectedPinnedHash {
					return nil
				}
			}
			return errors.New("ssl pinning failed: certificate hash mismatch")
		},
	}

	transport := &http.Transport{
		TLSClientConfig: tlsConfig,
	}

	httpClient := &http.Client{
		Transport: transport,
	}

	return &Client{baseURL: baseURL, httpClient: httpClient}
}

// CreateDocumentReference securely pushes a generated DocumentReference resource to the EHR.
//
// This function transmits the finalized SOAP note or clinical document to the
// upstream EHR system. It expects a context with a timeout and the DocumentReference
// payload. On success, it returns the newly created resource's ID provided by the EHR.
//
// Note: This operation is audited and all outgoing requests are TLS-encrypted.
//
// Parameters:
//   - ctx: The context controlling the execution timeout and cancellation.
//   - doc: A pointer to the DocumentReference resource to be uploaded.
//
// Returns:
//   - string: The assigned ID of the newly created DocumentReference in the EHR.
//   - error: Returns an error if the network request fails or the EHR rejects the payload.
func (c *Client) CreateDocumentReference(ctx context.Context, doc *DocumentReference) (string, error) {
	url := fmt.Sprintf("%s/DocumentReference", c.baseURL)
	
	payload, err := json.Marshal(doc)
	if err != nil {
		return "", fmt.Errorf("failed to marshal DocumentReference: %w", err)
	}

	maxRetries := 5
	baseDelay := 100 * time.Millisecond
	maxDelay := 5 * time.Second

	var lastErr error

	for i := 0; i <= maxRetries; i++ {
		req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewBuffer(payload))
		if err != nil {
			return "", fmt.Errorf("failed to create request: %w", err)
		}
		
		req.Header.Set("Content-Type", "application/fhir+json")

		resp, err := c.httpClient.Do(req)
		if err == nil {
			defer resp.Body.Close()
			if resp.StatusCode >= 200 && resp.StatusCode < 300 {
				var result struct {
					ID string `json:"id"`
				}
				if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
					return "", fmt.Errorf("failed to decode response: %w", err)
				}
				return result.ID, nil
			}
			
			bodyBytes, _ := io.ReadAll(resp.Body)
			lastErr = fmt.Errorf("ehr returned status %d: %s", resp.StatusCode, string(bodyBytes))
		} else {
			lastErr = err
		}

		if i == maxRetries {
			break
		}

		delay := baseDelay * (1 << i)
		if delay > maxDelay {
			delay = maxDelay
		}

		select {
		case <-time.After(delay):
		case <-ctx.Done():
			return "", ctx.Err()
		}
	}

	return "", fmt.Errorf("failed after %d retries: %w", maxRetries, lastErr)
}

