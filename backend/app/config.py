from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_api_key: str | None = None
    llm_model: str = "groq-small"
    llm_api_url: str = "https://api.groq.com/v1"
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
    sarvam_tts_voice: str = "abhilash"  # male voice; see SarvamTTSSpeakerV2/V3
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
    daily_api_key: str = ""

    # Storage
    sqlite_path: str = "data/receptionist.db"

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()
