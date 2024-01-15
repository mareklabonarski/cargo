import logging

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


def raise_integrity_error(integrity_error: IntegrityError):
    logging.error(str(integrity_error))
    raise HTTPException(status_code=409, detail=str(integrity_error).split('\n')[1])
