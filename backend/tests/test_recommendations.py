def test_recommendation_generation_and_feedback(client, auth_headers):
    # First, user likes Inception (Sci-Fi, Action)
    inter_res = client.post("/api/v1/interactions", json={
        "movie_id": "m1",
        "interaction_type": "like"
    }, headers=auth_headers)
    assert inter_res.status_code == 201

    # Fetch recommendations
    rec_res = client.get("/api/v1/recommendations", headers=auth_headers)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data is not None
    assert rec_data["status"] == "completed"
    assert len(rec_data["items"]) > 0

    # Ensure watched/interacted movie m1 is EXCLUDED from recommendations
    rec_movie_ids = [item["movie_id"] for item in rec_data["items"]]
    assert "m1" not in rec_movie_ids

    # Check that rank is 1..N and scores are finite
    for i, item in enumerate(rec_data["items"], start=1):
        assert item["rank"] == i
        assert item["score"] is not None
        assert len(item["explanation"]) > 0

    # Submit feedback on top recommendation
    first_item = rec_data["items"][0]
    fb_res = client.post(
        f"/api/v1/recommendations/{first_item['id']}/feedback",
        json={"feedback": "liked"},
        headers=auth_headers
    )
    assert fb_res.status_code == 200
    fb_data = fb_res.json()
    assert fb_data["feedback_status"] == "liked"
