#!/usr/bin/env bash
# =============================================================================
# Svaani - Kafka Topic Creation Script
# =============================================================================
# Idempotent: safe to run multiple times. Existing topics are skipped.
#
# Usage:
#   ./scripts/create-kafka-topics.sh
#   KAFKA_BOOTSTRAP=kafka-broker:9092 ./scripts/create-kafka-topics.sh
# =============================================================================

set -euo pipefail

KAFKA_BOOTSTRAP="${KAFKA_BOOTSTRAP:-localhost:9094}"
KAFKA_BIN="${KAFKA_BIN:-kafka-topics.sh}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# -----------------------------------------------------------------------------
# Wait for Kafka to be ready
# -----------------------------------------------------------------------------
wait_for_kafka() {
    local max_attempts=30
    local attempt=0
    log_info "Waiting for Kafka at ${KAFKA_BOOTSTRAP}..."

    while ! "${KAFKA_BIN}" --bootstrap-server "${KAFKA_BOOTSTRAP}" --list > /dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ "${attempt}" -ge "${max_attempts}" ]; then
            log_error "Kafka not available after ${max_attempts} attempts. Exiting."
            exit 1
        fi
        log_warn "Kafka not ready (attempt ${attempt}/${max_attempts}). Retrying in 2s..."
        sleep 2
    done

    log_info "Kafka is ready."
}

# -----------------------------------------------------------------------------
# Create a topic (idempotent — skips if topic already exists)
# -----------------------------------------------------------------------------
create_topic() {
    local topic_name="$1"
    local partitions="$2"
    local replication_factor="${3:-1}"

    # Check if topic already exists
    if "${KAFKA_BIN}" --bootstrap-server "${KAFKA_BOOTSTRAP}" --list 2>/dev/null | grep -qw "${topic_name}"; then
        log_warn "Topic '${topic_name}' already exists — skipping."
        return 0
    fi

    log_info "Creating topic '${topic_name}' (partitions=${partitions}, replication-factor=${replication_factor})..."
    "${KAFKA_BIN}" --bootstrap-server "${KAFKA_BOOTSTRAP}" \
        --create \
        --topic "${topic_name}" \
        --partitions "${partitions}" \
        --replication-factor "${replication_factor}" \
        --if-not-exists

    log_info "Topic '${topic_name}' created successfully."
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo ""
    echo "============================================"
    echo "  Svaani — Kafka Topic Provisioning"
    echo "============================================"
    echo ""

    wait_for_kafka

    # ---- Audio Pipeline Topics (high-throughput) ----
    create_topic "audio.raw.chunks"        3 1
    create_topic "audio.preprocessed"      3 1

    # ---- Transcription Topics ----
    create_topic "transcription.results"   3 1

    # ---- Clinical / FHIR Topics (lower-throughput, ordering matters) ----
    create_topic "clinical.notes.created"  1 1
    create_topic "fhir.outbound"           1 1

    # ---- Observability Topics ----
    create_topic "audit.events"            1 1
    create_topic "pipeline.errors"         1 1

    echo ""
    log_info "All topics created. Current topic list:"
    "${KAFKA_BIN}" --bootstrap-server "${KAFKA_BOOTSTRAP}" --list
    echo ""
}

main "$@"
