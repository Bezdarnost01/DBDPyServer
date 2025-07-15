from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional
from models.party import Party
import datetime

class PartyManager:
    @staticmethod
    async def create_party(
        db: AsyncSession,
        *,
        party_id: str,
        host_player_id: str,
        privacy_state: str = "public",
        player_limit: int = 4,
        auto_join_key: int = None,
        expiry_time: int = None,
        player_count: int = 1,
        game_specific_state: dict = None,
        members: list = None
    ) -> Party:
        """
        Создаёт новую пати и сохраняет её в базу.
        Если уже есть пати с таким party_id — сначала удаляет её.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            party_id: Уникальный идентификатор пати (str).
            host_player_id: ID создателя пати.
            privacy_state: Приватность (по умолчанию public).
            player_limit: Максимальное количество участников.
            auto_join_key: Ключ для быстрого входа (если нужен).
            expiry_time: Время истечения действия пати (timestamp, int).
            player_count: Текущее количество участников.
            game_specific_state: Словарь с гибкими настройками.
            members: Список участников (dict).

        Returns:
            Party: созданная пати.
        """
        old_party = await db.execute(select(Party).where(Party.party_id == party_id))
        old_party = old_party.scalar_one_or_none()
        if old_party:
            await db.delete(old_party)
            await db.commit()

        party = Party(
            party_id=party_id,
            host_player_id=host_player_id,
            privacy_state=privacy_state,
            player_limit=player_limit,
            auto_join_key=auto_join_key,
            expiry_time=expiry_time,
            player_count=player_count,
            game_specific_state=game_specific_state or {},
            members=members or [],
        )
        db.add(party)
        await db.commit()
        await db.refresh(party)
        return party

    @staticmethod
    async def get_party(db: AsyncSession, party_id: str) -> Optional[Party]:
        """
        Получить объект пати по её ID.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            party_id: ID пати.

        Returns:
            Party | None: найденная пати или None.
        """
        result = await db.execute(select(Party).where(Party.party_id == party_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_player_party(db: AsyncSession, player_id: str):
        """
        Получить пати, в которой состоит указанный игрок.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            player_id: ID игрока.

        Returns:
            Party | None: найденная пати или None.
        """
        result = await db.execute(select(Party))
        for party in result.scalars():
            if isinstance(party.members, list) and any(m.get("playerId") == player_id for m in party.members):
                return party
        return None

    @staticmethod
    async def get_public_parties(db: AsyncSession) -> List[Party]:
        """
        Получить список всех публичных пати.

        Args:
            db: Асинхронная сессия SQLAlchemy.

        Returns:
            List[Party]: список публичных пати.
        """
        result = await db.execute(select(Party).where(Party.privacy_state == "public"))
        return result.scalars().all()

    @staticmethod
    async def update_party(
        db: AsyncSession,
        party_id: str,
        **fields
    ) -> Optional[Party]:
        """
        Обновить поля пати (гибкий апдейт через kwargs).

        Args:
            db: Асинхронная сессия SQLAlchemy.
            party_id: ID пати.
            fields: ключ-значение полей для апдейта.

        Returns:
            Party | None: обновлённая пати или None.
        """
        result = await db.execute(select(Party).where(Party.party_id == party_id))
        party = result.scalar_one_or_none()
        if not party:
            return None
        for key, value in fields.items():
            if hasattr(party, key):
                setattr(party, key, value)
        await db.commit()
        await db.refresh(party)
        return party

    @staticmethod
    async def delete_party(db: AsyncSession, party_id: str) -> bool:
        """
        Удалить пати по ID.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            party_id: ID пати.

        Returns:
            bool: True если удалено, False если не найдено.
        """
        result = await db.execute(select(Party).where(Party.party_id == party_id))
        party = result.scalar_one_or_none()
        if not party:
            return False
        await db.delete(party)
        await db.commit()
        return True

    @staticmethod
    async def add_member(db: AsyncSession, party_id: str, member: dict) -> Optional[Party]:
        """
        Добавить участника в пати (members — это JSON-список dict).

        Args:
            db: Асинхронная сессия SQLAlchemy.
            party_id: ID пати.
            member: dict с данными участника (например, {"playerId": "1234"}).

        Returns:
            Party | None: пати с обновлёнными участниками или None.
        """
        party = await PartyManager.get_party(db, party_id)
        if not party:
            return None
        if not isinstance(party.members, list):
            party.members = []
        party.members.append(member)
        party.player_count = len(party.members)
        await db.commit()
        await db.refresh(party)
        return party

    @staticmethod
    async def remove_member(
        db: AsyncSession, 
        party_id: str, 
        player_id: str
    ) -> bool:
        """
        Удаляет участника из списка пати.
        Если участник — хост, то удаляет всю пати.
        
        Args:
            db: асинхронная сессия SQLAlchemy.
            party_id: ID пати.
            player_id: ID участника.
        Returns:
            bool: True если что-то удалено (мембер или вся пати), False если не найдено.
        """
        party = await PartyManager.get_party(db, party_id)
        if not party:
            return False

        if player_id == party.host_player_id:
            await db.delete(party)
            await db.commit()
            return True

        if isinstance(party.members, list):
            before = len(party.members)
            party.members = [m for m in party.members if m.get("playerId") != player_id]
            after = len(party.members)
            party.player_count = after
            await db.commit()
            await db.refresh(party)
            return before != after

        return False

    @staticmethod
    async def update_member_state(
        db: AsyncSession,
        party_id: str,
        player_id: str,
        state: dict
    ) -> Optional[Party]:
        """
        Обновить состояние (state) для участника в пати.

        Args:
            db: Асинхронная сессия SQLAlchemy.
            party_id: ID пати.
            player_id: ID игрока.
            state: dict с обновлённым состоянием.

        Returns:
            Party | None: пати с обновлённым members или None.
        """
        party = await PartyManager.get_party(db, party_id)
        if not party or not isinstance(party.members, list):
            return None
        for m in party.members:
            if m.get("playerId") == player_id:
                m.update(state)
        await db.commit()
        await db.refresh(party)
        return party
