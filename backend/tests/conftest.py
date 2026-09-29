import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.movie import Movie
from app.models.user import User, UserSettings
from app.services.auth_service import hash_password, create_access_token

# Use isolated in-memory or test SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_movierec.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Seed a few test movies
    db = TestingSessionLocal()
    sample_movies = [
        Movie(id="m1", movielens_id=1, title="Inception", release_year=2010, genres="Action|Sci-Fi"),
        Movie(id="m2", movielens_id=2, title="Interstellar", release_year=2014, genres="Adventure|Drama|Sci-Fi"),
        Movie(id="m3", movielens_id=3, title="The Dark Knight", release_year=2008, genres="Action|Crime|Drama"),
        Movie(id="m4", movielens_id=4, title="The Notebook", release_year=2004, genres="Drama|Romance"),
        Movie(id="m5", movielens_id=5, title="Toy Story", release_year=1995, genres="Animation|Children|Comedy"),
    ]
    for m in sample_movies:
        db.add(m)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    user = User(
        id="test-user-id",
        email="testuser@example.com",
        password_hash=hash_password("password123"),
        status="active"
    )
    db.add(user)
    db.flush()
    settings = UserSettings(user_id=user.id)
    db.add(settings)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(data={"sub": test_user.id, "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}
