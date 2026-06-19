from fastapi import APIRouter

from app.config import settings
from app.schemas.imprint import ImprintResponse

router = APIRouter()


@router.get("", response_model=ImprintResponse)
def get_imprint():
    return ImprintResponse(
        company_name=settings.imprint_company_name,
        address_street=settings.imprint_address_street,
        address_city=settings.imprint_address_city,
        email=settings.imprint_email,
        phone=settings.imprint_phone,
        responsible_person=settings.imprint_responsible_person,
        eu_odr_link=settings.imprint_eu_odr_link,
        dsgvo_contact_email=settings.dsgvo_contact_email,
        dsgvo_data_protection_officer=settings.dsgvo_data_protection_officer,
    )
