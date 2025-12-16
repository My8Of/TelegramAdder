import asyncio
import os
from datetime import datetime
from threading import Thread
from typing import Any, Dict, List

from dotenv import load_dotenv

from app.src.api import TelegramManeger
from app.utils.cache import save_users_cache
from app.utils.db_manager import TelegramDatabase
from app.utils.logger import ColorLogger
from app.utils.models import UserExportData, Users

load_dotenv()

try:
    API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
except ValueError:
    API_ID = 0


API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER")
GROUP_ID = os.getenv("TELEGRAM_GROUP_ID")
TARGET_GROUP_ID = os.getenv("TELEGRAM_TARGET_GROUP_ID")
DUMMY_ID = os.getenv("DUMMY_ID")
HOST = os.getenv("DB_HOST")
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
DATABASE = os.getenv("DB_NAME")

logger = ColorLogger("Main")
if HOST and USER and PASSWORD and DATABASE:
    db = TelegramDatabase(host=HOST,user=USER,password=PASSWORD,database=DATABASE)
else:
    db = None
    logger.warning("Database não setada no env inciando sessão temporaria")

LOGO = """
░▒▓███████▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░ ░▒▓█████████████▓▒░
"""



async def with_db():
    print(LOGO)  # O logo é impresso no logger, não no print.
    logger.info("Starting Telegram Scraper")
    connector = TelegramManeger(API_ID, API_HASH, PHONE_NUMBER, GROUP_ID)

    try:
        if not all(
            [API_ID, API_HASH, PHONE_NUMBER, GROUP_ID, TARGET_GROUP_ID]
        ):  # TARGET_GROUP_ID também é obrigatório
            logger.error(
                "Por favor, configure as variáveis de ambiente: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE_NUMBER, TELEGRAM_GROUP_ID e TELEGRAM_TARGET_GROUP_ID."
            )

        # A lógica de raspagem deve ser executada
        async with connector as scraper:
            users_list: List[dbUser] = await scraper.get_group_members(group_id_int=int(GROUP_ID))    

            if users_list:
                logger.info(
                    f"Busca finalizada. Total de {len(users_list)} usuários únicos prontos para exportação/adição."
                )

            if not users_list:
                logger.warning("Nenhum usuário foi coletado.")
            for user in users_list:
                await db.save_user(user=user)
                await connector.add_user_to_group(users_to_add=[int(user.id)], target_group_id=int(TARGET_GROUP_ID))

    except Exception as e:
        logger.critical(f"Falha na execução do scraper principal: {e}")

async def without_db():
    print(LOGO)  # O logo é impresso no logger, não no print.
    logger.info("Starting Telegram Scraper")
    connector = TelegramManeger(API_ID, API_HASH, PHONE_NUMBER, GROUP_ID)

    try:
        if not all(
            [API_ID, API_HASH, PHONE_NUMBER, GROUP_ID, TARGET_GROUP_ID]
        ):  # TARGET_GROUP_ID também é obrigatório
            logger.error(
                "Por favor, configure as variáveis de ambiente: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE_NUMBER, TELEGRAM_GROUP_ID e TELEGRAM_TARGET_GROUP_ID."
            )

        # A lógica de raspagem deve ser executada
        async with connector as scraper:
            users_list: List[dbUser] = await scraper.get_group_members(group_id_int=int(GROUP_ID))    

            if users_list:
                logger.info(
                    f"Busca finalizada. Total de {len(users_list)} usuários únicos prontos para exportação/adição."
                )

            if not users_list:
                logger.warning("Nenhum usuário foi coletado.")
            for user in users_list:
                await connector.add_user_to_group(users_to_add=[int(user.id)], target_group_id=int(TARGET_GROUP_ID))

    except Exception as e:
        logger.critical(f"Falha na execução do scraper principal: {e}")


if __name__ == "__main__":
    if db:  
        asyncio.run(with_db())
    else:
        asyncio.run(without_db())
