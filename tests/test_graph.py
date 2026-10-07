import pytest
from pathlib import Path
from src.cinemind.schemas import Movie
from src.cinemind.retrieval.graph import MovieGraph

def test_graph_walk_and_paths(tmp_path: Path):
    # Construct a 10-movie toy catalog
    # Seed movie: Movie 1 (Director: Nolan, Cast: [Bale], Genre: [Sci-Fi])
    # Movie 2: Director: Nolan (Shares director with Seed, cold-start: n_ratings_train=0)
    # Movie 3: Cast: [Bale] (Shares actor with Seed)
    # Movie 4: Genre: [Sci-Fi] (Shares only genre with Seed)
    # Movies 5-10: Other genres/directors
    toy_movies = [
        Movie(
            movie_id=1,
            title="Seed Inception",
            year=2010,
            director="Christopher Nolan",
            cast=["Christian Bale", "Actor A"],
            genres=["Sci-Fi", "Drama"],
            overview="A mind-bending heist thriller.",
            keywords=["dream", "heist"],
            n_ratings_train=100
        ),
        Movie(
            movie_id=2,
            title="Oppenheimer ColdStart",
            year=2023,
            director="Christopher Nolan",  # Shares director (weight 3.0)
            cast=["Cillian Murphy"],
            genres=["Biography", "Drama"],
            overview="Nuclear physics and atomic weapon development.",
            keywords=["physics", "history"],
            n_ratings_train=0  # Cold-start!
        ),
        Movie(
            movie_id=3,
            title="Bale Drama",
            year=2015,
            director="Other Director",
            cast=["Christian Bale"],  # Shares cast (weight 2.0)
            genres=["Drama"],
            overview="A dramatic story.",
            keywords=["drama"],
            n_ratings_train=50
        ),
        Movie(
            movie_id=4,
            title="Random SciFi",
            year=2018,
            director="Generic Director",
            cast=["Unknown Actor"],
            genres=["Sci-Fi"],  # Shares only genre (weight < 1.0)
            overview="Outer space journey.",
            keywords=["alien"],
            n_ratings_train=80
        )
    ]
    for i in range(5, 11):
        toy_movies.append(Movie(
            movie_id=i,
            title=f"Filler Movie {i}",
            year=2000 + i,
            director=f"Director {i}",
            cast=[f"Actor {i}"],
            genres=[f"Genre{i}"],
            overview=f"Overview for movie {i}",
            keywords=[f"kw{i}"],
            n_ratings_train=50
        ))

    mg = MovieGraph.build_from_catalog(toy_movies)

    # Walk from seed movie 1
    results = mg.walk(seed_movie_ids=[1], k=5)
    result_ids = [mid for mid, _, _ in results]

    # Acceptance Criterion 3: Seeds are never returned
    assert 1 not in result_ids

    # Acceptance Criterion 1: Movie sharing director ranks above movie sharing only genre
    assert 2 in result_ids
    assert 4 in result_ids
    rank_2 = result_ids.index(2)
    rank_4 = result_ids.index(4)
    assert rank_2 < rank_4  # Director shared ranks higher than genre shared

    # Acceptance Criterion 2: Cold-start movie with seed's director is returned and its path names that director
    oppenheimer_res = next(r for r in results if r[0] == 2)
    path_str = oppenheimer_res[2]
    assert "Christopher Nolan" in path_str
