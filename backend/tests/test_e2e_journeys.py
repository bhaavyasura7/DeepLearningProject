from app.models.user import User, UserSettings
from app.services.auth_service import hash_password, create_access_token


def test_cross_user_isolation(client, db):
    # Create User A
    user_a = User(id="user-a", email="usera@test.com", password_hash=hash_password("pw1"), status="active")
    db.add(user_a)
    db.flush()
    settings_a = UserSettings(user_id=user_a.id)
    db.add(settings_a)

    # Create User B
    user_b = User(id="user-b", email="userb@test.com", password_hash=hash_password("pw2"), status="active")
    db.add(user_b)
    db.flush()
    settings_b = UserSettings(user_id=user_b.id)
    db.add(settings_b)
    db.commit()

    token_a = create_access_token({"sub": user_a.id, "email": user_a.email})
    token_b = create_access_token({"sub": user_b.id, "email": user_b.email})
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates an interaction
    inter_res = client.post("/api/v1/interactions", json={
        "movie_id": "m1",
        "interaction_type": "like"
    }, headers=headers_a)
    assert inter_res.status_code == 201
    inter_a_id = inter_res.json()["id"]

    # User B attempts to delete User A's interaction -> MUST BE FORBIDDEN 403
    del_res = client.delete(f"/api/v1/interactions/{inter_a_id}", headers=headers_b)
    assert del_res.status_code == 403

    # User A gets recommendations
    rec_res = client.get("/api/v1/recommendations", headers=headers_a)
    assert rec_res.status_code == 200
    batch_a_id = rec_res.json()["id"]

    # User B attempts to access User A's recommendation batch -> MUST BE FORBIDDEN 403
    cross_rec_res = client.get(f"/api/v1/recommendations/{batch_a_id}", headers=headers_b)
    assert cross_rec_res.status_code == 403


def test_full_user_lifecycle_and_pause_resume(client, db):
    # 1. Register & Login
    reg_res = client.post("/api/v1/auth/register", json={
        "email": "lifecycle@test.com",
        "password": "validpassword123"
    })
    assert reg_res.status_code == 201
    token = client.post("/api/v1/auth/login", json={
        "email": "lifecycle@test.com",
        "password": "validpassword123"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. User rates movie m2 (Interstellar, Sci-Fi) 5.0
    client.post("/api/v1/interactions", json={
        "movie_id": "m2",
        "interaction_type": "rating",
        "rating": 5.0
    }, headers=headers)

    # 3. Check preferences updated with Sci-Fi
    pref_res = client.get("/api/v1/preferences", headers=headers)
    assert pref_res.status_code == 200
    assert "Sci-Fi" in pref_res.json()["short_term_preferences"]

    # 4. Generate recommendations
    rec_res = client.get("/api/v1/recommendations", headers=headers)
    assert rec_res.status_code == 200
    batch = rec_res.json()
    assert batch["status"] == "completed"
    movie_ids = [it["movie_id"] for it in batch["items"]]
    assert "m2" not in movie_ids  # Watched/rated item is excluded

    # 5. User dismisses a recommended movie
    first_item = batch["items"][0]
    client.post(f"/api/v1/recommendations/{first_item['id']}/feedback", json={
        "feedback": "dismissed"
    }, headers=headers)

    # 6. Pause recommendations in settings
    pause_res = client.patch("/api/v1/settings", json={"recommendations_enabled": False}, headers=headers)
    assert pause_res.status_code == 200
    assert pause_res.json()["recommendations_enabled"] is False

    # 7. Resume recommendations
    resume_res = client.patch("/api/v1/settings", json={"recommendations_enabled": True}, headers=headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["recommendations_enabled"] is True

    # 8. Reset preference profile
    reset_res = client.post("/api/v1/preferences/reset", headers=headers)
    assert reset_res.status_code == 200
    pref_after = client.get("/api/v1/preferences", headers=headers).json()
    assert pref_after["short_term_preferences"] == {}
