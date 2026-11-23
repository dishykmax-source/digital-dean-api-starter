from fastapi import FastAPI
from app.api.students import router as students_router
from app.api import secure_notes, crypto_lab

app = FastAPI(title="Digital Dean API", version="0.2.0")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(students_router)
app.include_router(secure_notes.router, prefix="/api/v1")
app.include_router(crypto_lab.router, prefix="/api/v1")
