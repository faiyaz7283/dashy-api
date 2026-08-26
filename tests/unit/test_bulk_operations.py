"""Unit tests for bulk operations (Phase 6)."""

import pytest

from app.domain.chores.models import MasterChore, MasterChoreStatus
from app.domain.chores.services import ChoresService
from app.infrastructure.chores.mock_adapter import MockChoresRepository


@pytest.fixture
def repository():
    """Create a mock repository for testing."""
    return MockChoresRepository()


@pytest.fixture
def service(repository):
    """Create a chores service with mock repository."""
    return ChoresService(repository)


class TestBulkUpdateMasterStatus:
    """Test bulk status updates for master chores."""

    async def test_bulk_update_single_master(self, service: ChoresService):
        """Test updating status of a single master."""
        # Create a master chore
        master = MasterChore(
            id="test-master-1",
            name="Test Chore",
            category_id="test-category",
            created_by="test-user",
        )
        created = await service.create_master_chore(master, tag_ids=[])

        # Update status to inactive
        updated_count = await service.bulk_update_master_status(
            [created.id], MasterChoreStatus.INACTIVE
        )

        assert updated_count == 1

        # Verify the status was updated
        updated_master = await service.repository.get_master_chore_by_id(created.id)
        assert updated_master.status == MasterChoreStatus.INACTIVE

    async def test_bulk_update_multiple_masters(self, service: ChoresService):
        """Test updating status of multiple masters at once."""
        # Create multiple master chores
        master1 = MasterChore(
            id="test-master-1",
            name="Chore 1",
            category_id="test-category",
            created_by="test-user",
        )
        master2 = MasterChore(
            id="test-master-2",
            name="Chore 2",
            category_id="test-category",
            created_by="test-user",
        )
        master3 = MasterChore(
            id="test-master-3",
            name="Chore 3",
            category_id="test-category",
            created_by="test-user",
        )

        created1 = await service.create_master_chore(master1, tag_ids=[])
        created2 = await service.create_master_chore(master2, tag_ids=[])
        created3 = await service.create_master_chore(master3, tag_ids=[])

        # Update all to inactive
        updated_count = await service.bulk_update_master_status(
            [created1.id, created2.id, created3.id], MasterChoreStatus.INACTIVE
        )

        assert updated_count == 3

        # Verify all were updated
        for master_id in [created1.id, created2.id, created3.id]:
            updated_master = await service.repository.get_master_chore_by_id(master_id)
            assert updated_master.status == MasterChoreStatus.INACTIVE

    async def test_bulk_update_partial_match(self, service: ChoresService):
        """Test updating with some non-existent IDs."""
        # Create one master
        master = MasterChore(
            id="test-master-1",
            name="Test Chore",
            category_id="test-category",
            created_by="test-user",
        )
        created = await service.create_master_chore(master, tag_ids=[])

        # Try to update existing and non-existing masters
        updated_count = await service.bulk_update_master_status(
            [created.id, "non-existent-id"], MasterChoreStatus.INACTIVE
        )

        # Should only update the one that exists
        assert updated_count == 1

        # Verify the existing one was updated
        updated_master = await service.repository.get_master_chore_by_id(created.id)
        assert updated_master.status == MasterChoreStatus.INACTIVE

    async def test_bulk_update_empty_list(self, service: ChoresService):
        """Test updating with empty list of IDs."""
        updated_count = await service.bulk_update_master_status(
            [], MasterChoreStatus.INACTIVE
        )

        assert updated_count == 0

    async def test_bulk_update_resume_from_inactive(self, service: ChoresService):
        """Test resuming masters from inactive to active."""
        # Create and set to inactive
        master = MasterChore(
            id="test-master-1",
            name="Test Chore",
            category_id="test-category",
            created_by="test-user",
        )
        created = await service.create_master_chore(master, tag_ids=[])
        await service.bulk_update_master_status([created.id], MasterChoreStatus.INACTIVE)

        # Resume to active
        updated_count = await service.bulk_update_master_status(
            [created.id], MasterChoreStatus.ACTIVE
        )

        assert updated_count == 1

        # Verify it's active again
        updated_master = await service.repository.get_master_chore_by_id(created.id)
        assert updated_master.status == MasterChoreStatus.ACTIVE

    async def test_bulk_update_to_archived(self, service: ChoresService):
        """Test archiving multiple masters."""
        # Create multiple masters
        master1 = MasterChore(
            id="test-master-1",
            name="Chore 1",
            category_id="test-category",
            created_by="test-user",
        )
        master2 = MasterChore(
            id="test-master-2",
            name="Chore 2",
            category_id="test-category",
            created_by="test-user",
        )

        created1 = await service.create_master_chore(master1, tag_ids=[])
        created2 = await service.create_master_chore(master2, tag_ids=[])

        # Archive both
        updated_count = await service.bulk_update_master_status(
            [created1.id, created2.id], MasterChoreStatus.ARCHIVED
        )

        assert updated_count == 2

        # Verify both are archived
        for master_id in [created1.id, created2.id]:
            updated_master = await service.repository.get_master_chore_by_id(master_id)
            assert updated_master.status == MasterChoreStatus.ARCHIVED
