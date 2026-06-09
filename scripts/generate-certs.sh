#!/usr/bin/env bash
# =============================================================================
# Svaani - TLS Development Certificate Generator
# =============================================================================
# Generates self-signed TLS certificates for local development using mkcert.
# Idempotent: re-running overwrites existing certs (safe for dev).
#
# Prerequisites:
#   - mkcert: https://github.com/FiloSottile/mkcert
#     Install via: brew install mkcert  (macOS)
#                  choco install mkcert (Windows)
#                  apt install mkcert   (Linux)
#
# Usage:
#   ./scripts/generate-certs.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CERTS_DIR="${PROJECT_ROOT}/certs"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# -----------------------------------------------------------------------------
# Preflight checks
# -----------------------------------------------------------------------------
check_prerequisites() {
    if ! command -v mkcert &> /dev/null; then
        log_error "mkcert is not installed."
        echo ""
        echo "Install mkcert:"
        echo "  macOS:   brew install mkcert"
        echo "  Windows: choco install mkcert"
        echo "  Linux:   https://github.com/FiloSottile/mkcert#installation"
        echo ""
        exit 1
    fi
    log_info "mkcert found: $(mkcert --version 2>&1 || true)"
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo ""
    echo "============================================"
    echo "  Svaani — TLS Certificate Generator"
    echo "============================================"
    echo ""

    check_prerequisites

    # Install the local CA into the system trust store (idempotent)
    log_info "Installing local CA (requires sudo on first run)..."
    mkcert -install

    # Create certs directory
    mkdir -p "${CERTS_DIR}"

    # Generate certificates for all service hostnames
    log_info "Generating TLS certificates..."
    mkcert \
        -cert-file "${CERTS_DIR}/cert.pem" \
        -key-file "${CERTS_DIR}/key.pem" \
        localhost \
        127.0.0.1 \
        ::1 \
        kafka-broker \
        redis \
        api-gateway

    # Ensure .gitkeep is preserved
    touch "${CERTS_DIR}/.gitkeep"

    # Set restrictive permissions on the key file
    chmod 600 "${CERTS_DIR}/key.pem" 2>/dev/null || true
    chmod 644 "${CERTS_DIR}/cert.pem" 2>/dev/null || true

    echo ""
    log_info "Certificates generated successfully:"
    echo "  Certificate: ${CERTS_DIR}/cert.pem"
    echo "  Private Key: ${CERTS_DIR}/key.pem"
    echo ""
    log_warn "These certificates are for DEVELOPMENT ONLY."
    log_warn "Never use mkcert certificates in production."
    echo ""
}

main "$@"
