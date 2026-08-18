"""Unit tests for family domain models."""

from datetime import date

from app.domain.family.models import FamilyMember


class TestFamilyMember:
    """Tests for FamilyMember entity."""

    def test_create_family_member(self) -> None:
        """Test creating a family member."""
        member = FamilyMember(
            id="alice",
            name="Alice",
            email="alice@example.com",
            color="#FF0000",
            initial="A",
            date_of_birth=date(1990, 5, 15),
            relation="mother",
        )
        assert member.id == "alice"
        assert member.name == "Alice"
        assert member.email == "alice@example.com"
        assert member.color == "#FF0000"
        assert member.initial == "A"
        assert member.date_of_birth == date(1990, 5, 15)
        assert member.relation == "mother"

    def test_create_family_member_minimal(self) -> None:
        """Test creating a family member with only required fields."""
        member = FamilyMember(
            id="bob", name="Bob", email="bob@example.com", color="#00FF00", initial="B"
        )
        assert member.id == "bob"
        assert member.date_of_birth is None
        assert member.relation is None

    def test_equality_by_id(self) -> None:
        """Test that family members are equal if they have the same ID."""
        member1 = FamilyMember(
            id="alice", name="Alice", email="alice@example.com", color="#FF0000", initial="A"
        )
        member2 = FamilyMember(
            id="alice",
            name="Alice Smith",
            email="alice.smith@example.com",
            color="#00FF00",
            initial="A",
        )
        assert member1 == member2

    def test_inequality_by_id(self) -> None:
        """Test that family members with different IDs are not equal."""
        member1 = FamilyMember(
            id="alice", name="Alice", email="alice@example.com", color="#FF0000", initial="A"
        )
        member2 = FamilyMember(
            id="bob", name="Alice", email="alice@example.com", color="#FF0000", initial="A"
        )
        assert member1 != member2

    def test_hash_by_id(self) -> None:
        """Test that family members hash by ID."""
        member1 = FamilyMember(
            id="alice", name="Alice", email="alice@example.com", color="#FF0000", initial="A"
        )
        member2 = FamilyMember(
            id="alice",
            name="Alice Smith",
            email="alice.smith@example.com",
            color="#00FF00",
            initial="A",
        )
        # Same hash because same ID
        assert hash(member1) == hash(member2)

        # Can be used in sets
        members = {member1, member2}
        assert len(members) == 1

    def test_not_equal_to_other_types(self) -> None:
        """Test that family member is not equal to other types."""
        member = FamilyMember(
            id="alice", name="Alice", email="alice@example.com", color="#FF0000", initial="A"
        )
        assert member != "alice"
        assert member != 123
        assert member != None  # noqa: E711
