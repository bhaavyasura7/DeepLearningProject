def test_record_interaction_and_idempotency(client, auth_headers):
    payload = {
        "movie_id": "m1",
        "interaction_type": "rating",
        "rating": 5.0,
        "idempotency_key": "key-12345"
    }

    # First attempt: creates interaction
    res1 = client.post("/api/v1/interactions", json=payload, headers=auth_headers)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["movie_id"] == "m1"
    assert data1["rating"] == 5.0
    assert data1["interaction_type"] == "rating"

    # Second attempt with same idempotency key: returns 200 without duplication
    res2 = client.post("/api/v1/interactions", json=payload, headers=auth_headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["id"] == data1["id"]

    # Verify interaction appears in list
    list_res = client.get("/api/v1/interactions", headers=auth_headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 1


def test_invalid_interaction_rejected(client, auth_headers):
    # Invalid rating (> 5.0)
    res = client.post("/api/v1/interactions", json={
        "movie_id": "m1",
        "interaction_type": "rating",
        "rating": 6.5
    }, headers=auth_headers)
    assert res.status_code == 422

    # Nonexistent movie
    res2 = client.post("/api/v1/interactions", json={
        "movie_id": "m-missing",
        "interaction_type": "like"
    }, headers=auth_headers)
    assert res2.status_code == 404
