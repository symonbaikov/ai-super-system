# API Endpoint Testing Documentation

This document details the testing of the basic API endpoints as defined in `docs/ui_integration_checklist.md`.

Each section includes the command used for testing, its purpose, and the result of the execution.

## 1. GET /api/metrics/latency-usage

**Command:**
```bash
curl -s http://localhost:8080/api/metrics/latency-usage
```

**Description:**
This command retrieves API latency and usage metrics.

**Result:**
The command failed with exit code 7, which indicates that the connection to `localhost:8080` could not be established. The service appears to be down.

**Output:**
```
(empty)
```

## 2. POST /api/cex-radar/search and GET /api/cex-radar/result

**Commands:**
```bash
# Command to start the search
curl -s -X POST http://localhost:8080/api/cex-radar/search -H 'Content-Type: application/json' -d '{"query":"OPTIMUS"}'

# Command to get the result (requires a valid jobId from the previous command)
curl -s "http://localhost:8080/api/cex-radar/result?jobId=..."
```

**Description:**
The first command starts a search for a token on CEXs and should return a `jobId`. The second command uses this `jobId` to retrieve the search results.

**Result:**
The `POST` command failed with exit code 7, indicating the service is not running. Consequently, the `GET` command could not be tested.

**Output:**
```
(empty)
```

## 3. GET /api/helius/mints

**Command:**
```bash
curl -s http://localhost:8080/api/helius/mints
```

**Description:**
This command retrieves recent mints from Helius.

**Result:**
The command failed with exit code 7, indicating the service is not running.

**Output:**
```
(empty)
```

## 4. POST /api/whales/scan and GET /api/whales/top3

**Commands:**
```bash
curl -s -X POST http://localhost:8080/api/whales/scan
curl -s "http://localhost:8080/api/whales/top3?jobId=..."
```

**Description:**
Starts a whale scan and retrieves the top 3 results.

**Result:**
The `POST` command failed with exit code 7. The service appears to be down.

**Output:**
```
(empty)
```

## 5. POST /api/alerts/enable and GET /api/alerts

**Commands:**
```bash
curl -s -X POST http://localhost:8080/api/alerts/enable -H 'Content-Type: application/json' -d '{"mint":"So1...","msar":0.6,"volume":5000,"liquidity":20000,"enabled":true}'
curl -s http://localhost:8080/api/alerts
```

**Description:**
Enables a new alert and lists the currently configured alerts.

**Result:**
Both commands failed with exit code 7. The service appears to be down.

**Output:**
```
(empty)
```

## 6. POST /api/ai/infer

**Command:**
```bash
curl -s -X POST http://localhost:8080/api/ai/infer -H 'Content-Type: application/json' -d '{"provider":"gemini","model":"gemini-2.5-flash","prompt":"test"}'
```

**Description:**
Sends a prompt to the AI inference endpoint.

**Result:**
The command failed with exit code 7. The service appears to be down.

**Output:**
```
(empty)
```

## Conclusion

All attempts to connect to the API service at `http://localhost:8080` failed. The primary issue is that the backend service is not running or is not accessible at this address. To proceed with testing, the backend application must be started first. The documentation in `docs/deploy.md` or `docker-compose.yml` should provide instructions on how to start the services.
