from fastapi import FastAPI

from papercast.internal import worker

app = FastAPI()

app.include_router(worker.router)
