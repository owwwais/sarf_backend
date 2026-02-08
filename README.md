# SmartBudget AI Backend

FastAPI backend for SmartBudget AI - a zero-based budgeting app with AI-powered SMS analysis.

## Features

- **Authentication** via Supabase Auth
- **Accounts** management (checking, savings, credit, cash)
- **Categories & Groups** for zero-based budgeting
- **Transactions** CRUD with filtering
- **AI SMS Analysis** using Google Gemini - automatically parse bank SMS messages
- **Auto-categorization** of transactions using AI
- **Monthly AI Reports** with financial insights

## Tech Stack

- **FastAPI** - Python web framework
- **Supabase** - Database & Authentication
- **Google Gemini** - AI/LLM for SMS parsing
- **Uvicorn** - ASGI server

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/owwwais/sarf_backend.git
cd sarf_backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual values
```

Required environment variables:
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Supabase service role key
- `SUPABASE_JWT_SECRET` - JWT secret from Supabase
- `GEMINI_API_KEY` - Google Gemini API key

### 3. Run

```bash
uvicorn app.main:app --reload --port 8001
```

API docs available at: `http://localhost:8001/docs`

## Deployment

### Railway (Recommended)

1. Connect GitHub repo
2. Set environment variables
3. Deploy automatically

### Render

1. Create new Web Service
2. Connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login |
| GET | `/accounts/` | List accounts |
| POST | `/accounts/` | Create account |
| GET | `/categories/groups` | List category groups |
| POST | `/categories/groups` | Create group |
| GET | `/categories/` | List categories |
| POST | `/categories/` | Create category |
| GET | `/transactions/` | List transactions |
| POST | `/transactions/` | Create transaction |
| POST | `/ai/analyze-sms` | Analyze SMS message |
| POST | `/ai/auto-process-sms` | Auto-process SMS |
| POST | `/ai/monthly-report` | Generate AI report |
| GET | `/ai/status` | Check AI service status |
