"""Family repository implementation using SQLModel."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.domain.family.models import FamilyMember
from app.domain.family.ports import FamilyRepository
from app.infrastructure.persistence.models import FamilyMemberDB


class FamilyRepositoryImpl(FamilyRepository):
    """SQLModel implementation of FamilyRepository.

    Maps between the domain ``FamilyMember`` (identified by string ``id``)
    and the database ``FamilyMemberDB`` (surrogate int PK, unique ``key``).
    The domain ``id`` corresponds to the DB ``key`` column.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with async session.

        Args:
            session: Async database session.
        """
        self.session = session

    async def get_all(self) -> list[FamilyMember]:
        """Retrieve all family members from database.

        Returns:
            List of domain FamilyMember entities.
        """
        statement = select(FamilyMemberDB)
        result = await self.session.execute(statement)
        db_members = result.scalars().all()
        return [self._to_domain(db_member) for db_member in db_members]

    async def get_by_id(self, member_id: str) -> FamilyMember | None:
        """Retrieve a family member by business ID (key).

        Args:
            member_id: Business identifier (maps to DB ``key`` column).

        Returns:
            FamilyMember if found, None otherwise.
        """
        statement = select(FamilyMemberDB).where(FamilyMemberDB.key == member_id)
        result = await self.session.execute(statement)
        db_member = result.scalar_one_or_none()
        return self._to_domain(db_member) if db_member else None

    async def save(self, member: FamilyMember) -> None:
        """Save a family member to database (create or update).

        Looks up existing records by the ``key`` column (business ID),
        not the surrogate integer PK.

        Args:
            member: FamilyMember to persist.
        """
        statement = select(FamilyMemberDB).where(FamilyMemberDB.key == member.id)
        result = await self.session.execute(statement)
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = member.name
            existing.email = member.email
            existing.color = member.color
            existing.initial = member.initial
            existing.date_of_birth = member.date_of_birth
            existing.relation = member.relation
            self.session.add(existing)
        else:
            db_member = self._to_db(member)
            self.session.add(db_member)

        await self.session.commit()

    async def delete(self, member_id: str) -> None:
        """Delete a family member from database.

        Args:
            member_id: Business identifier (maps to DB ``key`` column).
        """
        statement = select(FamilyMemberDB).where(FamilyMemberDB.key == member_id)
        result = await self.session.execute(statement)
        db_member = result.scalar_one_or_none()
        if db_member:
            await self.session.delete(db_member)
            await self.session.commit()

    def _to_domain(self, db_member: FamilyMemberDB) -> FamilyMember:
        """Convert database model to domain model.

        Maps DB ``key`` → domain ``id``.

        Args:
            db_member: Database row.

        Returns:
            Domain FamilyMember entity.
        """
        return FamilyMember(
            id=db_member.key,
            name=db_member.name,
            email=db_member.email,
            color=db_member.color,
            initial=db_member.initial,
            date_of_birth=db_member.date_of_birth,
            relation=db_member.relation,
        )

    def _to_db(self, member: FamilyMember) -> FamilyMemberDB:
        """Convert domain model to database model.

        Maps domain ``id`` → DB ``key``.

        Args:
            member: Domain entity.

        Returns:
            Database model ready for insertion.
        """
        return FamilyMemberDB(
            key=member.id,
            name=member.name,
            email=member.email,
            color=member.color,
            initial=member.initial,
            date_of_birth=member.date_of_birth,
            relation=member.relation,
        )
