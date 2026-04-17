from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.data import router as data_router
from app.api.train import router as train_router
from app.api.chat import router as chat_router

app = FastAPI(title="LLM Fine-tune WebUI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data_router)
app.include_router(train_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    return {"message": "LLM Fine-tune WebUI API"}
