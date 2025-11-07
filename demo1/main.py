import uvicorn
from fastapi import FastAPI, Depends
from starlette.staticfiles import StaticFiles

from services.middlewares.event_handle import register_event_handler
from services.middlewares.exception_handle import register_exception_handler
from services.middlewares.token_middleware_handle import register_token_middleware
from services.middlewares.log_middleware_handle import register_log_middleware
from routers import api_route
from admin import admin_router

app = FastAPI()

app.include_router(api_route)
app.include_router(admin_router)
register_event_handler(app)
register_exception_handler(app)
register_token_middleware(app)
register_log_middleware(app)


if __name__ == "__main__":
    app.mount("/static", StaticFiles(directory="data/static"), name="static")
    uvicorn.run(app, host="0.0.0.0", port=8003)
