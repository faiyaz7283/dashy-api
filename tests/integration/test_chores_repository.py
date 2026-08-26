"""Integration tests for ChoresRepositoryImpl against real PostgreSQL.

Tests the SQLModel persistence layer — domain↔DB mapping, queries,
bulk operations, and soft-delete behavior.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel
from uuid6 import uuid7

from app.core.database import get_async_session_factory
from app.domain.chores.models import (
    ChoreAssociation,
    ChoreInstance,
    InstanceStatus,
    MasterChore,
    MasterChoreStatus,
)
from app.infrastructure.persistence.chores_repository import ChoresRepositoryImpl
from app.infrastructure.persistence.models import (
    ChoreAssociationDB,
    ChoreInstanceDB,
    ChoreTagLinkDB,
    MasterChoreDB,
)


@pytest.fixture
async def session():
    """Create a fresh async session and clean chore tables.

    Yields:
        AsyncSession with clean chore tables.
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        # Clean chore tables in dependency order
        await session.execute(ChoreTagLinkDB.__table__.delete())
        await session.execute(ChoreInstanceDB.__table__.delete())
        await session.execute(ChoreAssociationDB.__table__.delete())
        await session.execute(MasterChoreDB.__table__.delete())
        await session.execute(
            SQLModel.metadata.tables["chore_categories"].delete()
        )
        await session.execute(SQLModel.metadata.tables["chore_tags"].delete())
        await session.commit()
        yield session


@pytest.fixture
def repo(session: AsyncSession) -> ChoresRepositoryImpl:
    """Create a repository bound to the test session.

    Args:
        session: AsyncSession fixture.

    Returns:
        ChoresRepositoryImpl instance.
    """
    return ChoresRepositoryImpl(session)


async def _seed_category(repo: ChoresRepositoryImpl) -> UUID:
    """Seed a category and return its ID.

    Args:
        repo: Repository instance.

    Returns:
        Category ID.
    """
    cat = await repo.create_category("Test Category")
    return cat.id


async def _seed_tag(repo: ChoresRepositoryImpl) -> UUID:
    """Seed a tag and return its ID.

    Args:
        repo: Repository instance.

    Returns:
        Tag ID.
    """
    tag = await repo.create_tag("Test Tag")
    return tag.id


async def _seed_master(
    repo: ChoresRepositoryImpl,
    category_id: UUID,
    master_id: UUID | None = None,
    **overrides,
) -> MasterChore:
    """Seed a master chore and return it.

    Args:
        repo: Repository instance.
        category_id: Category FK.
        master_id: Master chore ID (auto-generated if not provided).
        **overrides: Fields to override on the default master.

    Returns:
        Created MasterChore domain entity.
    """
    defaults = {
        "id": master_id or uuid7(),
        "name": "Integration Test Chore",
        "category_id": category_id,
        "created_by": "tester",
    }
    defaults.update(overrides)
    master = MasterChore(**defaults)
    return await repo.create_master_chore(master, tag_ids=[])


class TestCategoryPersistence:
    """Tests for category CRUD against real DB."""

    async def test_create_and_retrieve_category(self, repo: ChoresRepositoryImpl) -> None:
        """Test creating a category and reading it back."""
        created = await repo.create_category("Kitchen")

        categories = await repo.get_categories()
        assert len(categories) == 1
        assert categories[0].id == created.id
        assert categories[0].name == "Kitchen"

    async def test_categories_ordered_by_name(self, repo: ChoresRepositoryImpl) -> None:
        """Test categories are returned sorted by name."""
        await repo.create_category("Zebra")
        await repo.create_category("Alpha")
        await repo.create_category("Middle")

        categories = await repo.get_categories()
        names = [c.name for c in categories]
        assert names == ["Alpha", "Middle", "Zebra"]


class TestTagPersistence:
    """Tests for tag CRUD against real DB."""

    async def test_create_and_retrieve_tag(self, repo: ChoresRepositoryImpl) -> None:
        """Test creating a tag and reading it back."""
        created = await repo.create_tag("Urgent")

        tags = await repo.get_tags()
        assert len(tags) == 1
        assert tags[0].id == created.id
        assert tags[0].name == "Urgent"


class TestMasterChorePersistence:
    """Tests for master chore CRUD with tag associations."""

    async def test_create_master_with_tags(self, repo: ChoresRepositoryImpl) -> None:
        """Test creating a master chore with tag associations."""
        cat_id = await _seed_category(repo)
        tag1_id = await _seed_tag(repo)
        tag2 = await repo.create_tag("Physical")

        master = MasterChore(
            id=uuid7(),
            name="Tagged Chore",
            category_id=cat_id,
            created_by="tester",
        )
        created = await repo.create_master_chore(master, tag_ids=[tag1_id, tag2.id])

        assert len(created.tags) == 2
        tag_names = {t.name for t in created.tags}
        assert tag_names == {"Test Tag", "Physical"}

    async def test_get_master_by_id(self, repo: ChoresRepositoryImpl) -> None:
        """Test fetching a single master by ID."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(repo, cat_id, master_id=master_id)

        fetched = await repo.get_master_chore_by_id(master_id)
        assert fetched is not None
        assert fetched.name == "Integration Test Chore"
        assert fetched.category_id == cat_id

    async def test_get_master_by_id_not_found(self, repo: ChoresRepositoryImpl) -> None:
        """Test fetching non-existent master returns None."""
        result = await repo.get_master_chore_by_id(uuid7())
        assert result is None

    async def test_soft_delete_excludes_from_default_list(
        self, repo: ChoresRepositoryImpl
    ) -> None:
        """Test that soft-deleted masters are excluded from default listing."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(repo, cat_id, master_id=master_id)

        await repo.delete_master_chore(master_id)

        masters = await repo.get_master_chores()
        assert len(masters) == 0

    async def test_soft_delete_included_when_requested(
        self, repo: ChoresRepositoryImpl
    ) -> None:
        """Test that soft-deleted masters appear with include_archived=True."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(repo, cat_id, master_id=master_id)

        await repo.delete_master_chore(master_id)

        masters = await repo.get_master_chores(include_archived=True)
        assert len(masters) == 1
        assert masters[0].status == MasterChoreStatus.ARCHIVED
        assert masters[0].deleted_at is not None

    async def test_update_master_chore(self, repo: ChoresRepositoryImpl) -> None:
        """Test updating master chore fields."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(repo, cat_id, master_id=master_id)

        updated = await repo.update_master_chore(
            master_id,
            {"name": "Updated Name", "difficulty": 4},
        )

        assert updated.name == "Updated Name"
        assert updated.difficulty == 4

    async def test_update_master_replaces_tags(self, repo: ChoresRepositoryImpl) -> None:
        """Test that updating tag_ids replaces existing associations."""
        cat_id = await _seed_category(repo)
        tag1_id = await _seed_tag(repo)
        tag2 = await repo.create_tag("New Tag")

        master = MasterChore(
            id=uuid7(),
            name="Tag Replace Test",
            category_id=cat_id,
            created_by="tester",
        )
        created = await repo.create_master_chore(master, tag_ids=[tag1_id])

        updated = await repo.update_master_chore(
            created.id,
            {"tag_ids": [tag2.id]},
        )

        assert len(updated.tags) == 1
        assert updated.tags[0].name == "New Tag"

    async def test_update_nonexistent_raises(self, repo: ChoresRepositoryImpl) -> None:
        """Test that updating a non-existent master raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await repo.update_master_chore(uuid7(), {"name": "X"})


class TestBulkUpdatePersistence:
    """Tests for bulk master status updates against real DB."""

    async def test_bulk_update_status(self, repo: ChoresRepositoryImpl) -> None:
        """Test bulk status update hits the database correctly."""
        cat_id = await _seed_category(repo)
        ids = [uuid7() for _ in range(3)]
        for mid in ids:
            await _seed_master(repo, cat_id, master_id=mid)

        updated_count = await repo.bulk_update_master_status(
            ids,
            MasterChoreStatus.INACTIVE,
        )

        assert updated_count == 3

        for mid in ids:
            master = await repo.get_master_chore_by_id(mid)
            assert master.status == MasterChoreStatus.INACTIVE

    async def test_bulk_update_partial_ids(self, repo: ChoresRepositoryImpl) -> None:
        """Test bulk update with some non-existent IDs only updates existing."""
        cat_id = await _seed_category(repo)
        real_id = uuid7()
        await _seed_master(repo, cat_id, master_id=real_id)

        updated_count = await repo.bulk_update_master_status(
            [real_id, uuid7()],
            MasterChoreStatus.ARCHIVED,
        )

        assert updated_count == 1

    async def test_bulk_update_empty_list(self, repo: ChoresRepositoryImpl) -> None:
        """Test bulk update with empty list returns 0."""
        updated_count = await repo.bulk_update_master_status(
            [], MasterChoreStatus.INACTIVE
        )
        assert updated_count == 0


class TestInstancePersistence:
    """Tests for instance CRUD against real DB."""

    async def test_create_and_fetch_instance(self, repo: ChoresRepositoryImpl) -> None:
        """Test creating an instance and reading it back."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(repo, cat_id, master_id=master_id)

        today = datetime.now(UTC).date()
        instance_id = uuid7()
        instance = ChoreInstance(
            id=instance_id,
            master_chore_id=master_id,
            period_start=today,
            period_end=today,
            status=InstanceStatus.ACTIVE,
        )
        created = await repo.create_instance(instance)

        fetched = await repo.get_instance_by_id(instance_id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.status == InstanceStatus.ACTIVE
        assert fetched.period_start == today

    async def test_get_instances_filtered_by_master(
        self, repo: ChoresRepositoryImpl
    ) -> None:
        """Test filtering instances by master_chore_id."""
        cat_id = await _seed_category(repo)
        mid1 = uuid7()
        mid2 = uuid7()
        await _seed_master(repo, cat_id, master_id=mid1)
        await _seed_master(repo, cat_id, master_id=mid2)

        today = datetime.now(UTC).date()
        for mid in [mid1, mid1, mid2]:
            await repo.create_instance(
                ChoreInstance(
                    id=uuid7(),
                    master_chore_id=mid,
                    period_start=today,
                    period_end=today,
                    status=InstanceStatus.ACTIVE,
                )
            )

        instances = await repo.get_instances(master_chore_id=mid1)
        assert len(instances) == 2

    async def test_update_instance_status(self, repo: ChoresRepositoryImpl) -> None:
        """Test updating instance status fields."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(repo, cat_id, master_id=master_id)

        today = datetime.now(UTC).date()
        instance_id = uuid7()
        await repo.create_instance(
            ChoreInstance(
                id=instance_id,
                master_chore_id=master_id,
                period_start=today,
                period_end=today,
                status=InstanceStatus.ACTIVE,
            )
        )

        now = datetime.now(UTC)
        updated = await repo.update_instance(
            instance_id,
            {
                "status": InstanceStatus.COMPLETED,
                "completed_by": "tester",
                "completed_at": now,
            },
        )

        assert updated.status == InstanceStatus.COMPLETED
        assert updated.completed_by == "tester"

    async def test_delete_instance_permanently(self, repo: ChoresRepositoryImpl) -> None:
        """Test that delete_instance removes the row from DB."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(repo, cat_id, master_id=master_id)

        today = datetime.now(UTC).date()
        instance_id = uuid7()
        await repo.create_instance(
            ChoreInstance(
                id=instance_id,
                master_chore_id=master_id,
                period_start=today,
                period_end=today,
                status=InstanceStatus.ACTIVE,
            )
        )

        await repo.delete_instance(instance_id)

        result = await repo.get_instance_by_id(instance_id)
        assert result is None


class TestAssociationPersistence:
    """Tests for association CRUD and soft-delete against real DB."""

    async def test_create_and_fetch_association(self, repo: ChoresRepositoryImpl) -> None:
        """Test creating an association and reading it back."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(repo, cat_id, master_id=master_id)

        assoc_id = uuid7()
        association = ChoreAssociation(
            id=assoc_id,
            master_chore_id=master_id,
            member_id="tester",
            created_by="tester",
        )
        await repo.create_association(association)

        fetched = await repo.get_association(assoc_id)
        assert fetched is not None
        assert fetched.member_id == "tester"
        assert fetched.removed_at is None

    async def test_soft_delete_association(self, repo: ChoresRepositoryImpl) -> None:
        """Test that delete sets removed_at but keeps the row."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(repo, cat_id, master_id=master_id)

        assoc_id = uuid7()
        await repo.create_association(
            ChoreAssociation(
                id=assoc_id,
                master_chore_id=master_id,
                member_id="tester",
                created_by="tester",
            )
        )

        await repo.delete_association(assoc_id)

        # Still fetchable directly
        fetched = await repo.get_association(assoc_id)
        assert fetched is not None
        assert fetched.removed_at is not None

        # Excluded from default list
        active = await repo.list_associations(master_chore_id=master_id)
        assert len(active) == 0

        # Included when requested
        all_assocs = await repo.list_associations(
            master_chore_id=master_id, include_removed=True
        )
        assert len(all_assocs) == 1

    async def test_get_associations_by_member(self, repo: ChoresRepositoryImpl) -> None:
        """Test filtering associations by member_id."""
        cat_id = await _seed_category(repo)
        mid1 = uuid7()
        mid2 = uuid7()
        await _seed_master(repo, cat_id, master_id=mid1)
        await _seed_master(repo, cat_id, master_id=mid2)

        assoc1_id = uuid7()
        await repo.create_association(
            ChoreAssociation(
                id=assoc1_id,
                master_chore_id=mid1,
                member_id="arya",
                created_by="tester",
            )
        )
        await repo.create_association(
            ChoreAssociation(
                id=uuid7(),
                master_chore_id=mid2,
                member_id="raya",
                created_by="tester",
            )
        )

        arya_assocs = await repo.get_associations_by_member("arya")
        assert len(arya_assocs) == 1
        assert arya_assocs[0].id == assoc1_id


class TestInstanceQueryHelpers:
    """Tests for specialized instance query methods."""

    async def test_get_instance_for_period(self, repo: ChoresRepositoryImpl) -> None:
        """Test finding an instance by association + period dates."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(repo, cat_id, master_id=master_id)

        assoc_id = uuid7()
        await repo.create_association(
            ChoreAssociation(
                id=assoc_id,
                master_chore_id=master_id,
                member_id="tester",
                created_by="tester",
            )
        )

        today = datetime.now(UTC).date()
        instance_id = uuid7()
        await repo.create_instance(
            ChoreInstance(
                id=instance_id,
                master_chore_id=master_id,
                association_id=assoc_id,
                period_start=today,
                period_end=today,
                status=InstanceStatus.ACTIVE,
            )
        )

        found = await repo.get_instance_for_period(assoc_id, today, today)
        assert found is not None
        assert found.id == instance_id

    async def test_get_instance_for_period_not_found(
        self, repo: ChoresRepositoryImpl
    ) -> None:
        """Test period lookup returns None when no match."""
        today = datetime.now(UTC).date()
        tomorrow = today + timedelta(days=1)

        found = await repo.get_instance_for_period(uuid7(), today, tomorrow)
        assert found is None

    async def test_get_expired_instances(self, repo: ChoresRepositoryImpl) -> None:
        """Test fetching instances past their period_end."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(repo, cat_id, master_id=master_id)

        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        today = datetime.now(UTC).date()

        exp1_id = uuid7()
        exp2_id = uuid7()
        await repo.create_instance(
            ChoreInstance(
                id=exp1_id,
                master_chore_id=master_id,
                period_start=yesterday,
                period_end=yesterday,
                status=InstanceStatus.ACTIVE,
            )
        )
        await repo.create_instance(
            ChoreInstance(
                id=exp2_id,
                master_chore_id=master_id,
                period_start=today,
                period_end=today,
                status=InstanceStatus.ACTIVE,
            )
        )

        expired = await repo.get_expired_instances(today)
        expired_ids = [i.id for i in expired]
        assert exp1_id in expired_ids
        assert exp2_id not in expired_ids

    async def test_archive_instances_by_association(
        self, repo: ChoresRepositoryImpl
    ) -> None:
        """Test archiving active instances for an association."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(repo, cat_id, master_id=master_id)

        assoc_id = uuid7()
        await repo.create_association(
            ChoreAssociation(
                id=assoc_id,
                master_chore_id=master_id,
                member_id="tester",
                created_by="tester",
            )
        )

        today = datetime.now(UTC).date()
        inst1_id = uuid7()
        inst2_id = uuid7()
        await repo.create_instance(
            ChoreInstance(
                id=inst1_id,
                master_chore_id=master_id,
                association_id=assoc_id,
                period_start=today,
                period_end=today,
                status=InstanceStatus.ACTIVE,
            )
        )
        await repo.create_instance(
            ChoreInstance(
                id=inst2_id,
                master_chore_id=master_id,
                association_id=assoc_id,
                period_start=today,
                period_end=today,
                status=InstanceStatus.COMPLETED,
            )
        )

        archived_count = await repo.archive_instances_by_association(assoc_id)

        assert archived_count == 1
        inst_001 = await repo.get_instance_by_id(inst1_id)
        assert inst_001.status == InstanceStatus.ARCHIVED
        inst_002 = await repo.get_instance_by_id(inst2_id)
        assert inst_002.status == InstanceStatus.COMPLETED

    async def test_get_overdue_instances(self, repo: ChoresRepositoryImpl) -> None:
        """Test fetching instances past their due_time."""
        cat_id = await _seed_category(repo)
        master_id = uuid7()
        await _seed_master(
            repo,
            cat_id,
            master_id=master_id,
            due_time="08:00",
        )

        today = datetime.now(UTC).date()
        overdue_id = uuid7()
        await repo.create_instance(
            ChoreInstance(
                id=overdue_id,
                master_chore_id=master_id,
                period_start=today,
                period_end=today,
                status=InstanceStatus.ACTIVE,
            )
        )

        # Query with time well past 08:00
        overdue = await repo.get_overdue_instances(today, "12:00")
        overdue_ids = [i.id for i in overdue]
        assert overdue_id in overdue_ids

        # Query with time before 08:00 — should not be overdue
        not_overdue = await repo.get_overdue_instances(today, "07:00")
        not_overdue_ids = [i.id for i in not_overdue]
        assert overdue_id not in not_overdue_ids
