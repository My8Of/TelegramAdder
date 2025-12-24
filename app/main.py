import asyncio
import os
import time
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv

from app.src.api import TelegramManeger
from app.utils.db_manager import TelegramDatabase
from app.utils.logger import ColorLogger
from app.utils.models import dbUser

load_dotenv()


LOGO = """
░▒▓███████▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░ ░▒▓█████████████▓▒░
"""
print(LOGO)  # O logo é impresso no logger, não no print.

SESSIONS = int(os.getenv("SESSIONS", 1))
API_ID = os.getenv("TELEGRAM_API_ID", "")
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER", "")
GROUP_ID = os.getenv("TELEGRAM_GROUP_ID")
TARGET_GROUP_ID = os.getenv("TELEGRAM_TARGET_GROUP_ID")
DUMMY_ID = os.getenv("DUMMY_ID")
HOST = os.getenv("DB_HOST")
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
DATABASE = os.getenv("DB_NAME")


logger = ColorLogger("Main")

if HOST and USER and PASSWORD and DATABASE:
    db = TelegramDatabase(host=HOST, user=USER, password=PASSWORD, database=DATABASE)
else:
    db = None
    logger.warning("Database não setada no env inciando sessão temporaria")

connector = TelegramManeger(
    api_id=API_ID, api_hash=API_HASH, phone_number=PHONE_NUMBER, group_id=GROUP_ID
)


async def add():
    logger.info("Starting Telegram Scraper")
    try:
        # 1. Coleta inicial de membros (usando o primeiro conector apenas para o scrap)
        async with connector as scraper:
            users_list = await scraper.get_group_members(int(GROUP_ID))

            ignore_list = await db.get_users()
            logger.debug(ignore_list)
            logger.info(f"Ignorando {len(ignore_list)} usuários já adicionados")

            users = [u.id for u in users_list if u.id not in ignore_list]
            logger.debug(f"Adicionando {len(users)} novos usuários")

            if not users:
                logger.warning("Nenhum usuário novo para adicionar.")
                return

            chunks = [users[i : i + 3] for i in range(0, len(users), 3)]

            for user_chunk in chunks:
                if await scraper.add_user_to_contact(user_to_add=user_chunk):
                    await db.check_users(users=user_chunk)
                    res = await scraper.add_user_to_group(
                        users_to_add=user_chunk,
                        target_group_id=int(TARGET_GROUP_ID),
                    )

                    if res:
                        # Define o próximo desbloqueio para este conector (5 min)
                        logger.info("Entrou em cooldown de 5min.")
                        await asyncio.sleep(300)
    except Exception as e:
        logger.critical(f"Falha na execução: {e}")


async def scraper_for_db():
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
            users_list: List[dbUser] = await scraper.get_group_members(
                group_id_int=int(GROUP_ID)
            )

            logger.info("Adicionando usuarios ao banco de dados")
            for user in users_list:
                await db.save_user(user)
    except Exception as e:
        logger.critical(f"Falha na execução do scraper principal: {e}")


if __name__ == "__main__":
    asyncio.run(add())
