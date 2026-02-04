# Reverse Proxy Examples (Optional)

These configs are optional. Wingman runs fine without a reverse proxy, but a proxy
is recommended for TLS termination and stable hostnames.

## Caddy (simple HTTPS)

Create a `Caddyfile` in this folder and run Caddy alongside Wingman:

```caddyfile
wingman.example.com {
    reverse_proxy /api/* backend:8000
    reverse_proxy frontend:3000
}
```

Run Caddy on the same Docker network (`wingman-net`) so it can reach `backend` and
`frontend`.

## Traefik (docker labels)

If you run Traefik separately, you can add labels to the frontend/backed services.
Example snippet:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.wingman.rule=Host(`wingman.example.com`)"
  - "traefik.http.services.wingman.loadbalancer.server.port=3000"
  - "traefik.http.routers.wingman-api.rule=Host(`wingman.example.com`) && PathPrefix(`/api`)"
  - "traefik.http.services.wingman-api.loadbalancer.server.port=8000"
```

Make sure Traefik is attached to the `wingman-net` network.
