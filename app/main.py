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
from telethon.errors import (
    FloodWaitError,
    UserNotMutualContactError,
    UserPrivacyRestrictedError,
)

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


def get_env_list(key: str, is_int: bool = False):
    raw_value = os.getenv(key, "")
    if not raw_value:
        return []

    # Remove colchetes se o usuário insistir em colocá-los, remove espaços e dá split
    cleaned = raw_value.replace("[", "").replace("]", "").replace(" ", "")
    items = cleaned.split(",")

    try:
        return [int(item) for item in items] if is_int else items
    except ValueError as e:
        logger.error(f"Erro ao converter lista da env {key}: {e}")
        return []


SESSIONS = int(os.getenv("SESSIONS", 1))
API_IDS = get_env_list("TELEGRAM_API_IDS", is_int=True)
API_HASHES = get_env_list("TELEGRAM_API_HASHES")
PHONE_NUMBERS = get_env_list("TELEGRAM_PHONE_NUMBERS")
GROUP_ID = os.getenv("TELEGRAM_GROUP_ID")
TARGET_GROUP_ID = os.getenv("TELEGRAM_TARGET_GROUP_ID")
DUMMY_ID = os.getenv("DUMMY_ID")
HOST = os.getenv("DB_HOST")
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
DATABASE = os.getenv("DB_NAME")


logger = ColorLogger("Main")

logger.debug(API_IDS)
logger.debug(API_HASHES)
logger.debug(PHONE_NUMBERS)

if HOST and USER and PASSWORD and DATABASE:
    db = TelegramDatabase(host=HOST, user=USER, password=PASSWORD, database=DATABASE)
else:
    db = None
    logger.warning("Database não setada no env inciando sessão temporaria")


async def add():
    logger.info("Starting Telegram Scraper")
    connectors: List[TelegramManeger] = []

    connector_timeouts = {i: 0 for i in range(SESSIONS + 1)}

    try:
        group_id_int = int(GROUP_ID) if GROUP_ID else 0
    except ValueError:
        logger.error(
            f"TELEGRAM_GROUP_ID '{GROUP_ID}' não é um número inteiro válido. Usando 0."
        )
        group_id_int = 0

    if SESSIONS <= 0:
        logger.critical(
            "SESSIONS é configurado para 0 ou menos, nenhum conector será inicializado."
        )
        exit()
    else:
        for i in range(SESSIONS):
            # Log para depurar qual número está sendo usado agora
            logger.info(
                f"Preparando Conector {i + 1} para o número: {PHONE_NUMBERS[i]}"
            )

            manager = TelegramManeger(
                API_IDS[i], API_HASHES[i], PHONE_NUMBERS[i], group_id_int
            )

            # FORÇAR O START AQUI: Isso fará o terminal pedir o código do conector 1,
            # e depois que você digitar, ele seguirá para o conector 2.
            await manager.client.start(phone=manager.phone_number)

            connectors.append(manager)
            logger.info(f"✅ Conector {i + 1}/{SESSIONS} logado com sucesso.")

    if not connectors:
        logger.error("Nenhum conector disponível.")
        return

    try:
        # 1. Coleta inicial de membros (usando o primeiro conector apenas para o scrap)
        for i in range(SESSIONS):
            async with connectors[i] as scraper:
                logger.info(f"buscando usuarios para o canal {i + 1}")
                users_list = await scraper.get_group_members(int(GROUP_ID))

        ignore_list = await db.get_users()
        users_list = [u.id for u in users_list if u.id not in ignore_list]

        if not users_list:
            logger.warning("Nenhum usuário novo para adicionar.")
            return

        # 2. Lógica de Adição com Rodízio e Timeout
        idx = 0
        chunks = [users_list[i : i + 3] for i in range(0, len(users_list), 3)]

        for user_chunk in chunks:
            success = False

            while not success:
                current_connector = connectors[idx]
                now = time.time()

                # Verifica se o conector atual está em cooldown
                wait_needed = connector_timeouts[idx] - now
                if wait_needed > 0:
                    logger.info(
                        f"Conector {idx} em timeout. Aguardando {int(wait_needed)}s..."
                    )
                    await asyncio.sleep(
                        min(wait_needed, 10)
                    )  # Espera um pouco e tenta o próximo ou o mesmo

                    # Rotaciona para o próximo para verificar se algum outro está livre
                    idx = (idx + 1) % len(connectors)
                    continue

                # Tenta realizar a operação
                try:
                    logger.info(f"Usando Conector [{idx}] para adicionar {user_chunk}")

                    # Nota: Você precisa garantir que o connector esteja conectado.
                    # Se o seu Maneger não gerencia o start/stop interno, use 'async with' aqui.
                    async with current_connector as active_conn:
                        # Tenta adicionar aos contatos primeiro
                        # (Opcional: você pode querer tratar exceção aqui também se for crítico)
                        if await active_conn.add_user_to_contact(
                            user_to_add=user_chunk
                        ):
                            await db.check_users(users=user_chunk)
                            res = await active_conn.add_user_to_group(
                                users_to_add=user_chunk,
                                target_group_id=int(TARGET_GROUP_ID),
                            )

                            if res:
                                # Define o próximo desbloqueio para este conector (5 min)
                                connector_timeouts[idx] = time.time() + 300
                                logger.info(
                                    f"Conector [{idx}] entrou em cooldown de 5min."
                                )
                                success = True

                except FloodWaitError as e:
                    wait_time = e.seconds
                    # Adiciona um buffer de segurança e define o timeout APENAS para este conector
                    connector_timeouts[idx] = time.time() + wait_time + 10
                    logger.warning(
                        f"FLOOD_WAIT no Conector {idx}: aguardando {wait_time}s. Trocando de conector..."
                    )
                    # Não setamos success=True -> o while vai continuar e tentar o próximo conector
                    idx = (idx + 1) % len(connectors)
                    continue

                except (UserPrivacyRestrictedError, UserNotMutualContactError):
                    logger.warning(
                        f"Privacidade restrita no chunk {user_chunk} usando Conector {idx}. Pulando chunk."
                    )
                    # Erro de privacidade geralmente é do usuário alvo, não do conector.
                    # Mas vamos dar um pequeno respiro pro conector
                    connector_timeouts[idx] = time.time() + 30
                    success = True # Consideramos "sucesso" para sair do while e processar PRÓXIMO chunk (pular este)
                    
                except Exception as e:
                    logger.error(f"Erro Genérico no conector {idx}: {e}")
                    # Em caso de erro desconhecido, pune o conector por um tempo maior e tenta outro
                    connector_timeouts[idx] = time.time() + 600
                    idx = (idx + 1) % len(connectors)
                    # break # Sai do while para evitar loop infinito no mesmo chunk se for erro persistente de dados
                    # Se quisermos tentar o mesmo chunk com OUTRO conector, usamos continue.
                    # Se achamos que o chunk está "viciado" (dados ruins), usamos break ou success=True.
                    # Vou assumir que queremos tentar com outro conector:
                    continue

                # Passa para o próximo índice de conector para a próxima rodada
                idx = (idx + 1) % len(connectors)
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
