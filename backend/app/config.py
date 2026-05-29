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

    # Voice (Sarvam AI + Plivo/Twilio/Exotel)
    sarvam_api_key: str = ""
    voice_provider: str = "plivo"   # "plivo", "twilio", or "exotel"
    plivo_auth_id: str = ""
    plivo_auth_token: str = ""
    plivo_phone_number: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    exotel_sid: str = ""
    exotel_token: str = ""
    exotel_subdomain: str = ""
    exotel_phone_number: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
