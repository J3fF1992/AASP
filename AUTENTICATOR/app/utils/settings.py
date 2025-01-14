import os

NOTION_CLIENT_ID = os.getenv("NOTION_CLIENT_ID", "160d872b-594c-8042-951a-003734f3a877")
NOTION_CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET", "secret_CTQ6rFLj9jhcy94y1XXbW8F81zlIwf38ukKfSnTFsab")
# REDIRECT_URI = os.getenv("REDIRECT_URI", "https://a994-187-74-24-52.ngrok-free.app/oauth/callback")
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://bd7b-187-74-24-52.ngrok-free.app/oauth/callback") #teste local
NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://notion_user:notion_password@notion_postgres:5432/notion_db") #docker***
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://notion_user:notion_password@localhost:5432/notion_db") #teste local

