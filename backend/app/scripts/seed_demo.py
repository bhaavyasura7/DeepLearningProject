import os
import sys
from datetime import datetime, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models.user import User, UserSettings
from app.models.movie import Movie
from app.models.interaction import UserInteraction
from app.services.auth_service import hash_password
from app.services.preference_service import PreferenceService
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.job_queue import JobQueue


def seed_demo_environment():
    db = SessionLocal()
    try:
        print("Seeding demonstration user and interaction history...")
        demo_email = "demo@cinema.com"
        user = db.query(User).filter(User.email == demo_email).first()
        if not user:
            user = User(
                email=demo_email,
                password_hash=hash_password("demo123456"),
                status="active"
            )
            db.add(user)
            db.flush()
            settings = UserSettings(
                user_id=user.id,
                recommendations_enabled=True,
                notifications_enabled=True,
                refresh_frequency="event",
                notification_cooldown=15
            )
            db.add(settings)
            db.commit()
            print(f"Created demo user: {demo_email} (Password: demo123456)")
        else:
            print(f"Demo user already exists: {demo_email}")

        # Find sample movies for realistic historical interactions
        now = datetime.utcnow()
        movies = db.query(Movie).limit(10).all()
        if len(movies) < 5:
            print("Movies table empty. Please run import_movielens first!")
            return

        # Historical taste anchors (30 days ago: Sci-Fi & Action)
        inter1 = UserInteraction(
            user_id=user.id,
            movie_id=movies[0].id,
            interaction_type="rating",
            rating=5.0,
            occurred_at=now - timedelta(days=28),
            source="onboarding"
        )
        inter2 = UserInteraction(
            user_id=user.id,
            movie_id=movies[1].id,
            interaction_type="like",
            occurred_at=now - timedelta(days=25),
            source="web"
        )
        # Recent drift (1-2 days ago: Comedy & Animation)
        inter3 = UserInteraction(
            user_id=user.id,
            movie_id=movies[2].id,
            interaction_type="rating",
            rating=4.5,
            occurred_at=now - timedelta(days=2),
            source="web"
        )
        inter4 = UserInteraction(
            user_id=user.id,
            movie_id=movies[3].id,
            interaction_type="like",
            occurred_at=now - timedelta(hours=12),
            source="web"
        )

        db.add_all([inter1, inter2, inter3, inter4])
        db.commit()

        # Update preference profile
        print("Computing two-tier dynamic preference memory...")
        profile = PreferenceService.update_preference_profile(db, user.id)
        print(f"Preference profile updated to version {profile.profile_version}")
        print("Short-term preferences:", profile.short_term_preferences_json)
        print("Long-term preferences:", profile.long_term_preferences_json)

        # Generate proactive recommendations
        print("Running T-PRA proactive agent recommendation cycle...")
        orchestrator = AgentOrchestrator(db)
        batch = orchestrator.execute_recommendation_cycle(
            user_id=user.id,
            trigger_type="interaction",
            top_k=10,
            use_dynamic_memory=True
        )

        if batch:
            print(f"Successfully generated batch {batch.id} with {len(batch.items)} items!")
            for item in batch.items[:3]:
                movie = db.query(Movie).filter(Movie.id == item.movie_id).first()
                print(f"  #{item.rank}: {movie.title} ({movie.release_year}) -> {item.explanation}")

        print("\nDemo setup completed successfully!")
        print(f"Login Credentials:")
        print(f"  Email: {demo_email}")
        print(f"  Password: demo123456")

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_environment()
