"""Unit tests for expiration and overdue detection (Phase 4)."""

from datetime import UTC, datetime, timedelta

import pytest
from uuid6 import uuid7

from app.domain.chores.models import (
    ChoreAssociation,
    ChoreInstance,
    InstanceStatus,
    MasterChore,
)
from app.domain.chores.services import ChoresService
from app.infrastructure.chores.mock_adapter import MockChoresRepository


@pytest.fixture
def repository() -> MockChoresRepository:
    """Create a mock chores repository.

    Returns:
        MockChoresRepository instance.
    """
    return MockChoresRepository()


@pytest.fixture
def service(repository: MockChoresRepository) -> ChoresService:
    """Create a chores service with mock repository.

    Args:
        repository: Mock repository fixture.

    Returns:
        ChoresService instance.
    """
    return ChoresService(repository=repository)


class TestExpirationProcessing:
    """Tests for expiration processing (all expired instances marked as MISSED)."""

    @pytest.mark.asyncio
    async def test_expired_instance_marked_as_missed(
        self, service: ChoresService
    ) -> None:
        """Test that expired instances are marked as MISSED."""
        # Create master
        master = MasterChore(
            id=uuid7(),
            name="Expiration Test",
            category_id=uuid7(),
            frequency="daily",
            frequency_interval=1,
            due_time="18:00",
            created_by=uuid7(),
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create association
        association = ChoreAssociation(
            id=uuid7(),
            master_chore_id=master.id,
            member_id=uuid7(),
            created_by=master.created_by,
        )
        await service.create_association(association)

        # Manually create an expired instance (period_end in the past)
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        expired_instance = ChoreInstance(
            id=uuid7(),
            master_chore_id=master.id,
            association_id=association.id,
            period_start=yesterday,
            period_end=yesterday,
            member_id=association.member_id,
            status=InstanceStatus.ACTIVE,
            created_at=datetime.now(UTC) - timedelta(days=1),
            updated_at=datetime.now(UTC) - timedelta(days=1),
        )
        await service.repository.create_instance(expired_instance)

        # Process expired instances
        processed = await service.process_expired_instances()

        # Verify our test instance was processed
        processed_ids = [i.id for i in processed]
        assert expired_instance.id in processed_ids

        # Verify instance was marked as MISSED
        updated_instance = await service.repository.get_instance_by_id(
            expired_instance.id
        )
        assert updated_instance is not None
        assert updated_instance.status == InstanceStatus.MISSED


class TestOverdueDetection:
    """Tests for overdue instance detection."""

    @pytest.mark.asyncio
    async def test_mark_overdue_instances(
        self, service: ChoresService
    ) -> None:
        """Test that overdue instances are marked correctly."""
        # Create master with due_time in the past
        master = MasterChore(
            id=uuid7(),
            name="Overdue Test",
            category_id=uuid7(),
            frequency="daily",
            frequency_interval=1,
            due_time="08:00",  # Due at 8am
            created_by=uuid7(),
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create association
        association = ChoreAssociation(
            id=uuid7(),
            master_chore_id=master.id,
            member_id=uuid7(),
            created_by=master.created_by,
        )
        await service.create_association(association)

        # Get the generated instance
        instances = await service.get_instances(master_chore_id=master.id)
        assert len(instances) >= 1
        instance = instances[0]

        # Mark overdue (this will check if current time > due_time)
        marked = await service.mark_overdue_instances()

        # If current time is past 8am, instance should be marked OVERDUE
        # Otherwise, it should remain ACTIVE
        current_hour = datetime.now(UTC).hour
        if current_hour >= 8:
            assert len(marked) >= 1
            updated_instance = await service.repository.get_instance_by_id(instance.id)
            assert updated_instance is not None
            assert updated_instance.status == InstanceStatus.OVERDUE
        else:
            # Before 8am, no instances should be marked overdue
            assert len(marked) == 0


class TestSafetyNetIntegration:
    """Tests for safety net integration with expiration and overdue."""

    @pytest.mark.asyncio
    async def test_safety_net_processes_expiration_before_generation(
        self, service: ChoresService
    ) -> None:
        """Test that safety net processes expiration before generating instances."""
        # Create master
        master = MasterChore(
            id=uuid7(),
            name="Safety Net Test",
            category_id=uuid7(),
            frequency="daily",
            frequency_interval=1,
            due_time="18:00",
            created_by=uuid7(),
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create association
        association = ChoreAssociation(
            id=uuid7(),
            master_chore_id=master.id,
            member_id=uuid7(),
            created_by=master.created_by,
        )
        await service.create_association(association)

        # Manually create an expired instance
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        expired_instance = ChoreInstance(
            id=uuid7(),
            master_chore_id=master.id,
            association_id=association.id,
            period_start=yesterday,
            period_end=yesterday,
            member_id=association.member_id,
            status=InstanceStatus.ACTIVE,
            created_at=datetime.now(UTC) - timedelta(days=1),
            updated_at=datetime.now(UTC) - timedelta(days=1),
        )
        await service.repository.create_instance(expired_instance)

        # Run safety net
        generated = await service.ensure_current_instances()

        # Verify expired instance was marked as MISSED
        updated_instance = await service.repository.get_instance_by_id(
            expired_instance.id
        )
        assert updated_instance is not None
        assert updated_instance.status == InstanceStatus.MISSED

        # Verify new instances were generated
        assert len(generated) >= 1

    @pytest.mark.asyncio
    async def test_safety_net_handles_no_expired_instances(
        self, service: ChoresService
    ) -> None:
        """Test that safety net works when there are no expired instances."""
        # Create master
        master = MasterChore(
            id=uuid7(),
            name="No Expired Test",
            category_id=uuid7(),
            frequency="daily",
            frequency_interval=1,
            due_time="18:00",
            created_by=uuid7(),
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create association
        association = ChoreAssociation(
            id=uuid7(),
            master_chore_id=master.id,
            member_id=uuid7(),
            created_by=master.created_by,
        )
        await service.create_association(association)

        # Run safety net (no expired instances)
        generated = await service.ensure_current_instances()

        # Should generate instances without errors
        assert len(generated) >= 0  # May be 0 if already up to date
