from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, accounts, categories, transactions, budget, ingest, subscriptions, ai

app = FastAPI(
    title="SmartBudget AI API",
    description="Zero-Based Budgeting API with AI-powered features",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(accounts.router, prefix="/accounts", tags=["Accounts"])
app.include_router(categories.router, prefix="/categories", tags=["Categories"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(budget.router, prefix="/budget", tags=["Budget"])
app.include_router(ingest.router, prefix="/ingest", tags=["SMS/OCR Ingestion"])
app.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])
app.include_router(ai.router)


@app.get("/")
async def root():
    return {"message": "SmartBudget AI API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
