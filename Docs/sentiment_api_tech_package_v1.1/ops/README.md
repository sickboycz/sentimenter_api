# Ops templates

- `runbook.md` — operator guide
- `docker-compose.yml` — single-node dev/prod starter (adjust secrets)
- `sentiment_api.service` — systemd template

v1 is intentionally single-node friendly.
Scale later by:
- increasing worker replicas,
- moving artifacts to S3,
- moving queue to RabbitMQ/NATS,
- moving vectors to Qdrant.
