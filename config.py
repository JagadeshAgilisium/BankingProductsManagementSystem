import os
class Settings:
    PROJECT_NAME: str = "Banking Asset Inventory System"
    VERSION: str = "1.0.0"
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGO: str = "HS256"
    TOKEN_EXPIRE_MIN: int = 30
    DB_URL: str = "sqlite:///./banking_products_inventory.db"
    SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
    OWNER_NAME: str = "Jagadesh PJ"
    EMP_ID : str = "10461"
    EMAIL_ID : str = "jagadesh.jayaraman@agilisium.com"

settings = Settings()
