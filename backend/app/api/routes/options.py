from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.options_schemas import OptionsResponse
from app.modules.experiments.service import ExperimentService
from app.persistence.database import get_session

router = APIRouter(prefix="/options", tags=["options"])


@router.get("", response_model=OptionsResponse)
def get_options(session: Session = Depends(get_session)) -> OptionsResponse:
    service = ExperimentService(session)
    return service.get_options()
