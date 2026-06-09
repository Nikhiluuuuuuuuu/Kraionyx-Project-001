# Disaster Recovery & Business Continuity Plan

## Objectives
- **Recovery Time Objective (RTO)**: 4 hours for full system restoration.
- **Recovery Point Objective (RPO)**: 15 minutes for PostgreSQL (consent/audit data), 1 hour for ChromaDB vector embeddings.

## Data Backup Policies
1. **PostgreSQL**: Continuous archiving (WAL streaming) via pgBackRest to S3-compatible cold storage.
2. **ChromaDB**: Nightly volume snapshots of the Persistent Volume Claims (PVCs) retaining 30 days of history.
3. **Kafka**: Topics with `cleanup.policy=compact` (like consent events) are backed up hourly.

## HashiCorp Vault Runbook
### Unsealing Vault
If the Vault cluster restarts or is sealed during a security event:
1. Retrieve the 3 Shamir unseal keys from the secure offline vault (e.g., 1Password/Physical Safe).
2. Execute the unseal command on each pod:
   ```bash
   kubectl exec -it vault-0 -- vault operator unseal <KEY_1>
   kubectl exec -it vault-0 -- vault operator unseal <KEY_2>
   kubectl exec -it vault-0 -- vault operator unseal <KEY_3>
   ```

### Emergency Sealing
In the event of a suspected cluster compromise:
```bash
kubectl exec -it vault-0 -- vault operator seal
```

## Failover Strategy
- The cluster spans 3 Availability Zones (AZs).
- If an entire region fails, traffic is routed via Route53 to a warm-standby cluster in a secondary region.
