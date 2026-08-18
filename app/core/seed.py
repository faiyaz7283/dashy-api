"""Database seeding for initial family member setup.

On first startup, if the family_members table is empty and FAMILY_MEMBERS
is configured in the environment, seeds the database with those members.
After seeding, the database becomes the single source of truth.
"""

from app.config import settings
from app.core.database import get_async_session_factory
from app.core.logging import get_logger
from app.domain.family.models import FamilyMember
from app.infrastructure.persistence.family_repository import FamilyRepositoryImpl

logger = get_logger(__name__)


async def seed_family_members_if_empty() -> None:
    """Seed family members from environment if the database is empty.

    This runs once on startup. If the family_members table has no rows
    and FAMILY_MEMBERS is configured in the environment, creates those
    members in the database. After seeding, the database is the canonical
    source and the environment variable is no longer used.

    This allows migrating from the old config-based approach to the new
    database-backed approach without manual intervention.
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        repository = FamilyRepositoryImpl(session)
        existing = await repository.get_all()

        if existing:
            logger.info(
                "family_members_already_seeded",
                count=len(existing),
            )
            return

        config_members = settings.get_family_members()
        if not config_members:
            logger.info("no_family_members_to_seed")
            return

        for config_member in config_members:
            member = FamilyMember(
                id=config_member.key,
                name=config_member.name,
                email=config_member.email,
                color=config_member.color,
                initial=config_member.name[0].upper() if config_member.name else "",
            )
            await repository.save(member)

        logger.info(
            "family_members_seeded",
            count=len(config_members),
            members=[m.key for m in config_members],
        )
