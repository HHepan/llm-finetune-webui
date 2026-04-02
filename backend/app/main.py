from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.data import router as data_router

app = FastAPI(title="LLM Fine-tune WebUI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data_router)


@app.get("/")
async def root():
    return {"message": "LLM Fine-tune WebUI API"}
