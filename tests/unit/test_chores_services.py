"""Unit tests for chores domain services."""

import pytest

from app.domain.chores.models import (
    ChoreAssociation,
    InstanceStatus,
    MasterChore,
    MasterChoreStatus,
)
from app.domain.chores.services import AssociationConflictError, ChoresService
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


class TestMasterChoreCreation:
    """Tests for master chore creation."""

    @pytest.mark.asyncio
    async def test_create_master_chore_active(self, service: ChoresService) -> None:
        """Test that new master chores are created as active."""
        chore = MasterChore(
            id="test-001",
            name="Test Chore",
            category_id="cat-kitchen",
            created_by="faiyaz",
        )

        result = await service.create_master_chore(
            chore=chore,
            tag_ids=[],
        )

        assert result.status == MasterChoreStatus.ACTIVE
        assert result.created_by == "faiyaz"

    @pytest.mark.asyncio
    async def test_create_master_chore_with_tags(self, service: ChoresService) -> None:
        """Test creating a master chore with tags."""
        chore = MasterChore(
            id="test-002",
            name="Tagged Chore",
            category_id="cat-kitchen",
            created_by="trisha",
        )

        result = await service.create_master_chore(
            chore=chore,
            tag_ids=["tag-quick", "tag-physical"],
        )

        assert result.status == MasterChoreStatus.ACTIVE
        assert len(result.tags) == 2


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


class TestInstanceCompletion:
    """Tests for instance completion flow."""

    @pytest.mark.asyncio
    async def test_completion_sets_completed(self, service: ChoresService) -> None:
        """Test that any member can complete an instance."""
        # inst-001 is open/active
        result = await service.update_instance_status(
            "inst-001",
            InstanceStatus.COMPLETED,
            actor_id="arya",
        )

        assert result.status == InstanceStatus.COMPLETED
        assert result.completed_by == "arya"
        assert result.completed_at is not None

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
        assert "associations" in data
        assert "instances" in data
        assert isinstance(data["categories"], list)
        assert isinstance(data["tags"], list)
        assert isinstance(data["master_chores"], list)
        assert isinstance(data["associations"], list)
        assert isinstance(data["instances"], list)

    @pytest.mark.asyncio
    async def test_get_all_data_has_mock_content(self, service: ChoresService) -> None:
        """Test that mock data is populated."""
        data = await service.get_all_data()

        assert len(data["categories"]) == 5  # preset categories
        assert len(data["tags"]) == 5  # sample tags
        assert len(data["master_chores"]) > 0
        assert len(data["associations"]) > 0
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


class TestAssociationValidation:
    """Tests for association collaborative enforcement."""

    @pytest.mark.asyncio
    async def test_create_association_non_collaborative_fails_if_exists(
        self, service: ChoresService
    ) -> None:
        """Test that non-collaborative master rejects second member association."""
        # master-001 already has assoc-001 (arya)
        new_association = ChoreAssociation(
            id="assoc-new",
            master_chore_id="master-001",
            member_id="raya",
            is_open_pool=False,
            created_by="faiyaz",
        )

        with pytest.raises(AssociationConflictError) as exc_info:
            await service.create_association(new_association)

        assert "already has an active member association" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_association_duplicate_member_fails(
        self, service: ChoresService
    ) -> None:
        """Test that same member can't have two associations for same master."""
        # master-001 already has assoc-001 (arya)
        duplicate_association = ChoreAssociation(
            id="assoc-dup",
            master_chore_id="master-001",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )

        with pytest.raises(AssociationConflictError) as exc_info:
            await service.create_association(duplicate_association)

        assert "already has an active association" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_association_collaborative_allows_multiple(
        self, service: ChoresService
    ) -> None:
        """Test that collaborative master allows multiple member associations."""
        # Create a collaborative master
        collaborative_master = MasterChore(
            id="master-collab",
            name="Collaborative Chore",
            category_id="cat-kitchen",
            is_collaborative=True,
            created_by="faiyaz",
        )
        await service.create_master_chore(collaborative_master, tag_ids=[])

        # First association
        assoc1 = ChoreAssociation(
            id="assoc-collab-1",
            master_chore_id="master-collab",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )
        await service.create_association(assoc1)

        # Second association (different member) should succeed
        assoc2 = ChoreAssociation(
            id="assoc-collab-2",
            master_chore_id="master-collab",
            member_id="raya",
            is_open_pool=False,
            created_by="faiyaz",
        )
        result = await service.create_association(assoc2)

        assert result.id == "assoc-collab-2"
        assert result.member_id == "raya"

    @pytest.mark.asyncio
    async def test_create_association_collaborative_duplicate_member_fails(
        self, service: ChoresService
    ) -> None:
        """Test that even collaborative master rejects duplicate member."""
        # Create a collaborative master
        collaborative_master = MasterChore(
            id="master-collab-2",
            name="Collaborative Chore 2",
            category_id="cat-kitchen",
            is_collaborative=True,
            created_by="faiyaz",
        )
        await service.create_master_chore(collaborative_master, tag_ids=[])

        # First association
        assoc1 = ChoreAssociation(
            id="assoc-collab2-1",
            master_chore_id="master-collab-2",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )
        await service.create_association(assoc1)

        # Duplicate member should fail
        duplicate = ChoreAssociation(
            id="assoc-collab2-dup",
            master_chore_id="master-collab-2",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )

        with pytest.raises(AssociationConflictError) as exc_info:
            await service.create_association(duplicate)

        assert "already has an active association" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_open_pool_fails_if_exists(self, service: ChoresService) -> None:
        """Test that only one open pool association per master is allowed."""
        # master-003 already has assoc-002 (open pool)
        new_open_pool = ChoreAssociation(
            id="assoc-open-pool-2",
            master_chore_id="master-003",
            member_id=None,
            is_open_pool=True,
            created_by="faiyaz",
        )

        with pytest.raises(AssociationConflictError) as exc_info:
            await service.create_association(new_open_pool)

        assert "already has an open pool association" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_association_master_not_found(self, service: ChoresService) -> None:
        """Test that association with non-existent master raises ValueError."""
        association = ChoreAssociation(
            id="assoc-bad",
            master_chore_id="master-nonexistent",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )

        with pytest.raises(ValueError, match="not found"):
            await service.create_association(association)

    @pytest.mark.asyncio
    async def test_create_association_master_not_active(self, service: ChoresService) -> None:
        """Test that association with inactive master raises ValueError."""
        # Archive master-001
        await service.delete_master_chore("master-001")

        association = ChoreAssociation(
            id="assoc-inactive",
            master_chore_id="master-001",
            member_id="raya",
            is_open_pool=False,
            created_by="faiyaz",
        )

        with pytest.raises(ValueError, match="not active"):
            await service.create_association(association)


class TestDeleteAssociationCascade:
    """Tests for association deletion and instance archival."""

    @pytest.mark.asyncio
    async def test_delete_association_archives_instances(
        self, service: ChoresService
    ) -> None:
        """Test that deleting association archives its active instances."""
        # assoc-001 has inst-001 (ACTIVE) and inst-006 (COMPLETED)
        archived_count = await service.delete_association("assoc-001")

        # Only ACTIVE/IN_PROGRESS instances should be archived
        assert archived_count == 1

        # Verify inst-001 is archived
        inst_001 = await service.repository.get_instance_by_id("inst-001")
        assert inst_001 is not None
        assert inst_001.status == InstanceStatus.ARCHIVED

        # Verify inst-006 is still completed (not affected)
        inst_006 = await service.repository.get_instance_by_id("inst-006")
        assert inst_006 is not None
        assert inst_006.status == InstanceStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_delete_association_soft_deletes(
        self, service: ChoresService
    ) -> None:
        """Test that delete sets removed_at on association."""
        await service.delete_association("assoc-001")

        # Association should still exist but have removed_at set
        association = await service.repository.get_association("assoc-001")
        assert association is not None
        assert association.removed_at is not None

    @pytest.mark.asyncio
    async def test_delete_association_not_found(self, service: ChoresService) -> None:
        """Test that deleting non-existent association raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await service.delete_association("assoc-nonexistent")

    @pytest.mark.asyncio
    async def test_delete_association_no_instances(self, service: ChoresService) -> None:
        """Test that deleting association with no instances succeeds."""
        # Create a new association with no instances
        new_association = ChoreAssociation(
            id="assoc-no-instances",
            master_chore_id="master-005",
            member_id="arya",
            is_open_pool=False,
            created_by="faiyaz",
        )
        await service.create_association(new_association)

        # Delete should succeed with 0 archived
        archived_count = await service.delete_association("assoc-no-instances")
        assert archived_count == 0

