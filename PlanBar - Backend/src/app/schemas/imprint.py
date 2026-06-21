from pydantic import BaseModel


class ImprintResponse(BaseModel):
    company_name: str = ""
    address_street: str = ""
    address_city: str = ""
    email: str = ""
    phone: str = ""
    responsible_person: str = ""
    eu_odr_link: str = "https://ec.europa.eu/consumers/odr/"
    dsgvo_contact_email: str = ""
    dsgvo_data_protection_officer: str = ""
