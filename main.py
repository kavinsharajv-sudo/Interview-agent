# main.py
from fastapi import FastAPI
from dotenv import load_dotenv
load_dotenv()

from auth.router      import router as auth_router
from routers.interview import router as interview_router

app = FastAPI(title="Interview Automation API")

# auth endpoints — public, no token needed
app.include_router(auth_router,      prefix="/auth",      tags=["auth"])

# interview endpoints — protected, token required
app.include_router(interview_router, prefix="/interview",  tags=["interview"])


@app.get("/health")
def health():
    return {"status": "ok"}
