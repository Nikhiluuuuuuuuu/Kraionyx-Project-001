package auth

import (
	"context"
	"fmt"
	"strings"

	"github.com/coreos/go-oidc/v3/oidc"
)

type OIDCValidator struct {
	provider *oidc.Provider
	verifier *oidc.IDTokenVerifier
}

func NewOIDCValidator(ctx context.Context, issuerURL, clientID string) (*OIDCValidator, error) {
	provider, err := oidc.NewProvider(ctx, issuerURL)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize oidc provider: %w", err)
	}

	oidcConfig := &oidc.Config{
		ClientID: clientID,
	}
	verifier := provider.Verifier(oidcConfig)

	return &OIDCValidator{
		provider: provider,
		verifier: verifier,
	}, nil
}

func (v *OIDCValidator) ValidateToken(ctx context.Context, tokenString string) (*oidc.IDToken, error) {
	const prefix = "Bearer "
	if strings.HasPrefix(tokenString, prefix) {
		tokenString = strings.TrimPrefix(tokenString, prefix)
	}

	token, err := v.verifier.Verify(ctx, tokenString)
	if err != nil {
		return nil, fmt.Errorf("failed to verify token: %w", err)
	}

	return token, nil
}
