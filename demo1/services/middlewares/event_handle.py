from fastapi import FastAPI


def register_event_handler(app: FastAPI):
    @app.on_event("shutdown")
    def app_shutdown_event():
        ...
