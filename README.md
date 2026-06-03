# trading-dashboard

A full-stack Django SaaS trading dashboard with real trade data from a live cTrader account.

Built with Django 5, DRF REST API, PostgreSQL, Celery, Redis, Django Channels (WebSockets), and Google OAuth. Part of the [trading-platform](https://github.com/DeepaliCS/trading-platform) ecosystem.

---

## Features

- Google OAuth login (django-allauth)
- Multi-tenant architecture — each user sees only their own trades
- Fernet-encrypted cTrader API credentials (per user, stored encrypted in PostgreSQL)
- Incremental trade sync from live cTrader account via Celery async task
- Real-time sync status via Django Channels WebSocket
- Live price ticker via WebSocket (`ws/prices/<symbol>/`)
- Plotly equity curve and monthly P&L charts
- DRF REST API — 7 endpoints with token + session auth
- Calls trading-analytics service for advanced metrics and reports
- Docker + docker-compose (web + worker + PostgreSQL + Redis)
- 37 tests, 100% passing
- GitHub Actions CI/CD

---

## Stack

| Layer | Technology |
|---|---|
| Framework | Django 5, Django REST Framework |
| Auth | Google OAuth (django-allauth) |
| Database | PostgreSQL |
| Async tasks | Celery, Redis |
| WebSockets | Django Channels |
| Charts | Plotly |
| Encryption | Fernet (cryptography) |
| Containerisation | Docker, docker-compose |
| Tests | pytest, pytest-django |
| CI | GitHub Actions |

---

## Installation

```bash
git clone https://github.com/DeepaliCS/trading-dashboard
cd trading-dashboard
pip install -r requirements.txt
cp .env.example .env
# Fill in your .env values
python manage.py migrate
python manage.py runserver
```

---

## Quick Start with Docker

```bash
docker-compose up --build
```

Services:
- Web: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/trades/` | Paginated trade list (filterable by symbol, direction) |
| GET | `/api/v1/trades/<id>/` | Single trade detail |
| GET | `/api/v1/trades/stats/` | Summary stats: win rate, PnL, trade count |
| POST | `/api/v1/credentials/` | Save encrypted cTrader credentials |
| POST | `/api/v1/sync/` | Trigger async trade sync (Celery) |
| GET | `/api/v1/sync/status/` | Last sync log |
| GET | `/api/v1/analytics/report/` | Full strategy report (via trading-analytics) |

All endpoints require authentication (session or token).

---

## WebSocket Endpoints

| Endpoint | Description |
|---|---|
| `ws/prices/<symbol>/` | Real-time spot price stream |
| `ws/sync/<user_id>/` | Trade sync status updates |

Example:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/prices/XAUUSD/');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`${data.symbol}: bid=${data.bid} ask=${data.ask}`);
};
```

---

## Environment Variables

```env
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=trading_dashboard
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
REDIS_URL=redis://localhost:6379/0
FIELD_ENCRYPTION_KEY=your-fernet-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
ANALYTICS_API_URL=http://localhost:8001/api/v1
CTRADER_CLIENT_ID=your-ctrader-client-id
CTRADER_CLIENT_SECRET=your-ctrader-client-secret
CTRADER_ACCESS_TOKEN=your-access-token
CTRADER_ACCOUNT_ID=your-account-id
```

Generate Fernet key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
trading-dashboard/
├── config/
│   ├── settings.py          ← Django settings (PostgreSQL, Channels, Celery, allauth)
│   ├── settings_test.py     ← Test settings (SQLite in-memory)
│   ├── asgi.py              ← ASGI + Django Channels routing
│   └── urls.py              ← URL configuration
├── trading/
│   ├── models.py            ← CTraderCredentials, Symbol, Trade, SyncLog
│   ├── encryption.py        ← Fernet encryption helpers
│   ├── tasks.py             ← Celery tasks (sync, metrics)
│   ├── consumers.py         ← Django Channels WebSocket consumers
│   ├── routing.py           ← WebSocket URL routing
│   ├── services/
│   │   ├── ctrader_client.py ← cTrader sync (Twisted + Protobuf)
│   │   └── data_fetcher.py
│   └── api/
│       ├── serializers.py   ← DRF serializers
│       ├── views.py         ← 7 REST API views
│       └── urls.py          ← API URL routing
├── dashboard/
│   ├── views.py             ← Plotly chart views
│   ├── services/
│   │   └── analytics_client.py ← HTTP client for trading-analytics API
│   └── templates/
│       └── dashboard/home.html
├── tests/
│   ├── test_models.py       ← 18 model tests
│   └── test_api.py          ← 19 API tests
├── .github/workflows/
│   └── test.yml             ← GitHub Actions CI
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
└── requirements.txt
```

---

## Part of the Trading Platform Ecosystem

| Repo | Role |
|---|---|
| [ctrader-client](https://github.com/DeepaliCS/ctrader-client) | Async cTrader API client — data source |
| [trading-analytics](https://github.com/DeepaliCS/trading-analytics) | ETL pipeline + analytics API |
| **trading-dashboard** | This repo — Django SaaS dashboard |
| [ai-journal](https://github.com/DeepaliCS/ai-journal) | AI trade journaling (RAG + Claude API) |

---

## Author

Senior Python developer specialising in Django, FastAPI, AWS and trading systems.
[GitHub](https://github.com/DeepaliCS)
