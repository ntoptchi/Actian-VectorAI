# RigSense Feed

Replays the bottom half of the pump CSV (the part not seeded into
`past_incidents`) as a live `SensorReading` stream to the RigSense backend.

## Run

```bash
cd feed
uvicorn feed.server:app --port 8100
```

Or via `start.sh` which boots it alongside the backend and dashboard.

## Endpoints

- `GET  /health`  - liveness
- `GET  /status`  - tick counter, per-pump cursor, paused flag, speed factor
- `POST /pause`   - halt ticks
- `POST /resume`  - resume ticks
- `POST /speed?factor=2.0` - scale the tick interval (2.0 = twice as fast)

## Config (env)

| var            | default                                   |
|----------------|-------------------------------------------|
| `CSV_PATH`     | `../data/industrial_pump/...CSV`          |
| `BACKEND_URL`  | `http://localhost:8000`                   |
| `TICK_SECONDS` | `2.0`                                     |
| `RIG_ID`       | `rig-north-atlas-07`                      |
