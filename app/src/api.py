import asyncio
import os
from typing import Any, Dict, List

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    UserNotMutualContactError,
    UserPrivacyRestrictedError,
)
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.contacts import AddContactRequest
from telethon.tl.types import Message, User

from app.utils.logger import ColorLogger
from app.utils.models import UserExportData, dbUser

# Inicializa o logger para a classe
logger = ColorLogger("Scraper")


class TelegramManeger:
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

    def _extract_user_data(self, user: User) -> dbUser:
        """Extrai e formata as informações necessárias de um objeto User (Telethon)."""
        return dbUser(
            id=user.id,
            username=user.username if user.username else None,
            first_name=user.first_name if user.first_name else None,
            last_name=user.last_name if user.last_name else None,
            is_bot=user.bot,
        )

    async def get_last_100_users(self) -> List[dbUser]:
        """
        Busca as últimas 100 mensagens usando Telethon, coleta usuários
        e obedece o limite FLOOD_WAIT (FloodWaitError).
        """
        unique_users: Dict[int, dbUser] = {}
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

    async def get_group_members(self, group_id_int: int) -> List[dbUser]:
        """
        Busca os membros do grupo de origem e retorna uma lista de IDs de usuários.
        """
        try:
            # Obtem a lista de usuários do grupo de origem
            users = await self.client.get_participants(group_id_int)
            logger.info(f"Total de usuários encontrados: {len(users)}")
            return [self._extract_user_data(user) for user in users]
        except Exception as e:
            logger.critical(f"Erro ao buscar membros do grupo: {e}")
            return []

    async def add_user_to_group(
        self, users_to_add: List[int], target_group_id: int
    ) -> bool:
        """
        Lê o cache de usuários e tenta adicionar cada um ao grupo de destino,
        respeitando os limites de FLOOD_WAIT.
        """
        logger.info(
            f"Tentando adicionar {len(users_to_add)} usuários ao grupo ID: {target_group_id}"
        )
        try:
            result = await self.client(
                InviteToChannelRequest(channel=int(target_group_id), users=users_to_add)
            )
            logger.debug(result)
            logger.info("usuario adicionado com sucesso")
            return True

        except FloodWaitError as e:
            wait_time = e.seconds
            safe_wait_time = wait_time + 5
            logger.critical(f"FLOOD_WAIT (LOTE)! Esperando por {safe_wait_time}s.")
            await asyncio.sleep(safe_wait_time)
            return

        except UserPrivacyRestrictedError:
            logger.critical(
                "Falha (Privacidade) ao adicionar o lote: Pelo menos um usuário no lote não permite convites. Tente adicionar individualmente se for crítico."
            )
            await asyncio.sleep(120)  # Pausa maior devido à falha crítica
            return

        except UserNotMutualContactError:
            logger.warning(
                f"Usuario {users_to_add} não permite adição de contatos desconhecidos! [30 segundos]"
            )
            await asyncio.sleep(30)
            return

        except Exception as e:
            wait_time = 300  # 5 minutos para erros persistentes no lote
            logger.critical(
                f"Erro INESPERADO ao adicionar o {users_to_add}: {e}. Aguardando {wait_time}s."
            )
            await asyncio.sleep(wait_time)
            return

    async def add_user_to_contact(self, user_to_add: List[int]) -> bool:
        logger.info(f"Adicionando {len(user_to_add)} usuarios aos contatos")
        try:
            for user in user_to_add:
                result = await self.client(
                    AddContactRequest(
                        id=user,
                        first_name=f"user_{os.urandom(4).hex()}",
                        last_name="",
                        phone="",
                        add_phone_privacy_exception=False,
                    )
                )
                logger.debug(result)
                logger.info("Contato adicionado com sucesso [10 segundos]")
                await asyncio.sleep(10)

            # Verifica se o resultado possui usuários e se o primeiro usuário tem a foto com o atributo 'personal'
            return True
        except Exception as e:
            logger.warning(
                f"Não foi possivel adicionar {user_to_add} aos contados pulando: {e}"
            )
            return
