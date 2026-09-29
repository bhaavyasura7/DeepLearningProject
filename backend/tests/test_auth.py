def test_register_and_login(client):
    # Register new user
    res = client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "securepassword123"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data

    # Try duplicate registration
    dup_res = client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "securepassword123"
    })
    assert dup_res.status_code == 409

    # Login with valid credentials
    login_res = client.post("/api/v1/auth/login", json={
        "email": "newuser@example.com",
        "password": "securepassword123"
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # Verify protected route /me
    me_res = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "newuser@example.com"


def test_login_invalid_credentials(client):
    res = client.post("/api/v1/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    })
    assert res.status_code == 401


def test_protected_route_without_token(client):
    res = client.get("/api/v1/me")
    assert res.status_code == 401
