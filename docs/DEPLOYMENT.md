# Deployment

Production deployment uses `docker-compose.prod.yml` behind Nginx.

Before live trading:

- Verify Binance API key has trading permission only.
- Verify withdrawal permission is disabled.
- Verify IP whitelist is enabled.
- Run database migrations.
- Confirm health checks and Prometheus metrics.
- Run backup and restore drills.

