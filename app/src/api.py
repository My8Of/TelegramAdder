import asyncio
import json
import os
from syslog import LOG_SYSLOG
from typing import Any, Dict, List

from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import Message, User

from app.utils.logger import ColorLogger
from app.utils.models import UserExportData

# Inicializa o logger para a classe
logger = ColorLogger("Scraper")


class TelegramManger:
    def __init__(self, api_id: int, api_hash: str, phone_number: str, group_id: int):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        # O Telethon é mais flexível: aceita o ID negativo, o username ou o link
        try:
            # Converte a string (ex: "-100...") em um inteiro
            self.group_id_int = int(group_id)
        except ValueError:
            logger.critical(f"O GROUP_ID '{group_id}' não é um número válido.")
            # Você pode levantar um erro ou sair aqui
            raise
        self.session_name = f"scraper_{abs(self.group_id_int)}"

        # O cliente Telethon é instanciado. Ele gerencia o arquivo de sessão.
        self.client = TelegramClient(
            session=self.session_name, api_id=self.api_id, api_hash=self.api_hash
        )
        logger.info(f"Scraper Telethon inicializado para o grupo ID: {group_id}")

        self.cache_file = "app/cache/users.json"

    async def __aenter__(self):
        """Inicia o cliente Telethon e lida com o login inicial."""
        await self.client.start(phone=self.phone_number)
        logger.info("Cliente Telethon conectado. ✅")

        # NOVO PASSO: Forçar a sincronização de diálogos para resolver o ID.
        try:
            # Tentar resolver a entidade AGORA
            entity = await self.client.get_entity(self.group_id_int)
            logger.info(
                f"Peer resolvido com sucesso! Título: {entity.title if hasattr(entity, 'title') else 'Entidade'}"
            )
        except Exception as e:
            logger.critical(
                f"ERRO CRÍTICO: Não foi possível resolver o ID do grupo de origem ({self.group_id_int}). Erro: {e}"
            )
            raise  # Interrompe a execução se o grupo de origem não for encontrado

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Encerra o cliente Telethon."""
        await self.client.disconnect()
        logger.info("[SYSTEM] Cliente Telethon desconectado. 👋")

    def _extract_user_data(self, user: User) -> UserExportData:
        """Extrai e formata as informações necessárias de um objeto User (Telethon)."""
        return {
            "id": user.id,
            "username": user.username if user.username else None,
            "first_name": user.first_name if user.first_name else None,
            "last_name": user.last_name if user.last_name else None,
            "is_bot": user.bot,
        }

    async def get_last_100_users(self) -> List[UserExportData]:
        """
        Busca as últimas 100 mensagens usando Telethon, coleta usuários
        e obedece o limite FLOOD_WAIT (FloodWaitError).
        """
        unique_users: Dict[int, UserExportData] = {}
        limit = 100

        logger.info(f"Buscando as últimas {limit} mensagens com Telethon...")

        try:
            # 🚨 Tratamento do FloodWait no loop de iteração 🚨
            # Telethon usa iter_messages() que retorna um Async Iterador.
            messages = self.client.iter_messages(entity=self.group_id_int, limit=limit)

            # Usamos async for para iterar sobre as mensagens
            logger.info("🕵️ Buscando usuarios e verificando bots...")
            async for message in messages:
                if (
                    message.sender
                    and isinstance(message.sender, User)
                    and not message.sender.bot
                ):
                    user = message.sender
                    if user.id not in unique_users:
                        unique_users[user.id] = self._extract_user_data(user)
            logger.info(
                f"✅ Mensagens processadas. Total de usuários únicos encontrados: {len(unique_users)} ✅"
            )

        except FloodWaitError as e:
            # 🚨 TRATAMENTO CRÍTICO DO FLOOD_WAIT DO TELETHON 🚨
            wait_time = e.seconds
            logger.warning(
                f"FLOOD_WAIT recebido (Telethon). Esperando por {wait_time} segundos."
            )
            await asyncio.sleep(wait_time + 1)
            # Como a busca falhou, o loop principal (se houvesse mais iterações) precisaria recomeçar.
            # Neste caso, como é uma única busca de 100, apenas retornamos o que foi coletado até agora.
        except Exception as e:
            logger.critical(f"Erro inesperado: {e}")
            await asyncio.sleep(20)

        return list(unique_users.values())

    async def add_users_to_group(self, target_group_id: int):
        """
        Lê o cache de usuários e tenta adicionar cada um ao grupo de destino,
        respeitando os limites de FLOOD_WAIT.
        """

        # 1. Carregar o cache (supondo que save_users_cache já foi chamado)
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                users_to_add: List[UserExportData] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.critical(
                f"Cache de usuários não encontrado ou corrompido: {self.cache_file}. Abortando adição."
            )
            return

        safe_users_to_add = users_to_add[:8]

        logger.info(
            f"Tentando adicionar {len(safe_users_to_add)} usuários ao grupo ID: {target_group_id}"
        )

        if not safe_users_to_add:
            logger.warning("Nenhum usuário para adicionar no lote.")
            return

        for user in safe_users_to_add:
            try:
                result = await self.client(
                    InviteToChannelRequest(
                        channel=int(target_group_id), users=[user.get("id")]
                    )
                )
                logger.info(
                    f"Resposta da API para o lote/usuário: {result.stringify()}"
                )

                wait_time = 60  # 1 minuto de pausa é mais seguro para convite em lote
                logger.info(f"Aguardando {wait_time} segundos após o convite em lote.")
                await asyncio.sleep(wait_time)

            except FloodWaitError as e:
                wait_time = e.seconds
                safe_wait_time = wait_time + 5
                logger.critical(f"FLOOD_WAIT (LOTE)! Esperando por {safe_wait_time}s.")
                await asyncio.sleep(safe_wait_time)

            except UserPrivacyRestrictedError:
                logger.critical(
                    "Falha (Privacidade) ao adicionar o lote: Pelo menos um usuário no lote não permite convites. Tente adicionar individualmente se for crítico."
                )
                await asyncio.sleep(120)  # Pausa maior devido à falha crítica

            except Exception as e:
                wait_time = 300  # 5 minutos para erros persistentes no lote
                logger.critical(
                    f"Erro INESPERADO ao adicionar o {user.get('username')}: {e}. Aguardando {wait_time}s."
                )
                await asyncio.sleep(wait_time)

        logger.info(
            "Processo de adição em lote concluído (Verifique o grupo para confirmação de usuários)."
        )
