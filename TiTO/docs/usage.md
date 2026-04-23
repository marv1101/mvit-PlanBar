# TiTO Usage

## Voraussetzungen

- Python 3.11+
- Abhängigkeiten installieren mit:

```bash
cd TiTO
python -m pip install -r requirements.txt
```

## Lokaler Start

### API starten

```bash
cd TiTO
python main.py --mode api --port 5000
```

### Worker starten

```bash
cd TiTO
python main.py --mode worker
```

### Beispiel-Job in die Queue legen

```bash
cd TiTO
python main.py --mode seed
```

## Endpunkte

- `GET /health` - Health-Check
- `GET /metrics` - Queue-Metriken
- `GET /jobs` - Liste aller Jobs
- `POST /jobs` - Job in die Queue einfügen
