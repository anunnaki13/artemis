# Deployment

Production deployment uses `docker-compose.prod.yml` behind Nginx.

Before live trading:

- Verify Bybit API key has trading permission only, withdrawal disabled, and UTA enabled.
- Set `BYBIT_WITHDRAWAL_ENABLED=false` in the Settings Vault.
- Verify withdrawal permission is disabled.
- Verify IP whitelist is enabled.
- Set `BYBIT_WHITELISTED_IP` to the VPS public IP before enabling private stream or live transport.
- Run database migrations.
- Confirm health checks and Prometheus metrics.
- Run backup and restore drills.
