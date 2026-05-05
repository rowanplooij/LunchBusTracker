# Lunch Bus Tracker

Real-time map tracker for the Copernicus lunch bus. Shows the bus location on a full-screen map and notifies you when it arrives at the office.

## Features

- Live bus position updated every 30s (every 15s between 12:25–12:45 when the bus is expected)
- Tracking is only active between 12:00 and 13:00
- Countdown showing "Bus in ~X min" from up to an hour before lunch
- 100m arrival zone around the Copernicus office — triggers a browser notification + audio chime when the bus enters it
- Custom map icons for the bus and the office

## Run with Docker

```bash
docker compose up -d
```

Then open [http://localhost:8080](http://localhost:8080).

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

## Configuration

All tuneable values are at the top of [app.py](app.py):

| Constant | Default | Description |
|---|---|---|
| `ACTIVE_START` / `ACTIVE_END` | 12:00 – 13:00 | Window during which the GPS is polled |
| `ALERT_START` / `ALERT_END` | 12:15 – 12:45 | Window during which arrival is checked |
| `HIGH_FREQ_START` | 12:25 | Start of the 15s refresh interval |
| `ARRIVAL_RADIUS_M` | 100 | Metres from the office that counts as arrived |
| `COPERNICUS` | 52.2918, 4.7264 | Office coordinates |
