# API tests

Written from the endpoints captured in the browser's network traffic (`make har` → `make endpoints`).
Planned: ≥2 positive calls (projects, pipeline/runs, schedules) and negative calls (no token, tampered token,
unknown id, invalid destination credentials), asserting on status codes and response bodies.
