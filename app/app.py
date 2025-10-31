from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from access_control.controller import router as access_control_router
from adapters.logger import LogLevels, configure_logging
from app_lifespan import lifespan
from auth.controller import router as auth_router
from authority_linking.controller import router as authority_linking_router
from catalog.controller import router as catalog_router
from comparison.controller import router as comparison_router
from config import config
from settings.controller import router as settings_router
from validation.controller import router as validation_router

configure_logging(LogLevels.info)


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors.allow_origins,
    allow_credentials=config.cors.allow_credentials,
    allow_methods=config.cors.allow_methods,
    allow_headers=config.cors.allow_headers,
)

# Register routers
app.include_router(access_control_router)
app.include_router(auth_router)
app.include_router(authority_linking_router)
app.include_router(catalog_router)
app.include_router(comparison_router)
app.include_router(settings_router)
app.include_router(validation_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
