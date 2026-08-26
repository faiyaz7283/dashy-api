"""API tests for chores endpoints.

Integration tests for the chores API to verify response structure
and endpoint behavior.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.container import get_chores_repository, get_chores_service
from app.domain.chores.services import ChoresService
from app.infrastructure.chores.mock_adapter import MockChoresRepository
from app.main import app


@pytest.fixture
def client() -> AsyncClient:
    """Create an async test client with mock repository.

    Returns:
        AsyncClient configured with the app and mock chores repository.
    """
    # Override the dependencies to use mock data
    mock_repo = MockChoresRepository()
    mock_service = ChoresService(repository=mock_repo)

    app.dependency_overrides[get_chores_repository] = lambda: mock_repo
    app.dependency_overrides[get_chores_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    # Clean up
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_all_chores(client: AsyncClient) -> None:
    """Test GET /api/v1/chores returns proper structure."""
    response = await client.get("/api/v1/chores")
    assert response.status_code == 200
    data = response.json()

    assert "categories" in data
    assert "tags" in data
    assert "master_chores" in data
    assert "associations" in data
    assert "instances" in data

    # Verify categories have expected fields
    assert isinstance(data["categories"], list)
    if data["categories"]:
        cat = data["categories"][0]
        assert "id" in cat
        assert "name" in cat

    # Verify tags have expected fields
    assert isinstance(data["tags"], list)
    if data["tags"]:
        tag = data["tags"][0]
        assert "id" in tag
        assert "name" in tag

    # Verify master_chores have expected fields
    assert isinstance(data["master_chores"], list)
    if data["master_chores"]:
        master = data["master_chores"][0]
        assert "id" in master
        assert "name" in master
        assert "category" in master
        assert "tags" in master
        assert "difficulty" in master
        assert "recurrence_rule" in master
        assert "status" in master
        assert "created_by" in master
        assert "is_collaborative" in master

    # Verify associations have expected fields
    assert isinstance(data["associations"], list)
    if data["associations"]:
        assoc = data["associations"][0]
        assert "id" in assoc
        assert "master_chore_id" in assoc
        assert "member_id" in assoc or "is_open_pool" in assoc

    # Verify instances have expected fields
    assert isinstance(data["instances"], list)
    if data["instances"]:
        inst = data["instances"][0]
        assert "id" in inst
        assert "master_chore_id" in inst
        assert "association_id" in inst
        assert "status" in inst


@pytest.mark.asyncio
async def test_create_master_chore(client: AsyncClient) -> None:
    """Test POST /api/v1/chores/masters creates a master chore."""
    response = await client.post(
        "/api/v1/chores/masters",
        json={
            "name": "Test Chore",
            "category_id": "cat-kitchen",
            "tag_ids": [],
            "difficulty": 2,
            "recurrence_rule": {"frequency": "daily", "time": "18:00"},
            "estimated_minutes": 10,
            "expiration_behavior": "carry_over",
            "created_by": "faiyaz",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Chore"
    assert data["difficulty"] == 2
    assert data["recurrence_rule"]["frequency"] == "daily"
    assert data["status"] == "active"
    assert data["created_by"] == "faiyaz"


@pytest.mark.asyncio
async def test_create_master_chore_with_conditions(client: AsyncClient) -> None:
    """Test creating a conditional master chore."""
    response = await client.post(
        "/api/v1/chores/masters",
        json={
            "name": "Shovel Snow",
            "category_id": "cat-outdoor",
            "tag_ids": [],
            "difficulty": 3,
            "recurrence_rule": {"frequency": "daily", "time": "08:00"},
            "conditions": {
                "logic": "and",
                "conditions": [
                    {"type": "weather", "metric": "snowfall", "operator": "gt", "value": 0}
                ]
            },
            "expiration_behavior": "disappear",
            "created_by": "faiyaz",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Shovel Snow"
    assert data["conditions"] is not None
    assert data["conditions"]["logic"] == "and"


@pytest.mark.asyncio
async def test_create_association(client: AsyncClient) -> None:
    """Test POST /api/v1/chores/associations creates an association."""
    # master-005 has no existing associations
    response = await client.post(
        "/api/v1/chores/associations",
        json={
            "master_chore_id": "master-005",
            "member_id": "arya",
            "is_open_pool": False,
            "created_by": "faiyaz",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["master_chore_id"] == "master-005"
    assert data["member_id"] == "arya"
    assert data["is_open_pool"] is False


@pytest.mark.asyncio
async def test_create_open_pool_association(client: AsyncClient) -> None:
    """Test creating an open pool association."""
    response = await client.post(
        "/api/v1/chores/associations",
        json={
            "master_chore_id": "master-002",
            "member_id": None,
            "is_open_pool": True,
            "created_by": "trisha",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["master_chore_id"] == "master-002"
    assert data["member_id"] is None
    assert data["is_open_pool"] is True


@pytest.mark.asyncio
async def test_delete_association(client: AsyncClient) -> None:
    """Test DELETE /api/v1/chores/associations/{id}."""
    response = await client.delete("/api/v1/chores/associations/assoc-001")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_create_association_nonexistent_master_returns_404(
    client: AsyncClient,
) -> None:
    """Test creating association with non-existent master returns 404."""
    response = await client.post(
        "/api/v1/chores/associations",
        json={
            "master_chore_id": "nonexistent",
            "member_id": "arya",
            "is_open_pool": False,
            "created_by": "faiyaz",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_association_duplicate_member_returns_409(
    client: AsyncClient,
) -> None:
    """Test creating duplicate member association returns 409."""
    # master-001 already has assoc-001 (arya)
    response = await client.post(
        "/api/v1/chores/associations",
        json={
            "master_chore_id": "master-001",
            "member_id": "arya",
            "is_open_pool": False,
            "created_by": "faiyaz",
        },
    )
    assert response.status_code == 409
    data = response.json()
    assert "already has an active association" in data["detail"]


@pytest.mark.asyncio
async def test_create_association_non_collaborative_conflict_returns_409(
    client: AsyncClient,
) -> None:
    """Test creating second association on non-collaborative master returns 409."""
    # master-001 already has assoc-001 (arya), try adding raya
    response = await client.post(
        "/api/v1/chores/associations",
        json={
            "master_chore_id": "master-001",
            "member_id": "raya",
            "is_open_pool": False,
            "created_by": "faiyaz",
        },
    )
    assert response.status_code == 409
    data = response.json()
    assert "already has an active member association" in data["detail"]


@pytest.mark.asyncio
async def test_create_association_duplicate_open_pool_returns_409(
    client: AsyncClient,
) -> None:
    """Test creating duplicate open pool association returns 409."""
    # master-003 already has assoc-002 (open pool)
    response = await client.post(
        "/api/v1/chores/associations",
        json={
            "master_chore_id": "master-003",
            "member_id": None,
            "is_open_pool": True,
            "created_by": "faiyaz",
        },
    )
    assert response.status_code == 409
    data = response.json()
    assert "already has an open pool association" in data["detail"]


@pytest.mark.asyncio
async def test_create_association_inactive_master_returns_404(
    client: AsyncClient,
) -> None:
    """Test creating association with inactive master returns 404."""
    # First archive master-002
    await client.delete("/api/v1/chores/masters/master-002")

    # Try to create association with archived master
    response = await client.post(
        "/api/v1/chores/associations",
        json={
            "master_chore_id": "master-002",
            "member_id": "arya",
            "is_open_pool": False,
            "created_by": "faiyaz",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_association_returns_404(
    client: AsyncClient,
) -> None:
    """Test deleting non-existent association returns 404."""
    response = await client.delete("/api/v1/chores/associations/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_claim_instance(client: AsyncClient) -> None:
    """Test POST /api/v1/chores/instances/{id}/claim."""
    response = await client.post(
        "/api/v1/chores/instances/inst-001/claim",
        json={"member_id": "arya"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["claimed_by"] == "arya"
    assert data["assigned_to"] is None
    assert data["assigned_by"] is None


@pytest.mark.asyncio
async def test_assign_instance(client: AsyncClient) -> None:
    """Test POST /api/v1/chores/instances/{id}/assign."""
    response = await client.post(
        "/api/v1/chores/instances/inst-001/assign",
        json={"assignee_id": "raya", "assigner_id": "trisha"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["assigned_to"] == "raya"
    assert data["assigned_by"] == "trisha"
    assert data["claimed_by"] is None


@pytest.mark.asyncio
async def test_update_instance_status(client: AsyncClient) -> None:
    """Test PUT /api/v1/chores/instances/{id}/status."""
    response = await client.put(
        "/api/v1/chores/instances/inst-001/status",
        json={
            "status": "in_progress",
            "actor_id": "arya",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["started_at"] is not None


@pytest.mark.asyncio
async def test_complete_instance(client: AsyncClient) -> None:
    """Test completing an instance."""
    response = await client.put(
        "/api/v1/chores/instances/inst-001/status",
        json={
            "status": "completed",
            "actor_id": "arya",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["completed_by"] == "arya"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_create_category(client: AsyncClient) -> None:
    """Test POST /api/v1/chores/categories."""
    response = await client.post(
        "/api/v1/chores/categories",
        json={"name": "Pet Care"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Pet Care"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_tag(client: AsyncClient) -> None:
    """Test POST /api/v1/chores/tags."""
    response = await client.post(
        "/api/v1/chores/tags",
        json={"name": "Urgent"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Urgent"
    assert "id" in data


@pytest.mark.asyncio
async def test_delete_master_chore(client: AsyncClient) -> None:
    """Test DELETE /api/v1/chores/masters/{id}."""
    response = await client.delete("/api/v1/chores/masters/master-001")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_claim_nonexistent_instance_returns_404(client: AsyncClient) -> None:
    """Test that claiming a nonexistent instance returns 404."""
    response = await client.post(
        "/api/v1/chores/instances/nonexistent/claim",
        json={"member_id": "arya"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_master_chore(client: AsyncClient) -> None:
    """Test PUT /api/v1/chores/masters/{id}."""
    response = await client.put(
        "/api/v1/chores/masters/master-002",
        json={
            "name": "Clean Bathroom Sink (Updated)",
            "difficulty": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Clean Bathroom Sink (Updated)"
    assert data["difficulty"] == 3


@pytest.mark.asyncio
async def test_update_master_chore_status(client: AsyncClient) -> None:
    """Test updating master chore status."""
    response = await client.put(
        "/api/v1/chores/masters/master-001",
        json={
            "status": "inactive",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inactive"
