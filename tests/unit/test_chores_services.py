"""Unit tests for chores domain services."""

import pytest

from app.domain.chores.models import (
    InstanceStatus,
    MasterChore,
    MasterChoreStatus,
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


class TestApprovalFlow:
    """Tests for master chore approval logic."""

    @pytest.mark.asyncio
    async def test_adult_creator_auto_approves(self, service: ChoresService) -> None:
        """Test that adult creators auto-approve their master chores."""
        chore = MasterChore(
            id="test-001",
            name="Test Chore",
            category_id="cat-kitchen",
            created_by="faiyaz",
        )

        result = await service.create_master_chore(
            chore=chore,
            tag_ids=[],
            is_adult_creator=True,
        )

        assert result.status == MasterChoreStatus.ACTIVE
        assert result.approved_by == "faiyaz"

    @pytest.mark.asyncio
    async def test_kid_creator_without_approver_pending(self, service: ChoresService) -> None:
        """Test that kid creators without approver get pending status."""
        chore = MasterChore(
            id="test-002",
            name="Test Chore",
            category_id="cat-kitchen",
            created_by="arya",
        )

        result = await service.create_master_chore(
            chore=chore,
            tag_ids=[],
            is_adult_creator=False,
        )

        assert result.status == MasterChoreStatus.PENDING_APPROVAL
        assert result.approved_by is None

    @pytest.mark.asyncio
    async def test_kid_creator_with_approver_auto_approves(self, service: ChoresService) -> None:
        """Test that kid creators with a selected approver auto-approve."""
        chore = MasterChore(
            id="test-003",
            name="Test Chore",
            category_id="cat-kitchen",
            created_by="arya",
        )

        result = await service.create_master_chore(
            chore=chore,
            tag_ids=[],
            is_adult_creator=False,
            approver_id="faiyaz",
        )

        assert result.status == MasterChoreStatus.ACTIVE
        assert result.approved_by == "faiyaz"

    @pytest.mark.asyncio
    async def test_approve_pending_master(self, service: ChoresService) -> None:
        """Test approving a pending master chore."""
        # First create a pending master
        chore = MasterChore(
            id="test-004",
            name="Pending Chore",
            category_id="cat-kitchen",
            created_by="arya",
            status=MasterChoreStatus.PENDING_APPROVAL,
        )
        repo = service.repository
        await repo.create_master_chore(chore, [])

        # Now approve it
        result = await service.approve_master_chore("test-004", "trisha")

        assert result.status == MasterChoreStatus.ACTIVE
        assert result.approved_by == "trisha"

    @pytest.mark.asyncio
    async def test_approve_non_pending_raises(self, service: ChoresService) -> None:
        """Test that approving an already-active master raises ValueError."""
        # The mock adapter has master-001 which is already active
        with pytest.raises(ValueError, match="not pending approval"):
            await service.approve_master_chore("master-001", "faiyaz")

    @pytest.mark.asyncio
    async def test_approve_nonexistent_raises(self, service: ChoresService) -> None:
        """Test that approving a nonexistent master raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await service.approve_master_chore("nonexistent", "faiyaz")


class TestClaimAssignExclusivity:
    """Tests for claim/assign mutual exclusivity."""

    @pytest.mark.asyncio
    async def test_claim_clears_assignment(self, service: ChoresService) -> None:
        """Test that claiming an instance clears assigned_to and assigned_by."""
        # inst-004 is assigned to raya by trisha
        result = await service.claim_instance("inst-004", "arya")

        assert result.claimed_by == "arya"
        assert result.assigned_to is None
        assert result.assigned_by is None

    @pytest.mark.asyncio
    async def test_assign_clears_claim(self, service: ChoresService) -> None:
        """Test that assigning an instance clears claimed_by."""
        # inst-003 is claimed by arya
        result = await service.assign_instance("inst-003", "raya", "trisha")

        assert result.assigned_to == "raya"
        assert result.assigned_by == "trisha"
        assert result.claimed_by is None

    @pytest.mark.asyncio
    async def test_claim_nonexistent_raises(self, service: ChoresService) -> None:
        """Test that claiming a nonexistent instance raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await service.claim_instance("nonexistent", "arya")

    @pytest.mark.asyncio
    async def test_assign_nonexistent_raises(self, service: ChoresService) -> None:
        """Test that assigning a nonexistent instance raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await service.assign_instance("nonexistent", "raya", "trisha")


class TestCompletionSignoff:
    """Tests for completion and signoff flow."""

    @pytest.mark.asyncio
    async def test_adult_completion_immediate(self, service: ChoresService) -> None:
        """Test that adult completion goes straight to completed."""
        # inst-001 is open/active
        result = await service.update_instance_status(
            "inst-001",
            InstanceStatus.COMPLETED,
            actor_id="faiyaz",
            is_adult=True,
        )

        assert result.status == InstanceStatus.COMPLETED
        assert result.completed_by == "faiyaz"
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_kid_completion_pending_signoff(self, service: ChoresService) -> None:
        """Test that kid completion goes to completed_pending_signoff."""
        # inst-002 is open/active
        result = await service.update_instance_status(
            "inst-002",
            InstanceStatus.COMPLETED_PENDING_SIGNOFF,
            actor_id="arya",
            is_adult=False,
        )

        assert result.status == InstanceStatus.COMPLETED_PENDING_SIGNOFF
        assert result.completed_by == "arya"
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_signoff_completes_instance(self, service: ChoresService) -> None:
        """Test that parent signoff transitions to completed."""
        # inst-005 is completed_pending_signoff
        result = await service.signoff_instance("inst-005", "faiyaz")

        assert result.status == InstanceStatus.COMPLETED
        assert result.signoff_by == "faiyaz"
        assert result.signed_off_at is not None

    @pytest.mark.asyncio
    async def test_signoff_non_pending_raises(self, service: ChoresService) -> None:
        """Test that signing off a non-pending instance raises ValueError."""
        # inst-006 is already completed
        with pytest.raises(ValueError, match="not pending signoff"):
            await service.signoff_instance("inst-006", "faiyaz")

    @pytest.mark.asyncio
    async def test_in_progress_sets_started_at(self, service: ChoresService) -> None:
        """Test that setting in_progress records started_at."""
        result = await service.update_instance_status(
            "inst-001",
            InstanceStatus.IN_PROGRESS,
            actor_id="arya",
        )

        assert result.status == InstanceStatus.IN_PROGRESS
        assert result.started_at is not None


class TestGetAllData:
    """Tests for the get_all_data aggregation."""

    @pytest.mark.asyncio
    async def test_get_all_data_structure(self, service: ChoresService) -> None:
        """Test that get_all_data returns the expected structure."""
        data = await service.get_all_data()

        assert "categories" in data
        assert "tags" in data
        assert "master_chores" in data
        assert "instances" in data
        assert isinstance(data["categories"], list)
        assert isinstance(data["tags"], list)
        assert isinstance(data["master_chores"], list)
        assert isinstance(data["instances"], list)

    @pytest.mark.asyncio
    async def test_get_all_data_has_mock_content(self, service: ChoresService) -> None:
        """Test that mock data is populated."""
        data = await service.get_all_data()

        assert len(data["categories"]) == 5  # preset categories
        assert len(data["tags"]) == 5  # sample tags
        assert len(data["master_chores"]) > 0
        assert len(data["instances"]) > 0


class TestCategoryAndTagCRUD:
    """Tests for category and tag creation."""

    @pytest.mark.asyncio
    async def test_create_category(self, service: ChoresService) -> None:
        """Test creating a new category."""
        result = await service.create_category("Pet Care")

        assert result.name == "Pet Care"
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_tag(self, service: ChoresService) -> None:
        """Test creating a new tag."""
        result = await service.create_tag("Urgent")

        assert result.name == "Urgent"
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_get_categories_returns_presets(self, service: ChoresService) -> None:
        """Test that preset categories are returned."""
        categories = await service.get_categories()

        names = {c.name for c in categories}
        assert "Kitchen" in names
        assert "Bathroom" in names
        assert "Outdoor" in names
        assert "Laundry" in names
        assert "General" in names


class TestDeleteMasterChore:
    """Tests for master chore soft-delete."""

    @pytest.mark.asyncio
    async def test_delete_sets_deleted_at(self, service: ChoresService) -> None:
        """Test that delete sets deleted_at and archives the master."""
        await service.delete_master_chore("master-001")

        master = await service.repository.get_master_chore_by_id("master-001")
        assert master is not None
        assert master.deleted_at is not None
        assert master.status == MasterChoreStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_deleted_excluded_from_default_list(self, service: ChoresService) -> None:
        """Test that archived masters are excluded from default listing."""
        await service.delete_master_chore("master-001")

        masters = await service.get_master_chores()
        master_ids = {m.id for m in masters}
        assert "master-001" not in master_ids

    @pytest.mark.asyncio
    async def test_deleted_included_when_requested(self, service: ChoresService) -> None:
        """Test that archived masters are included when include_archived=True."""
        await service.delete_master_chore("master-001")

        masters = await service.get_master_chores(include_archived=True)
        master_ids = {m.id for m in masters}
        assert "master-001" in master_ids
