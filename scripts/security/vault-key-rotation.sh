#!/bin/bash
# vault-key-rotation.sh
# Automated key rotation script for HashiCorp Vault integration.
# This script handles the rotation of Vault Transit Engine keys or Database credentials.

set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"

if [[ -z "$VAULT_TOKEN" ]]; then
  echo "Error: VAULT_TOKEN environment variable is not set."
  echo "Please set VAULT_TOKEN with an appropriate policy to rotate keys."
  exit 1
fi

export VAULT_ADDR
export VAULT_TOKEN

echo "Starting HashiCorp Vault Key Rotation Process..."

# Ensure jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required to parse Vault responses."
    exit 1
fi

# Rotate Transit Engine Key
# Assumes the transit secrets engine is mounted at 'transit/' and the key is 'kraionyx-app-key'
TRANSIT_KEY="kraionyx-app-key"

echo "Rotating transit key: $TRANSIT_KEY..."
# Use the Vault CLI to rotate the transit key
if vault write -f "transit/keys/$TRANSIT_KEY/rotate"; then
    echo "Successfully issued rotation command for $TRANSIT_KEY."
else
    echo "Failed to rotate transit key: $TRANSIT_KEY. Please check permissions and path."
    exit 1
fi

# Verify key rotation by checking the latest version
KEY_INFO=$(vault read -format=json "transit/keys/$TRANSIT_KEY")
LATEST_VERSION=$(echo "$KEY_INFO" | jq -r '.data.latest_version')
echo "Transit key '$TRANSIT_KEY' latest version is now: $LATEST_VERSION."

# Example: Rotate Database root credentials (if database secrets engine is configured)
# echo "Rotating database credentials..."
# vault write -f database/rotate-root/kraionyx-db

# Example: Update minimal key version to enforce usage of new keys (optional)
# MIN_VERSION=$((LATEST_VERSION - 1))
# if [ "$MIN_VERSION" -gt 0 ]; then
#     echo "Setting minimum decryption version to $MIN_VERSION..."
#     vault write "transit/keys/$TRANSIT_KEY/config" min_decryption_version="$MIN_VERSION"
# fi

echo "Key Rotation Completed Successfully at $(date)."
