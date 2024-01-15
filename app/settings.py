import logging.config
import os

env = os.environ.get

DATABASE_URL = (
    f"postgresql+asyncpg://{env('POSTGRES_USER')}:{env('POSTGRES_PASSWORD')}"
    f"@db:{env('POSTGRES_PORT')}/{env('POSTGRES_DB')}"
)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "sqlalchemy.engine.Engine": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING)

STATE_URL = env("STATE_URL")
STATE_INTERVAL = env("STATE_INTERVAL")
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")
REDIS_URL = env("REDIS_URL")
