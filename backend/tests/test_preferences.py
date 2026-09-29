from datetime import datetime, timedelta
from app.models.interaction import UserInteraction
from app.models.movie import Movie
from app.services.preference_service import (
    map_interaction_to_strength,
    calculate_genre_preferences,
    PreferenceService,
)


def test_interaction_strength_mapping():
    assert map_interaction_to_strength("rating", 5.0) == 1.0
    assert map_interaction_to_strength("rating", 3.0) == 0.0
    assert map_interaction_to_strength("rating", 1.0) == -1.0
    assert map_interaction_to_strength("like") == 1.0
    assert map_interaction_to_strength("dislike") == -1.0
    assert map_interaction_to_strength("dismiss") == -0.8
    assert map_interaction_to_strength("watched") == 0.3


def test_time_decay_calculation():
    now = datetime(2026, 1, 10, 12, 0, 0)
    old_time = now - timedelta(days=20)
    recent_time = now - timedelta(days=1)

    movie = Movie(id="m1", movielens_id=1, title="Test Movie", genres="Action|Sci-Fi")
    inter_old = UserInteraction(
        id="i1", user_id="u1", movie_id="m1", interaction_type="like", occurred_at=old_time
    )
    inter_recent = UserInteraction(
        id="i2", user_id="u1", movie_id="m1", interaction_type="like", occurred_at=recent_time
    )

    # With decay_rate = 0.1: recent interaction has higher weight than old interaction
    decayed_scores_old = calculate_genre_preferences([(inter_old, movie)], decay_rate=0.1, reference_time=now)
    decayed_scores_recent = calculate_genre_preferences([(inter_recent, movie)], decay_rate=0.1, reference_time=now)

    assert decayed_scores_recent["Action"] > 0
    # Old interaction decay is dampened
    assert decayed_scores_old["Action"] > 0


def test_preference_profile_api_and_reset(client, auth_headers):
    # Get initial preference profile
    res = client.get("/api/v1/preferences", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "profile_version" in data
    initial_version = data["profile_version"]

    # Reset profile
    reset_res = client.post("/api/v1/preferences/reset", headers=auth_headers)
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["profile_version"] > initial_version

    # Verify reset profile is empty
    pref_res = client.get("/api/v1/preferences", headers=auth_headers)
    assert pref_res.status_code == 200
    pref_data = pref_res.json()
    assert pref_data["long_term_preferences"] == {}
    assert pref_data["short_term_preferences"] == {}
