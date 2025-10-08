# Postman troubleshooting for API endpoints

When calling the backend from Postman make sure you target the FastAPI service that runs behind the Traefik proxy.  The stack exposes the API through the `api` service which is available on the local machine as `https://api.localhost`.  Requests that go to `http://localhost:8081` (the Next.js dev server) will never reach the backend and Postman will report `ECONNREFUSED` or `404` errors.

## Checklist

1. **Base URL** – use `https://api.localhost` (or the URL of your remote stack).  Do not point Postman to the web container port.
2. **HTTPS certificate** – Traefik issues a self-signed certificate.  Either disable "SSL certificate verification" in Postman for the environment or import the `traefik/certs/localhost.crt` certificate into your OS trust store.
3. **Endpoint path** – the parser is mounted under `/api/parser/run` in FastAPI.
4. **Docker status** – ensure `docker compose ps` shows the `api` container as `Up (healthy)`.

With this configuration a `POST https://api.localhost/api/parser/run` request with a JSON body will return `202 Accepted` and a payload containing the `job_id` of the enqueued task.
