package oauth

import (
	"context"
	"net/http"

	"golang.org/x/oauth2/clientcredentials"
)

type SMARTClient struct {
	config *clientcredentials.Config
}

func NewSMARTClient(tokenURL, clientID, clientSecret string) (*SMARTClient, error) {
	config := &clientcredentials.Config{
		ClientID:     clientID,
		ClientSecret: clientSecret,
		TokenURL:     tokenURL,
		Scopes:       []string{"system/DocumentReference.write", "system/Patient.read"},
	}
	return &SMARTClient{config: config}, nil
}

// GetHTTPClient returns an http.Client that automatically adds the OAuth2 Bearer token
// and refreshes it as needed.
func (s *SMARTClient) GetHTTPClient(ctx context.Context) (*http.Client, error) {
	return s.config.Client(ctx), nil
}
