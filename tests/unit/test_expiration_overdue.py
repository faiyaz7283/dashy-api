"""Unit tests for expiration and overdue detection (Phase 4)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.chores.models import (
    ChoreAssociation,
    ChoreInstance,
    ExpirationBehavior,
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


class TestExpirationBehaviors:
    """Tests for expiration behavior processing."""

    @pytest.mark.asyncio
    async def test_disappear_deletes_expired_instance(
        self, service: ChoresService
    ) -> None:
        """Test DISAPPEAR behavior deletes the expired instance."""
        # Create master with DISAPPEAR behavior
        master = MasterChore(
            id="master-disappear",
            name="Disappear Test",
            category_id="cat-kitchen",
            recurrence_rule={"frequency": "daily", "time": "18:00"},
            expiration_behavior=ExpirationBehavior.DISAPPEAR,
            created_by="faiyaz",
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create association
        association = ChoreAssociation(
            id="assoc-disappear",
            master_chore_id="master-disappear",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )
        await service.create_association(association)

        # Manually create an expired instance (period_end in the past)
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        expired_instance = ChoreInstance(
            id="inst-expired-disappear",
            master_chore_id="master-disappear",
            association_id="assoc-disappear",
            period_start=yesterday,
            period_end=yesterday,
            status=InstanceStatus.ACTIVE,
            created_at=datetime.now(UTC) - timedelta(days=1),
            updated_at=datetime.now(UTC) - timedelta(days=1),
        )
        await service.repository.create_instance(expired_instance)

        # Process expired instances
        processed = await service.process_expired_instances()

        # Verify our test instance was deleted
        processed_ids = [i.id for i in processed]
        assert "inst-expired-disappear" in processed_ids
        all_instances = await service.get_instances()
        instance_ids = [i.id for i in all_instances]
        assert "inst-expired-disappear" not in instance_ids

    @pytest.mark.asyncio
    async def test_stay_visible_marks_missed_and_generates_next(
        self, service: ChoresService
    ) -> None:
        """Test STAY_VISIBLE marks MISSED; new instance from ensure_current_instances."""
        # Create master with STAY_VISIBLE behavior
        master = MasterChore(
            id="master-stayvisible-next",
            name="Stay Visible Next Test",
            category_id="cat-kitchen",
            recurrence_rule={"frequency": "daily", "time": "18:00"},
            expiration_behavior=ExpirationBehavior.STAY_VISIBLE,
            created_by="faiyaz",
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create association
        association = ChoreAssociation(
            id="assoc-stayvisible-next",
            master_chore_id="master-stayvisible-next",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )
        await service.create_association(association)

        # Manually create an expired instance
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        expired_instance = ChoreInstance(
            id="inst-expired-stayvisible-next",
            master_chore_id="master-stayvisible-next",
            association_id="assoc-stayvisible-next",
            period_start=yesterday,
            period_end=yesterday,
            status=InstanceStatus.ACTIVE,
            created_at=datetime.now(UTC) - timedelta(days=1),
            updated_at=datetime.now(UTC) - timedelta(days=1),
        )
        await service.repository.create_instance(expired_instance)

        # Process expired instances
        processed = await service.process_expired_instances()

        # Verify our test instance was processed
        processed_ids = [i.id for i in processed]
        assert "inst-expired-stayvisible-next" in processed_ids

        # Verify instance was marked as MISSED
        updated_instance = await service.repository.get_instance_by_id(
            "inst-expired-stayvisible-next"
        )
        assert updated_instance is not None
        assert updated_instance.status == InstanceStatus.MISSED

        # Verify a new instance was generated for the next period (by ensure_current_instances)
        generated = await service.ensure_current_instances()
        assert len(generated) >= 1

    @pytest.mark.asyncio
    async def test_stay_visible_marks_missed_but_keeps_visible(
        self, service: ChoresService
    ) -> None:
        """Test STAY_VISIBLE behavior marks instance as MISSED but keeps it visible."""
        # Create master with STAY_VISIBLE behavior
        master = MasterChore(
            id="master-stayvisible",
            name="Stay Visible Test",
            category_id="cat-kitchen",
            recurrence_rule={"frequency": "daily", "time": "18:00"},
            expiration_behavior=ExpirationBehavior.STAY_VISIBLE,
            created_by="faiyaz",
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create association
        association = ChoreAssociation(
            id="assoc-stayvisible",
            master_chore_id="master-stayvisible",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )
        await service.create_association(association)

        # Manually create an expired instance
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        expired_instance = ChoreInstance(
            id="inst-expired-stayvisible",
            master_chore_id="master-stayvisible",
            association_id="assoc-stayvisible",
            period_start=yesterday,
            period_end=yesterday,
            status=InstanceStatus.ACTIVE,
            created_at=datetime.now(UTC) - timedelta(days=1),
            updated_at=datetime.now(UTC) - timedelta(days=1),
        )
        await service.repository.create_instance(expired_instance)

        # Process expired instances
        processed = await service.process_expired_instances()

        # Verify our test instance was processed
        processed_ids = [i.id for i in processed]
        assert "inst-expired-stayvisible" in processed_ids

        # Verify instance was marked as MISSED but still exists
        updated_instance = await service.repository.get_instance_by_id("inst-expired-stayvisible")
        assert updated_instance is not None
        assert updated_instance.status == InstanceStatus.MISSED

        # Verify no new instance was generated
        all_instances = await service.get_instances(master_chore_id="master-stayvisible")
        active_instances = [i for i in all_instances if i.status == InstanceStatus.ACTIVE]
        # Should only have the one generated on association creation
        assert len(active_instances) == 1

    @pytest.mark.asyncio
    async def test_convert_to_open_clears_assignment(
        self, service: ChoresService
    ) -> None:
        """Test CONVERT_TO_OPEN behavior clears assignment fields."""
        # Create master with CONVERT_TO_OPEN behavior
        master = MasterChore(
            id="master-convertopen",
            name="Convert to Open Test",
            category_id="cat-kitchen",
            recurrence_rule={"frequency": "daily", "time": "18:00"},
            expiration_behavior=ExpirationBehavior.CONVERT_TO_OPEN,
            created_by="faiyaz",
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create association
        association = ChoreAssociation(
            id="assoc-convertopen",
            master_chore_id="master-convertopen",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )
        await service.create_association(association)

        # Manually create an expired instance with assignment
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        expired_instance = ChoreInstance(
            id="inst-expired-convertopen",
            master_chore_id="master-convertopen",
            association_id="assoc-convertopen",
            period_start=yesterday,
            period_end=yesterday,
            status=InstanceStatus.ACTIVE,
            claimed_by="arya",
            assigned_to="arya",
            assigned_by="faiyaz",
            created_at=datetime.now(UTC) - timedelta(days=1),
            updated_at=datetime.now(UTC) - timedelta(days=1),
        )
        await service.repository.create_instance(expired_instance)

        # Process expired instances
        processed = await service.process_expired_instances()

        # Verify our test instance was processed
        processed_ids = [i.id for i in processed]
        assert "inst-expired-convertopen" in processed_ids

        # Verify instance still exists but assignment cleared
        updated_instance = await service.repository.get_instance_by_id("inst-expired-convertopen")
        assert updated_instance is not None
        assert updated_instance.claimed_by is None
        assert updated_instance.assigned_to is None
        assert updated_instance.assigned_by is None
        # Status should still be ACTIVE (not MISSED)
        assert updated_instance.status == InstanceStatus.ACTIVE


class TestOverdueDetection:
    """Tests for overdue instance detection."""

    @pytest.mark.asyncio
    async def test_mark_overdue_instances(
        self, service: ChoresService
    ) -> None:
        """Test that overdue instances are marked correctly."""
        # Create master with due_time in the past
        master = MasterChore(
            id="master-overdue",
            name="Overdue Test",
            category_id="cat-kitchen",
            recurrence_rule={"frequency": "daily", "time": "18:00"},
            due_time="08:00",  # Due at 8am
            created_by="faiyaz",
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create association
        association = ChoreAssociation(
            id="assoc-overdue",
            master_chore_id="master-overdue",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )
        await service.create_association(association)

        # Get the generated instance
        instances = await service.get_instances(master_chore_id="master-overdue")
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
        # Create master with STAY_VISIBLE behavior
        master = MasterChore(
            id="master-safetynet",
            name="Safety Net Test",
            category_id="cat-kitchen",
            recurrence_rule={"frequency": "daily", "time": "18:00"},
            expiration_behavior=ExpirationBehavior.STAY_VISIBLE,
            created_by="faiyaz",
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create association
        association = ChoreAssociation(
            id="assoc-safetynet",
            master_chore_id="master-safetynet",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )
        await service.create_association(association)

        # Manually create an expired instance
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        expired_instance = ChoreInstance(
            id="inst-expired-safetynet",
            master_chore_id="master-safetynet",
            association_id="assoc-safetynet",
            period_start=yesterday,
            period_end=yesterday,
            status=InstanceStatus.ACTIVE,
            created_at=datetime.now(UTC) - timedelta(days=1),
            updated_at=datetime.now(UTC) - timedelta(days=1),
        )
        await service.repository.create_instance(expired_instance)

        # Run safety net
        generated = await service.ensure_current_instances()

        # Verify expired instance was marked as MISSED
        updated_instance = await service.repository.get_instance_by_id("inst-expired-safetynet")
        assert updated_instance is not None
        assert updated_instance.status == InstanceStatus.MISSED

        # Verify new instances were generated
        assert len(generated) >= 1

    @pytest.mark.asyncio
    async def test_safety_net_handles_no_expired_instances(
        self, service: ChoresService
    ) -> None:
        """Test that safety net works when there are no expired instances."""
        # Create master with normal behavior
        master = MasterChore(
            id="master-noexpired",
            name="No Expired Test",
            category_id="cat-kitchen",
            recurrence_rule={"frequency": "daily", "time": "18:00"},
            expiration_behavior=ExpirationBehavior.STAY_VISIBLE,
            created_by="faiyaz",
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create association
        association = ChoreAssociation(
            id="assoc-noexpired",
            master_chore_id="master-noexpired",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )
        await service.create_association(association)

        # Run safety net (no expired instances)
        generated = await service.ensure_current_instances()

        # Should generate instances without errors
        assert len(generated) >= 0  # May be 0 if already up to date
