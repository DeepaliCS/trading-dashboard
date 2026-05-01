# Trading Dashboard

A multi-user web application for active traders to connect their cTrader accounts and visualise their trading performance, with an AI-powered journaling assistant (in development) for strategy adherence and behavioural pattern analysis.

Built by an active gold/FX trader (verified MyFXBook +174%) for traders who actually need it.

## Screenshots
<img width="1917" height="908" alt="Screenshot 2026-05-01 174500" src="https://github.com/user-attachments/assets/2fda3547-be7e-4fc5-b829-0ae4f1b5d7e0" />

## Why this exists

Most retail trading dashboards are either generic (MyFXBook, FXBlue) or locked into specific brokers. Prop firm traders (FTMO, MyForexFunds) are an underserved segment with very specific needs: strategy adherence tracking, drawdown rule monitoring, and behavioural pattern recognition.

This project is a foundation for those features, with multi-tenant architecture from day one.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Django 5.0 + Django REST Framework |
| Database | PostgreSQL (production), SQLite (dev) |
| Auth | Django + django-allauth (Google OAuth) + JWT for API |
| Broker integration | cTrader Open API via `ctrader-open-api` (Twisted-based async protocol) |
| AI | Anthropic Claude API (planned — trade journaling) |
| Visualisation | Plotly |
| Deployment | Render (planned) |

## Architecture highlights

- **Per-user encrypted credentials.** cTrader API secrets stored encrypted-at-rest using Fernet symmetric encryption, with key separation from the database. See [`trading/encryption.py`](trading/encryption.py) and the property-based encrypt/decrypt pattern in [`trading/models.py`](trading/models.py).
- **Twisted reactor integrated with Django ORM.** The cTrader Open API is built on Twisted's async protocol. The sync service ([`trading/services/ctrader_client.py`](trading/services/ctrader_client.py)) bridges Twisted callbacks to Django's ORM cleanly, with chunked weekly fetches respecting cTrader's API rate limits.
- **Incremental sync.** A `SyncLog` model tracks `last_synced_at` per user, so subsequent syncs only fetch new deals — minimising API calls and avoiding duplicate data.
- **Multi-tenancy from day one.** All trade and credential models are scoped by `user` foreign key with appropriate indexes.

## Local development

### Prerequisites

- Python 3.11
- A cTrader account + API credentials from [openapi.ctrader.com](https://openapi.ctrader.com)

### Setup

```bash
# Clone and create env
git clone <your-repo-url>
cd trading-dashboard
conda create -n trading-dashboard python=3.11 -y
conda activate trading-dashboard
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your cTrader credentials and generated keys
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Migrate and run
python manage.py migrate
python manage.py createsuperuser
python manage.py setup_ctrader --username <your-username>
python manage.py sync_trades --username <your-username>
python manage.py runserver
```

Visit `http://localhost:8000/dashboard/`.

## Roadmap

- [x] cTrader account connection (encrypted, multi-tenant)
- [x] Trade history sync (incremental, chunked)
- [x] Dashboard with equity curve + P&L breakdown
- [ ] Google OAuth (django-allauth)
- [ ] AI trade journaling with Claude API (strategy adherence, pattern detection, weekly reports)
- [ ] Deploy to Render
- [ ] Architecture diagram

## About the author

Senior Python developer (8 years, primarily Django + AWS). Currently based in Dubai, building this project as a portfolio piece while job hunting for senior backend roles.

[LinkedIn](https://www.linkedin.com/in/ddiippssyy/)
