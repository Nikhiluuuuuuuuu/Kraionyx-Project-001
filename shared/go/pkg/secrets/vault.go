package secrets

import (
	"context"
	"fmt"

	vault "github.com/hashicorp/vault/api"
)

type VaultClient struct {
	client *vault.Client
}

func NewVaultClient(address, token string) (*VaultClient, error) {
	config := vault.DefaultConfig()
	config.Address = address

	client, err := vault.NewClient(config)
	if err != nil {
		return nil, err
	}

	client.SetToken(token)

	return &VaultClient{client: client}, nil
}

func (v *VaultClient) GetSecret(ctx context.Context, path string) (map[string]interface{}, error) {
	secret, err := v.client.Logical().ReadWithContext(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("failed to read secret at %s: %w", path, err)
	}
	if secret == nil {
		return nil, fmt.Errorf("secret not found at %s", path)
	}
	
	if data, ok := secret.Data["data"].(map[string]interface{}); ok {
		// KV v2
		return data, nil
	}
	
	return secret.Data, nil
}
