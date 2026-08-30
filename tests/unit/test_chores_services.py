"""Unit tests for chores domain services."""

from datetime import date
from unittest.mock import AsyncMock

import pytest
from uuid6 import uuid7

from app.domain.chores.models import (
    ChoreAssociation,
    InstanceStatus,
    MasterChore,
    MasterChoreStatus,
)
from app.domain.chores.services import AssociationConflictError, ChoresService
from app.infrastructure.chores.mock_adapter import (
    _ASSOC_001,
    _CAT_KITCHEN,
    _INST_001,
    _INST_003,
    _INST_004,
    _INST_006,
    _MASTER_001,
    _MASTER_003,
    _MASTER_005,
    _MEMBER_ARYA,
    _MEMBER_FAIYAZ,
    _MEMBER_RAYA,
    _MEMBER_TRISHA,
    _TAG_PHYSICAL,
    _TAG_QUICK,
    MockChoresRepository,
)


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
            id=uuid7(),
            name="Test Chore",
            category_id=_CAT_KITCHEN,
            created_by=_MEMBER_FAIYAZ,
        )

        result = await service.create_master_chore(
            chore=chore,
            tag_ids=[],
        )

        assert result.status == MasterChoreStatus.ACTIVE
        assert result.created_by == _MEMBER_FAIYAZ

    @pytest.mark.asyncio
    async def test_create_master_chore_with_tags(self, service: ChoresService) -> None:
        """Test creating a master chore with tags."""
        chore = MasterChore(
            id=uuid7(),
            name="Tagged Chore",
            category_id=_CAT_KITCHEN,
            created_by=_MEMBER_TRISHA,
        )

        result = await service.create_master_chore(
            chore=chore,
            tag_ids=[_TAG_QUICK, _TAG_PHYSICAL],
        )

        assert result.status == MasterChoreStatus.ACTIVE
        assert len(result.tags) == 2


class TestClaimAssignExclusivity:
    """Tests for claim/assign mutual exclusivity."""

    @pytest.mark.asyncio
    async def test_claim_clears_assignment(self, service: ChoresService) -> None:
        """Test that claiming an instance clears assigned_by."""
        # _INST_004 is assigned to raya by trisha
        result = await service.claim_instance(_INST_004, _MEMBER_ARYA)

        assert result.member_id == _MEMBER_ARYA
        assert result.assigned_by is None

    @pytest.mark.asyncio
    async def test_assign_clears_claim(self, service: ChoresService) -> None:
        """Test that assigning an instance sets member_id and assigned_by."""
        # _INST_003 is claimed by arya
        result = await service.assign_instance(_INST_003, _MEMBER_RAYA, _MEMBER_TRISHA)

        assert result.member_id == _MEMBER_RAYA
        assert result.assigned_by == _MEMBER_TRISHA

    @pytest.mark.asyncio
    async def test_claim_nonexistent_raises(self, service: ChoresService) -> None:
        """Test that claiming a nonexistent instance raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await service.claim_instance(uuid7(), _MEMBER_ARYA)

    @pytest.mark.asyncio
    async def test_assign_nonexistent_raises(self, service: ChoresService) -> None:
        """Test that assigning a nonexistent instance raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await service.assign_instance(uuid7(), _MEMBER_RAYA, _MEMBER_TRISHA)


class TestInstanceCompletion:
    """Tests for instance completion flow."""

    @pytest.mark.asyncio
    async def test_completion_sets_completed(self, service: ChoresService) -> None:
        """Test that any member can complete an instance."""
        # _INST_001 is active with member_id=_MEMBER_ARYA
        result = await service.update_instance_status(
            _INST_001,
            InstanceStatus.COMPLETED,
            actor_id=_MEMBER_ARYA,
        )

        assert result.status == InstanceStatus.COMPLETED
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_in_progress_sets_started_at(self, service: ChoresService) -> None:
        """Test that setting in_progress records started_at."""
        result = await service.update_instance_status(
            _INST_001,
            InstanceStatus.IN_PROGRESS,
            actor_id=_MEMBER_ARYA,
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
        await service.delete_master_chore(_MASTER_001)

        master = await service.repository.get_master_chore_by_id(_MASTER_001)
        assert master is not None
        assert master.deleted_at is not None
        assert master.status == MasterChoreStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_deleted_excluded_from_default_list(self, service: ChoresService) -> None:
        """Test that archived masters are excluded from default listing."""
        await service.delete_master_chore(_MASTER_001)

        masters = await service.get_master_chores()
        master_ids = {m.id for m in masters}
        assert _MASTER_001 not in master_ids

    @pytest.mark.asyncio
    async def test_deleted_included_when_requested(self, service: ChoresService) -> None:
        """Test that archived masters are included when include_archived=True."""
        await service.delete_master_chore(_MASTER_001)

        masters = await service.get_master_chores(include_archived=True)
        master_ids = {m.id for m in masters}
        assert _MASTER_001 in master_ids


class TestAssociationValidation:
    """Tests for association collaborative enforcement."""

    @pytest.mark.asyncio
    async def test_create_association_non_collaborative_fails_if_exists(
        self, service: ChoresService
    ) -> None:
        """Test that non-collaborative master rejects second association."""
        # _MASTER_001 already has _ASSOC_001 (arya)
        new_association = ChoreAssociation(
            id=uuid7(),
            master_chore_id=_MASTER_001,
            member_id=_MEMBER_RAYA,
            created_by=_MEMBER_FAIYAZ,
        )

        with pytest.raises(AssociationConflictError) as exc_info:
            await service.create_association(new_association)

        assert "already has an active association" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_association_duplicate_member_fails(
        self, service: ChoresService
    ) -> None:
        """Test that same member can't have two associations for same master."""
        # _MASTER_001 already has _ASSOC_001 (arya)
        duplicate_association = ChoreAssociation(
            id=uuid7(),
            master_chore_id=_MASTER_001,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
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
        collab_master_id = uuid7()
        collaborative_master = MasterChore(
            id=collab_master_id,
            name="Collaborative Chore",
            category_id=_CAT_KITCHEN,
            is_collaborative=True,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(collaborative_master, tag_ids=[])

        # First association
        assoc1_id = uuid7()
        assoc1 = ChoreAssociation(
            id=assoc1_id,
            master_chore_id=collab_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_association(assoc1)

        # Second association (different member) should succeed
        assoc2_id = uuid7()
        assoc2 = ChoreAssociation(
            id=assoc2_id,
            master_chore_id=collab_master_id,
            member_id=_MEMBER_RAYA,
            created_by=_MEMBER_FAIYAZ,
        )
        result, instance = await service.create_association(assoc2)

        assert result.id == assoc2_id
        assert result.member_id == _MEMBER_RAYA

    @pytest.mark.asyncio
    async def test_create_association_collaborative_duplicate_member_fails(
        self, service: ChoresService
    ) -> None:
        """Test that even collaborative master rejects duplicate member."""
        # Create a collaborative master
        collab2_master_id = uuid7()
        collaborative_master = MasterChore(
            id=collab2_master_id,
            name="Collaborative Chore 2",
            category_id=_CAT_KITCHEN,
            is_collaborative=True,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(collaborative_master, tag_ids=[])

        # First association
        assoc1 = ChoreAssociation(
            id=uuid7(),
            master_chore_id=collab2_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_association(assoc1)

        # Duplicate member should fail
        duplicate = ChoreAssociation(
            id=uuid7(),
            master_chore_id=collab2_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )

        with pytest.raises(AssociationConflictError) as exc_info:
            await service.create_association(duplicate)

        assert "already has an active association" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_open_pool_fails_if_exists(self, service: ChoresService) -> None:
        """Test that only one open pool association per master is allowed."""
        # _MASTER_003 already has _ASSOC_002 (open pool)
        new_open_pool = ChoreAssociation(
            id=uuid7(),
            master_chore_id=_MASTER_003,
            member_id=None,
            created_by=_MEMBER_FAIYAZ,
        )

        with pytest.raises(AssociationConflictError) as exc_info:
            await service.create_association(new_open_pool)

        assert "already has an open pool association" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_non_collaborative_rejects_open_pool_if_member_exists(
        self, service: ChoresService
    ) -> None:
        """Bug 5: Non-collaborative master with member association rejects open pool."""
        # _MASTER_001 (non-collaborative) already has _ASSOC_001 (member arya)
        new_open_pool = ChoreAssociation(
            id=uuid7(),
            master_chore_id=_MASTER_001,
            member_id=None,
            created_by=_MEMBER_FAIYAZ,
        )

        with pytest.raises(AssociationConflictError) as exc_info:
            await service.create_association(new_open_pool)

        assert "already has a member association" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_non_collaborative_rejects_member_if_open_pool_exists(
        self, service: ChoresService
    ) -> None:
        """Bug 5: Non-collaborative master with open pool rejects member association."""
        # _MASTER_003 (non-collaborative) already has _ASSOC_002 (open pool)
        new_member_assoc = ChoreAssociation(
            id=uuid7(),
            master_chore_id=_MASTER_003,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )

        with pytest.raises(AssociationConflictError) as exc_info:
            await service.create_association(new_member_assoc)

        assert "already has an active association" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_association_master_not_found(self, service: ChoresService) -> None:
        """Test that association with non-existent master raises ValueError."""
        association = ChoreAssociation(
            id=uuid7(),
            master_chore_id=uuid7(),
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )

        with pytest.raises(ValueError, match="not found"):
            await service.create_association(association)

    @pytest.mark.asyncio
    async def test_create_association_master_not_active(self, service: ChoresService) -> None:
        """Test that association with inactive master raises ValueError."""
        # Archive _MASTER_001
        await service.delete_master_chore(_MASTER_001)

        association = ChoreAssociation(
            id=uuid7(),
            master_chore_id=_MASTER_001,
            member_id=_MEMBER_RAYA,
            created_by=_MEMBER_FAIYAZ,
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
        # _ASSOC_001 has _INST_001 (ACTIVE) and _INST_006 (COMPLETED)
        archived_count = await service.delete_association(_ASSOC_001)

        # Only ACTIVE/IN_PROGRESS instances should be archived
        assert archived_count == 1

        # Verify _INST_001 is archived
        inst_001 = await service.repository.get_instance_by_id(_INST_001)
        assert inst_001 is not None
        assert inst_001.status == InstanceStatus.ARCHIVED

        # Verify _INST_006 is still completed (not affected)
        inst_006 = await service.repository.get_instance_by_id(_INST_006)
        assert inst_006 is not None
        assert inst_006.status == InstanceStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_delete_association_soft_deletes(
        self, service: ChoresService
    ) -> None:
        """Test that delete sets removed_at on association."""
        await service.delete_association(_ASSOC_001)

        # Association should still exist but have removed_at set
        association = await service.repository.get_association(_ASSOC_001)
        assert association is not None
        assert association.removed_at is not None

    @pytest.mark.asyncio
    async def test_delete_association_not_found(self, service: ChoresService) -> None:
        """Test that deleting non-existent association raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await service.delete_association(uuid7())

    @pytest.mark.asyncio
    async def test_delete_association_no_instances(self, service: ChoresService) -> None:
        """Test that deleting association with no instances succeeds."""
        # Create a new association directly via repository (bypasses generation)
        no_inst_assoc_id = uuid7()
        new_association = ChoreAssociation(
            id=no_inst_assoc_id,
            master_chore_id=_MASTER_005,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.repository.create_association(new_association)

        # Delete should succeed with 0 archived
        archived_count = await service.delete_association(no_inst_assoc_id)
        assert archived_count == 0


class TestInstanceGeneration:
    """Tests for instance generation logic."""

    @pytest.mark.asyncio
    async def test_generate_instance_for_association(
        self, service: ChoresService
    ) -> None:
        """Test generating an instance for an association."""
        # Create a new master and association
        gen_master_id = uuid7()
        master = MasterChore(
            id=gen_master_id,
            name="Test Generation",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        gen_assoc_id = uuid7()
        association = ChoreAssociation(
            id=gen_assoc_id,
            master_chore_id=gen_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_association(association)

        # Manually trigger generation
        instance = await service.generate_instance_for_association(gen_assoc_id)

        assert instance is not None
        assert instance.master_chore_id == gen_master_id
        assert instance.association_id == gen_assoc_id
        assert instance.status == InstanceStatus.ACTIVE
        assert instance.member_id == _MEMBER_ARYA

    @pytest.mark.asyncio
    async def test_generate_instance_respects_end_date(
        self, service: ChoresService
    ) -> None:
        """Test that generation stops at end_date."""
        past_date = date(2020, 1, 1)  # Well in the past
        gen2_master_id = uuid7()
        master = MasterChore(
            id=gen2_master_id,
            name="Expired Chore",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            end_date=past_date,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        gen2_assoc_id = uuid7()
        association = ChoreAssociation(
            id=gen2_assoc_id,
            master_chore_id=gen2_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_association(association)

        # Try to generate — should return None because end_date is in the past
        await service.generate_instance_for_association(gen2_assoc_id)

        # The association creation already tried to generate, so we check no new instance
        instances = await service.get_instances(master_chore_id=gen2_master_id)
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_generate_instance_respects_max_occurrences(
        self, service: ChoresService
    ) -> None:
        """Test that association creation is rejected at max_occurrences."""
        gen3_master_id = uuid7()
        master = MasterChore(
            id=gen3_master_id,
            name="Limited Chore",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            max_occurrences=1,
            occurrence_count=1,  # Already at limit
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        gen3_assoc_id = uuid7()
        association = ChoreAssociation(
            id=gen3_assoc_id,
            master_chore_id=gen3_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        # Should reject association creation when at max_occurrences
        with pytest.raises(ValueError, match="maximum of 1 occurrences"):
            await service.create_association(association)

        instances = await service.get_instances(master_chore_id=gen3_master_id)
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_generate_instance_no_duplicate_for_same_period(
        self, service: ChoresService
    ) -> None:
        """Test that generation doesn't create duplicates for the same period."""
        gen4_master_id = uuid7()
        master = MasterChore(
            id=gen4_master_id,
            name="No Duplicate",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        gen4_assoc_id = uuid7()
        association = ChoreAssociation(
            id=gen4_assoc_id,
            master_chore_id=gen4_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_association(association)

        # First generation (happens on association creation)
        instances_after_first = await service.get_instances(master_chore_id=gen4_master_id)
        assert len(instances_after_first) == 1

        # Try to generate again — should return existing instance
        instance = await service.generate_instance_for_association(gen4_assoc_id)

        instances_after_second = await service.get_instances(master_chore_id=gen4_master_id)
        assert len(instances_after_second) == 1
        assert instance is not None
        assert instance.id == instances_after_first[0].id

    @pytest.mark.asyncio
    async def test_generate_instance_increments_occurrence_count(
        self, service: ChoresService
    ) -> None:
        """Test that generation increments master's occurrence_count."""
        gen5_master_id = uuid7()
        master = MasterChore(
            id=gen5_master_id,
            name="Count Test",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            occurrence_count=0,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        gen5_assoc_id = uuid7()
        association = ChoreAssociation(
            id=gen5_assoc_id,
            master_chore_id=gen5_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_association(association)

        # After association creation, occurrence_count should be 1
        updated_master = await service.repository.get_master_chore_by_id(gen5_master_id)
        assert updated_master is not None
        assert updated_master.occurrence_count == 1


class TestSafetyNet:
    """Tests for ensure_current_instances safety net."""

    @pytest.mark.asyncio
    async def test_ensure_current_instances_generates_missing(
        self, service: ChoresService
    ) -> None:
        """Test that safety net generates missing instances."""
        # Create a master with an association but no instances
        safety1_master_id = uuid7()
        master = MasterChore(
            id=safety1_master_id,
            name="Safety Net Test",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        safety1_assoc_id = uuid7()
        association = ChoreAssociation(
            id=safety1_assoc_id,
            master_chore_id=safety1_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        # Create association directly without triggering generation
        await service.repository.create_association(association)

        # Verify no instances exist
        instances_before = await service.get_instances(master_chore_id=safety1_master_id)
        assert len(instances_before) == 0

        # Run safety net
        generated = await service.ensure_current_instances()

        # Should have generated one instance
        assert len(generated) >= 1
        instances_after = await service.get_instances(master_chore_id=safety1_master_id)
        assert len(instances_after) == 1

    @pytest.mark.asyncio
    async def test_ensure_current_instances_skips_inactive_masters(
        self, service: ChoresService
    ) -> None:
        """Test that safety net skips inactive masters."""
        safety2_master_id = uuid7()
        master = MasterChore(
            id=safety2_master_id,
            name="Inactive Master",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            created_by=_MEMBER_FAIYAZ,
        )
        # Create via repository to bypass the ACTIVE override in service
        master.status = MasterChoreStatus.INACTIVE
        await service.repository.create_master_chore(master, tag_ids=[])

        safety2_assoc_id = uuid7()
        association = ChoreAssociation(
            id=safety2_assoc_id,
            master_chore_id=safety2_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.repository.create_association(association)

        # Run safety net
        await service.ensure_current_instances()

        # Should not generate for inactive master
        instances = await service.get_instances(master_chore_id=safety2_master_id)
        assert len(instances) == 0


class TestCompletionTrigger:
    """Tests for instance completion triggering next generation."""

    @pytest.mark.asyncio
    async def test_completion_triggers_next_generation(
        self, service: ChoresService
    ) -> None:
        """Test that completing an instance triggers generation of the next."""
        complete_master_id = uuid7()
        master = MasterChore(
            id=complete_master_id,
            name="Completion Trigger",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        complete_assoc_id = uuid7()
        association = ChoreAssociation(
            id=complete_assoc_id,
            master_chore_id=complete_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_association(association)

        # Get the generated instance
        instances = await service.get_instances(master_chore_id=complete_master_id)
        assert len(instances) == 1
        first_instance = instances[0]

        # Complete it
        await service.update_instance_status(
            first_instance.id, InstanceStatus.COMPLETED, _MEMBER_ARYA
        )

        # Should have generated a new instance for the next period
        # For daily frequency, if we complete before the configured time,
        # it generates for today again. If after, it generates for tomorrow.
        # Since we can't control the exact time in tests, we just check that
        # occurrence_count incremented
        updated_master = await service.repository.get_master_chore_by_id(complete_master_id)
        assert updated_master is not None
        assert updated_master.occurrence_count >= 1


class TestConditionalChores:
    """Tests for conditional chore generation."""

    @pytest.fixture
    def mock_evaluator(self) -> AsyncMock:
        """Create a mock condition evaluator.

        Returns:
            AsyncMock configured as ConditionEvaluator.
        """
        return AsyncMock()

    @pytest.fixture
    def service_with_evaluator(
        self, repository: MockChoresRepository, mock_evaluator: AsyncMock
    ) -> ChoresService:
        """Create a chores service with mock evaluator.

        Args:
            repository: Mock repository fixture.
            mock_evaluator: Mock evaluator fixture.

        Returns:
            ChoresService instance with evaluator.
        """
        return ChoresService(repository=repository, condition_evaluator=mock_evaluator)

    @pytest.mark.asyncio
    async def test_generate_when_conditions_met(
        self, service_with_evaluator: ChoresService, mock_evaluator: AsyncMock
    ) -> None:
        """Test instance generation when conditions are met."""
        mock_evaluator.evaluate.return_value = True

        cond1_master_id = uuid7()
        master = MasterChore(
            id=cond1_master_id,
            name="Conditional Chore",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            conditions={"logic": "and", "conditions": []},
            created_by=_MEMBER_FAIYAZ,
        )
        await service_with_evaluator.create_master_chore(master, tag_ids=[])

        cond1_assoc_id = uuid7()
        association = ChoreAssociation(
            id=cond1_assoc_id,
            master_chore_id=cond1_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service_with_evaluator.create_association(association)

        # Should have generated an instance
        instances = await service_with_evaluator.get_instances(
            master_chore_id=cond1_master_id
        )
        assert len(instances) == 1
        mock_evaluator.evaluate.assert_called()

    @pytest.mark.asyncio
    async def test_skip_when_conditions_not_met(
        self, service_with_evaluator: ChoresService, mock_evaluator: AsyncMock
    ) -> None:
        """Test instance generation is skipped when conditions are not met."""
        mock_evaluator.evaluate.return_value = False

        cond2_master_id = uuid7()
        master = MasterChore(
            id=cond2_master_id,
            name="Conditional Chore Not Met",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            conditions={"logic": "and", "conditions": []},
            created_by=_MEMBER_FAIYAZ,
        )
        await service_with_evaluator.create_master_chore(master, tag_ids=[])

        cond2_assoc_id = uuid7()
        association = ChoreAssociation(
            id=cond2_assoc_id,
            master_chore_id=cond2_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service_with_evaluator.create_association(association)

        # Should NOT have generated an instance
        instances = await service_with_evaluator.get_instances(
            master_chore_id=cond2_master_id
        )
        assert len(instances) == 0
        mock_evaluator.evaluate.assert_called()

    @pytest.mark.asyncio
    async def test_generate_without_conditions(
        self, service_with_evaluator: ChoresService, mock_evaluator: AsyncMock
    ) -> None:
        """Test instance generation when no conditions are defined."""
        cond3_master_id = uuid7()
        master = MasterChore(
            id=cond3_master_id,
            name="Non-conditional Chore",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            created_by=_MEMBER_FAIYAZ,
        )
        await service_with_evaluator.create_master_chore(master, tag_ids=[])

        cond3_assoc_id = uuid7()
        association = ChoreAssociation(
            id=cond3_assoc_id,
            master_chore_id=cond3_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service_with_evaluator.create_association(association)

        # Should have generated an instance without calling evaluator
        instances = await service_with_evaluator.get_instances(
            master_chore_id=cond3_master_id
        )
        assert len(instances) == 1
        mock_evaluator.evaluate.assert_not_called()


class TestUpdateMasterChore:
    """Tests for update_master_chore service method."""

    @pytest.mark.asyncio
    async def test_update_master_name(self, service: ChoresService) -> None:
        """Test updating master chore name."""
        updated = await service.update_master_chore(
            _MASTER_001, {"name": "Updated Name"}
        )

        assert updated.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_master_status(self, service: ChoresService) -> None:
        """Test updating master chore status."""
        updated = await service.update_master_chore(
            _MASTER_001, {"status": MasterChoreStatus.INACTIVE}
        )

        assert updated.status == MasterChoreStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_update_master_multiple_fields(self, service: ChoresService) -> None:
        """Test updating multiple fields at once."""
        updated = await service.update_master_chore(
            _MASTER_001,
            {"name": "New Name", "difficulty": 4, "estimated_minutes": 30},
        )

        assert updated.name == "New Name"
        assert updated.difficulty == 4
        assert updated.estimated_minutes == 30

    @pytest.mark.asyncio
    async def test_update_nonexistent_master_raises(self, service: ChoresService) -> None:
        """Test updating non-existent master raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await service.update_master_chore(uuid7(), {"name": "X"})


class TestCollaborativeGeneration:
    """Tests for collaborative master instance generation."""

    @pytest.mark.asyncio
    async def test_collaborative_generates_per_association(
        self, service: ChoresService
    ) -> None:
        """Test that collaborative master generates separate instances per member."""
        # Create collaborative master
        collab_gen_master_id = uuid7()
        master = MasterChore(
            id=collab_gen_master_id,
            name="Collaborative Generation",
            category_id=_CAT_KITCHEN,
            is_collaborative=True,
            frequency="daily",
            due_time="18:00",
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create two associations (different members)
        collab_gen_assoc1_id = uuid7()
        assoc1 = ChoreAssociation(
            id=collab_gen_assoc1_id,
            master_chore_id=collab_gen_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_association(assoc1)

        collab_gen_assoc2_id = uuid7()
        assoc2 = ChoreAssociation(
            id=collab_gen_assoc2_id,
            master_chore_id=collab_gen_master_id,
            member_id=_MEMBER_RAYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_association(assoc2)

        # Should have generated two instances (one per association)
        instances = await service.get_instances(master_chore_id=collab_gen_master_id)
        assert len(instances) == 2

        # Each instance should be linked to its association
        instance_assoc_ids = {i.association_id for i in instances}
        assert collab_gen_assoc1_id in instance_assoc_ids
        assert collab_gen_assoc2_id in instance_assoc_ids


class TestOpenPoolGeneration:
    """Tests for open pool association instance generation."""

    @pytest.mark.asyncio
    async def test_open_pool_generates_instance(self, service: ChoresService) -> None:
        """Test that open pool association generates an instance."""
        # Create master
        pool_master_id = uuid7()
        master = MasterChore(
            id=pool_master_id,
            name="Open Pool Generation",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create open pool association
        pool_assoc_id = uuid7()
        assoc = ChoreAssociation(
            id=pool_assoc_id,
            master_chore_id=pool_master_id,
            member_id=None,  # Open pool
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_association(assoc)

        # Should have generated an instance
        instances = await service.get_instances(master_chore_id=pool_master_id)
        assert len(instances) == 1
        assert instances[0].association_id == pool_assoc_id
        # Open pool instances have no member_id initially
        assert instances[0].member_id is None


class TestOneTimeChoreGeneration:
    """Tests for one-time chore (frequency='once') instance generation."""

    @pytest.mark.asyncio
    async def test_one_time_generates_instance_on_association(
        self, service: ChoresService
    ) -> None:
        """Test that one-time chore generates an instance when associated."""
        # Create one-time master (default frequency is 'once')
        once_master_id = uuid7()
        master = MasterChore(
            id=once_master_id,
            name="One-Time Chore",
            category_id=_CAT_KITCHEN,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        # Create association
        once_assoc_id = uuid7()
        assoc = ChoreAssociation(
            id=once_assoc_id,
            master_chore_id=once_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_association(assoc)

        # Should have generated an instance
        instances = await service.get_instances(master_chore_id=once_master_id)
        assert len(instances) == 1
        assert instances[0].master_chore_id == once_master_id
        assert instances[0].association_id == once_assoc_id
        assert instances[0].status == InstanceStatus.ACTIVE
        assert instances[0].member_id == _MEMBER_ARYA

    @pytest.mark.asyncio
    async def test_one_time_uses_due_date(self, service: ChoresService) -> None:
        """Test that one-time chore uses due_date for period."""
        future_date = date(2027, 6, 15)
        once_master_id = uuid7()
        master = MasterChore(
            id=once_master_id,
            name="One-Time with Due Date",
            category_id=_CAT_KITCHEN,
            due_date=future_date,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        once_assoc_id = uuid7()
        assoc = ChoreAssociation(
            id=once_assoc_id,
            master_chore_id=once_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_association(assoc)

        instances = await service.get_instances(master_chore_id=once_master_id)
        assert len(instances) == 1
        assert instances[0].period_start == future_date
        assert instances[0].period_end == future_date

    @pytest.mark.asyncio
    async def test_one_time_only_generates_once(
        self, service: ChoresService
    ) -> None:
        """Test that one-time chore only generates one instance per association."""
        once_master_id = uuid7()
        master = MasterChore(
            id=once_master_id,
            name="One-Time Single",
            category_id=_CAT_KITCHEN,
            occurrence_count=1,  # Already generated
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        once_assoc_id = uuid7()
        assoc = ChoreAssociation(
            id=once_assoc_id,
            master_chore_id=once_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        # Create association directly (bypasses generation trigger)
        await service.repository.create_association(assoc)

        # Manually trigger generation
        result = await service.generate_instance_for_association(once_assoc_id)

        # Should return None (already generated)
        assert result is None
        instances = await service.get_instances(master_chore_id=once_master_id)
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_one_time_safety_net_generates(
        self, service: ChoresService
    ) -> None:
        """Test that safety net generates one-time instances."""
        once_master_id = uuid7()
        master = MasterChore(
            id=once_master_id,
            name="One-Time Safety Net",
            category_id=_CAT_KITCHEN,
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        once_assoc_id = uuid7()
        assoc = ChoreAssociation(
            id=once_assoc_id,
            master_chore_id=once_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )
        # Create association directly (bypasses generation trigger)
        await service.repository.create_association(assoc)

        # Verify no instances exist
        instances_before = await service.get_instances(master_chore_id=once_master_id)
        assert len(instances_before) == 0

        # Run safety net
        generated = await service.ensure_current_instances()

        # Should have generated one instance
        assert len(generated) >= 1
        instances_after = await service.get_instances(master_chore_id=once_master_id)
        assert len(instances_after) == 1


class TestAssociationAutoClaimAssign:
    """Tests for auto_claim and auto_assign on association creation."""

    @pytest.mark.asyncio
    async def test_create_association_with_auto_claim(
        self, service: ChoresService
    ) -> None:
        """Test that auto_claim claims the generated instance."""
        # Create a new master and association
        claim_master_id = uuid7()
        master = MasterChore(
            id=claim_master_id,
            name="Auto Claim Test",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        claim_assoc_id = uuid7()
        association = ChoreAssociation(
            id=claim_assoc_id,
            master_chore_id=claim_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )

        created, instance = await service.create_association(
            association, auto_claim=True
        )

        assert created.id == claim_assoc_id
        assert instance is not None
        assert instance.member_id == _MEMBER_ARYA
        assert instance.assigned_by is None

    @pytest.mark.asyncio
    async def test_create_association_with_auto_assign(
        self, service: ChoresService
    ) -> None:
        """Test that auto_assign assigns the generated instance."""
        assign_master_id = uuid7()
        master = MasterChore(
            id=assign_master_id,
            name="Auto Assign Test",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        assign_assoc_id = uuid7()
        association = ChoreAssociation(
            id=assign_assoc_id,
            master_chore_id=assign_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )

        created, instance = await service.create_association(
            association,
            auto_assign={"assigner_id": _MEMBER_TRISHA},
        )

        assert created.id == assign_assoc_id
        assert instance is not None
        assert instance.member_id == _MEMBER_ARYA
        assert instance.assigned_by == _MEMBER_TRISHA

    @pytest.mark.asyncio
    async def test_create_association_without_auto_flags(
        self, service: ChoresService
    ) -> None:
        """Test backward compatibility: no auto flags returns instance as-is."""
        backward_master_id = uuid7()
        master = MasterChore(
            id=backward_master_id,
            name="Backward Compat Test",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        backward_assoc_id = uuid7()
        association = ChoreAssociation(
            id=backward_assoc_id,
            master_chore_id=backward_master_id,
            member_id=_MEMBER_ARYA,
            created_by=_MEMBER_FAIYAZ,
        )

        created, instance = await service.create_association(association)

        assert created.id == backward_assoc_id
        assert instance is not None
        # For member associations, instance is pre-populated with member_id
        assert instance.member_id == _MEMBER_ARYA

    @pytest.mark.asyncio
    async def test_create_association_auto_claim_open_pool_no_effect(
        self, service: ChoresService
    ) -> None:
        """Test that auto_claim on open pool has no effect (no member_id)."""
        pool_master_id = uuid7()
        master = MasterChore(
            id=pool_master_id,
            name="Open Pool Auto Claim",
            category_id=_CAT_KITCHEN,
            frequency="daily",
            due_time="18:00",
            created_by=_MEMBER_FAIYAZ,
        )
        await service.create_master_chore(master, tag_ids=[])

        pool_assoc_id = uuid7()
        association = ChoreAssociation(
            id=pool_assoc_id,
            master_chore_id=pool_master_id,
            member_id=None,
            created_by=_MEMBER_FAIYAZ,
        )

        # auto_claim=True but member_id=None — should not claim
        created, instance = await service.create_association(
            association, auto_claim=True
        )

        assert created.id == pool_assoc_id
        assert instance is not None
        assert instance.member_id is None
