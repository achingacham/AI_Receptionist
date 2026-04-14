from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str | None = None
    groq_model: str = "groq-small"
    groq_api_url: str = "https://api.groq.com/v1"
    business_name: str = "Our Business"
    business_hours: str = "Monday-Friday 9am-5pm"
    business_phone: str = ""
    business_email: str = ""
    business_address: str = ""
    receptionist_name: str = "Alex"

    # Cal.com
    calcom_api_key: str = ""
    calcom_username: str = ""
    calcom_event_type_id: int = 0
    calcom_timezone: str = "Asia/Kolkata"
    calcom_fallback_email: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
