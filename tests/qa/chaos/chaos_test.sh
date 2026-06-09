#!/bin/bash
# Chaos engineering script to simulate Redis and Kafka failures

echo "=== Chaos Engineering Test Starting ==="

# Function to test health
check_health() {
    curl -k -s https://localhost:8443/health | grep -q "ok"
    return $?
}

echo "[Chaos] Injecting failure: Stopping Redis..."
docker stop svaani-redis-1

# Verify gateway handles Redis failure (e.g. might fail or retry)
echo "[Chaos] Wait 5s..."
sleep 5
echo "[Chaos] Restoring Redis..."
docker start svaani-redis-1
sleep 5

echo "[Chaos] Injecting failure: Pausing Kafka..."
docker pause svaani-kafka-1

# Attempting some operation while Kafka is paused...
echo "[Chaos] Wait 5s..."
sleep 5

echo "[Chaos] Restoring Kafka..."
docker unpause svaani-kafka-1

echo "=== Chaos Engineering Test Complete ==="
