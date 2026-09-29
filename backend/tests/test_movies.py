def test_list_movies_pagination_and_search(client):
    # List movies
    res = client.get("/api/v1/movies?page=1&page_size=2")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 5
    assert data["page"] == 1
    assert data["page_size"] == 2

    # Search by title
    search_res = client.get("/api/v1/movies?search=Inception")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert len(search_data["items"]) == 1
    assert search_data["items"][0]["title"] == "Inception"

    # Filter by genre
    genre_res = client.get("/api/v1/movies?genre=Sci-Fi")
    assert genre_res.status_code == 200
    genre_data = genre_res.json()
    assert len(genre_data["items"]) >= 2


def test_invalid_pagination_parameters(client):
    res = client.get("/api/v1/movies?page=0")
    assert res.status_code in [400, 422]

    res2 = client.get("/api/v1/movies?page_size=200")
    assert res2.status_code in [400, 422]


def test_get_movie_by_id(client):
    res = client.get("/api/v1/movies/m1")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "m1"
    assert data["title"] == "Inception"

    # Nonexistent movie
    res_404 = client.get("/api/v1/movies/m-nonexistent")
    assert res_404.status_code == 404
