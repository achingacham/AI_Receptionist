# TODO — AI Receptionist

This file lists remaining tasks, status, and short notes to help continuing work.

- [x] Verify HTTPS /health is serving (done)
- [x] Fix Caddy reverse proxy upstream for host-network (done)
- [x] Add README notes for HTTPS and DNS (done) — see [README.md](README.md)
- [x] Create `restart_service.sh` and make executable (done) — see [restart_service.sh](restart_service.sh)

- [ ] Troubleshoot hairpin / NAT routing (in-progress)
  - Ensure VM public IP is attached and externally reachable
  - Option: use OCI Load Balancer if direct public IP problematic

- [ ] Move Caddy into Docker Compose network (optional)
  - Benefit: Caddy can proxy to `app:8000` instead of host loopback
  - Files to change: [docker-compose.yml](docker-compose.yml), [Caddyfile](Caddyfile)

- [ ] Fix `docker build` failure for `app` image
  - Problem: private `--extra-index-url` caused pip auth prompt during build
  - Options: provide build-time credentials or remove private index

- [ ] Implement DNS-01 (Cloudflare) option for Caddy
  - Add example `Caddyfile` and document `CLOUDFLARE_API_TOKEN` in `.env` or container env

- [ ] Add monitoring / alerts for certificate renewals and service health

- [ ] Harden Caddy and app for production (security, logging, rate-limits)

Notes:
- Health endpoint: `GET /health` returns a small JSON used by scripts and load balancers.
- Use [README.md](README.md) for deployment quickstarts and more details.
