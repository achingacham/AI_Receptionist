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

    class Config:
        env_file = ".env"


settings = Settings()
