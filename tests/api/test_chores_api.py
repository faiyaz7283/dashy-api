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
        assert "frequency" in master
        assert "status" in master
        assert "created_by" in master

    # Verify instances have expected fields
    assert isinstance(data["instances"], list)
    if data["instances"]:
        inst = data["instances"][0]
        assert "id" in inst
        assert "master_chore_id" in inst
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
            "frequency": "daily",
            "estimated_minutes": 10,
            "expiration_behavior": "carry_over",
            "created_by": "faiyaz",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Chore"
    assert data["difficulty"] == 2
    assert data["frequency"] == "daily"
    assert data["status"] == "active"  # adult creator auto-approves
    assert data["approved_by"] == "faiyaz"


@pytest.mark.asyncio
async def test_create_master_chore_kid_pending(client: AsyncClient) -> None:
    """Test that kid creator without approver gets pending status."""
    response = await client.post(
        "/api/v1/chores/masters",
        json={
            "name": "Kid's Chore",
            "category_id": "cat-general",
            "tag_ids": [],
            "difficulty": 1,
            "frequency": "once",
            "expiration_behavior": "disappear",
            "created_by": "arya",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending_approval"
    assert data["approved_by"] is None


@pytest.mark.asyncio
async def test_approve_master_chore(client: AsyncClient) -> None:
    """Test POST /api/v1/chores/masters/{id}/approve."""
    # First create a pending chore
    create_resp = await client.post(
        "/api/v1/chores/masters",
        json={
            "name": "Pending Chore",
            "category_id": "cat-kitchen",
            "tag_ids": [],
            "difficulty": 1,
            "frequency": "once",
            "expiration_behavior": "disappear",
            "created_by": "raya",
        },
    )
    chore_id = create_resp.json()["id"]

    # Now approve it
    response = await client.post(
        f"/api/v1/chores/masters/{chore_id}/approve",
        json={"approver_id": "trisha"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["approved_by"] == "trisha"


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
            "is_adult": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["started_at"] is not None


@pytest.mark.asyncio
async def test_signoff_instance(client: AsyncClient) -> None:
    """Test POST /api/v1/chores/instances/{id}/signoff."""
    # inst-005 is completed_pending_signoff
    response = await client.post(
        "/api/v1/chores/instances/inst-005/signoff",
        json={"signoff_member_id": "faiyaz"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["signoff_by"] == "faiyaz"
    assert data["signed_off_at"] is not None


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
