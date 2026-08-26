"""Integration tests for ChoresRepositoryImpl against real SQLite.

Tests the SQLModel persistence layer — domain↔DB mapping, queries,
bulk operations, and soft-delete behavior.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

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


async def _seed_category(repo: ChoresRepositoryImpl) -> str:
    """Seed a category and return its ID.

    Args:
        repo: Repository instance.

    Returns:
        Category ID.
    """
    cat = await repo.create_category("Test Category")
    return cat.id


async def _seed_tag(repo: ChoresRepositoryImpl) -> str:
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
    category_id: str,
    master_id: str = "master-int-001",
    **overrides,
) -> MasterChore:
    """Seed a master chore and return it.

    Args:
        repo: Repository instance.
        category_id: Category FK.
        master_id: Master chore ID.
        **overrides: Fields to override on the default master.

    Returns:
        Created MasterChore domain entity.
    """
    defaults = {
        "id": master_id,
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
            id="master-tags-001",
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
        await _seed_master(repo, cat_id, master_id="master-fetch-001")

        fetched = await repo.get_master_chore_by_id("master-fetch-001")
        assert fetched is not None
        assert fetched.name == "Integration Test Chore"
        assert fetched.category_id == cat_id

    async def test_get_master_by_id_not_found(self, repo: ChoresRepositoryImpl) -> None:
        """Test fetching non-existent master returns None."""
        result = await repo.get_master_chore_by_id("nonexistent")
        assert result is None

    async def test_soft_delete_excludes_from_default_list(
        self, repo: ChoresRepositoryImpl
    ) -> None:
        """Test that soft-deleted masters are excluded from default listing."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="master-del-001")

        await repo.delete_master_chore("master-del-001")

        masters = await repo.get_master_chores()
        assert len(masters) == 0

    async def test_soft_delete_included_when_requested(
        self, repo: ChoresRepositoryImpl
    ) -> None:
        """Test that soft-deleted masters appear with include_archived=True."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="master-del-002")

        await repo.delete_master_chore("master-del-002")

        masters = await repo.get_master_chores(include_archived=True)
        assert len(masters) == 1
        assert masters[0].status == MasterChoreStatus.ARCHIVED
        assert masters[0].deleted_at is not None

    async def test_update_master_chore(self, repo: ChoresRepositoryImpl) -> None:
        """Test updating master chore fields."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="master-upd-001")

        updated = await repo.update_master_chore(
            "master-upd-001",
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
            id="master-tagupd-001",
            name="Tag Replace Test",
            category_id=cat_id,
            created_by="tester",
        )
        await repo.create_master_chore(master, tag_ids=[tag1_id])

        updated = await repo.update_master_chore(
            "master-tagupd-001",
            {"tag_ids": [tag2.id]},
        )

        assert len(updated.tags) == 1
        assert updated.tags[0].name == "New Tag"

    async def test_update_nonexistent_raises(self, repo: ChoresRepositoryImpl) -> None:
        """Test that updating a non-existent master raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await repo.update_master_chore("nonexistent", {"name": "X"})


class TestBulkUpdatePersistence:
    """Tests for bulk master status updates against real DB."""

    async def test_bulk_update_status(self, repo: ChoresRepositoryImpl) -> None:
        """Test bulk status update hits the database correctly."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="bulk-001")
        await _seed_master(repo, cat_id, master_id="bulk-002")
        await _seed_master(repo, cat_id, master_id="bulk-003")

        updated_count = await repo.bulk_update_master_status(
            ["bulk-001", "bulk-002", "bulk-003"],
            MasterChoreStatus.INACTIVE,
        )

        assert updated_count == 3

        for mid in ["bulk-001", "bulk-002", "bulk-003"]:
            master = await repo.get_master_chore_by_id(mid)
            assert master.status == MasterChoreStatus.INACTIVE

    async def test_bulk_update_partial_ids(self, repo: ChoresRepositoryImpl) -> None:
        """Test bulk update with some non-existent IDs only updates existing."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="bulk-partial-001")

        updated_count = await repo.bulk_update_master_status(
            ["bulk-partial-001", "nonexistent"],
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
        await _seed_master(repo, cat_id, master_id="master-inst-001")

        today = datetime.now(UTC).date()
        instance = ChoreInstance(
            id="inst-int-001",
            master_chore_id="master-inst-001",
            period_start=today,
            period_end=today,
            status=InstanceStatus.ACTIVE,
        )
        created = await repo.create_instance(instance)

        fetched = await repo.get_instance_by_id("inst-int-001")
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.status == InstanceStatus.ACTIVE
        assert fetched.period_start == today

    async def test_get_instances_filtered_by_master(
        self, repo: ChoresRepositoryImpl
    ) -> None:
        """Test filtering instances by master_chore_id."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="master-filter-001")
        await _seed_master(repo, cat_id, master_id="master-filter-002")

        today = datetime.now(UTC).date()
        for inst_id, mid in [
            ("inst-f-1", "master-filter-001"),
            ("inst-f-2", "master-filter-001"),
            ("inst-f-3", "master-filter-002"),
        ]:
            await repo.create_instance(
                ChoreInstance(
                    id=inst_id,
                    master_chore_id=mid,
                    period_start=today,
                    period_end=today,
                    status=InstanceStatus.ACTIVE,
                )
            )

        instances = await repo.get_instances(master_chore_id="master-filter-001")
        assert len(instances) == 2

    async def test_update_instance_status(self, repo: ChoresRepositoryImpl) -> None:
        """Test updating instance status fields."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="master-upd-inst")

        today = datetime.now(UTC).date()
        await repo.create_instance(
            ChoreInstance(
                id="inst-upd-001",
                master_chore_id="master-upd-inst",
                period_start=today,
                period_end=today,
                status=InstanceStatus.ACTIVE,
            )
        )

        now = datetime.now(UTC)
        updated = await repo.update_instance(
            "inst-upd-001",
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
        await _seed_master(repo, cat_id, master_id="master-del-inst")

        today = datetime.now(UTC).date()
        await repo.create_instance(
            ChoreInstance(
                id="inst-del-001",
                master_chore_id="master-del-inst",
                period_start=today,
                period_end=today,
                status=InstanceStatus.ACTIVE,
            )
        )

        await repo.delete_instance("inst-del-001")

        result = await repo.get_instance_by_id("inst-del-001")
        assert result is None


class TestAssociationPersistence:
    """Tests for association CRUD and soft-delete against real DB."""

    async def test_create_and_fetch_association(self, repo: ChoresRepositoryImpl) -> None:
        """Test creating an association and reading it back."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="master-assoc-001")

        association = ChoreAssociation(
            id="assoc-int-001",
            master_chore_id="master-assoc-001",
            member_id="tester",
            created_by="tester",
        )
        await repo.create_association(association)

        fetched = await repo.get_association("assoc-int-001")
        assert fetched is not None
        assert fetched.member_id == "tester"
        assert fetched.removed_at is None

    async def test_soft_delete_association(self, repo: ChoresRepositoryImpl) -> None:
        """Test that delete sets removed_at but keeps the row."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="master-assoc-del")

        await repo.create_association(
            ChoreAssociation(
                id="assoc-del-001",
                master_chore_id="master-assoc-del",
                member_id="tester",
                created_by="tester",
            )
        )

        await repo.delete_association("assoc-del-001")

        # Still fetchable directly
        fetched = await repo.get_association("assoc-del-001")
        assert fetched is not None
        assert fetched.removed_at is not None

        # Excluded from default list
        active = await repo.list_associations(master_chore_id="master-assoc-del")
        assert len(active) == 0

        # Included when requested
        all_assocs = await repo.list_associations(
            master_chore_id="master-assoc-del", include_removed=True
        )
        assert len(all_assocs) == 1

    async def test_get_associations_by_member(self, repo: ChoresRepositoryImpl) -> None:
        """Test filtering associations by member_id."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="master-mem-001")
        await _seed_master(repo, cat_id, master_id="master-mem-002")

        await repo.create_association(
            ChoreAssociation(
                id="assoc-mem-001",
                master_chore_id="master-mem-001",
                member_id="arya",
                created_by="tester",
            )
        )
        await repo.create_association(
            ChoreAssociation(
                id="assoc-mem-002",
                master_chore_id="master-mem-002",
                member_id="raya",
                created_by="tester",
            )
        )

        arya_assocs = await repo.get_associations_by_member("arya")
        assert len(arya_assocs) == 1
        assert arya_assocs[0].id == "assoc-mem-001"


class TestInstanceQueryHelpers:
    """Tests for specialized instance query methods."""

    async def test_get_instance_for_period(self, repo: ChoresRepositoryImpl) -> None:
        """Test finding an instance by association + period dates."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="master-period-001")

        await repo.create_association(
            ChoreAssociation(
                id="assoc-period-001",
                master_chore_id="master-period-001",
                member_id="tester",
                created_by="tester",
            )
        )

        today = datetime.now(UTC).date()
        await repo.create_instance(
            ChoreInstance(
                id="inst-period-001",
                master_chore_id="master-period-001",
                association_id="assoc-period-001",
                period_start=today,
                period_end=today,
                status=InstanceStatus.ACTIVE,
            )
        )

        found = await repo.get_instance_for_period("assoc-period-001", today, today)
        assert found is not None
        assert found.id == "inst-period-001"

    async def test_get_instance_for_period_not_found(
        self, repo: ChoresRepositoryImpl
    ) -> None:
        """Test period lookup returns None when no match."""
        today = datetime.now(UTC).date()
        tomorrow = today + timedelta(days=1)

        found = await repo.get_instance_for_period("assoc-none", today, tomorrow)
        assert found is None

    async def test_get_expired_instances(self, repo: ChoresRepositoryImpl) -> None:
        """Test fetching instances past their period_end."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="master-exp-001")

        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        today = datetime.now(UTC).date()

        await repo.create_instance(
            ChoreInstance(
                id="inst-exp-001",
                master_chore_id="master-exp-001",
                period_start=yesterday,
                period_end=yesterday,
                status=InstanceStatus.ACTIVE,
            )
        )
        await repo.create_instance(
            ChoreInstance(
                id="inst-exp-002",
                master_chore_id="master-exp-001",
                period_start=today,
                period_end=today,
                status=InstanceStatus.ACTIVE,
            )
        )

        expired = await repo.get_expired_instances(today)
        expired_ids = [i.id for i in expired]
        assert "inst-exp-001" in expired_ids
        assert "inst-exp-002" not in expired_ids

    async def test_archive_instances_by_association(
        self, repo: ChoresRepositoryImpl
    ) -> None:
        """Test archiving active instances for an association."""
        cat_id = await _seed_category(repo)
        await _seed_master(repo, cat_id, master_id="master-arch-001")

        await repo.create_association(
            ChoreAssociation(
                id="assoc-arch-001",
                master_chore_id="master-arch-001",
                member_id="tester",
                created_by="tester",
            )
        )

        today = datetime.now(UTC).date()
        await repo.create_instance(
            ChoreInstance(
                id="inst-arch-001",
                master_chore_id="master-arch-001",
                association_id="assoc-arch-001",
                period_start=today,
                period_end=today,
                status=InstanceStatus.ACTIVE,
            )
        )
        await repo.create_instance(
            ChoreInstance(
                id="inst-arch-002",
                master_chore_id="master-arch-001",
                association_id="assoc-arch-001",
                period_start=today,
                period_end=today,
                status=InstanceStatus.COMPLETED,
            )
        )

        archived_count = await repo.archive_instances_by_association("assoc-arch-001")

        assert archived_count == 1
        inst_001 = await repo.get_instance_by_id("inst-arch-001")
        assert inst_001.status == InstanceStatus.ARCHIVED
        inst_002 = await repo.get_instance_by_id("inst-arch-002")
        assert inst_002.status == InstanceStatus.COMPLETED

    async def test_get_overdue_instances(self, repo: ChoresRepositoryImpl) -> None:
        """Test fetching instances past their due_time."""
        cat_id = await _seed_category(repo)
        await _seed_master(
            repo,
            cat_id,
            master_id="master-overdue-001",
            due_time="08:00",
        )

        today = datetime.now(UTC).date()
        await repo.create_instance(
            ChoreInstance(
                id="inst-overdue-001",
                master_chore_id="master-overdue-001",
                period_start=today,
                period_end=today,
                status=InstanceStatus.ACTIVE,
            )
        )

        # Query with time well past 08:00
        overdue = await repo.get_overdue_instances(today, "12:00")
        overdue_ids = [i.id for i in overdue]
        assert "inst-overdue-001" in overdue_ids

        # Query with time before 08:00 — should not be overdue
        not_overdue = await repo.get_overdue_instances(today, "07:00")
        not_overdue_ids = [i.id for i in not_overdue]
        assert "inst-overdue-001" not in not_overdue_ids
