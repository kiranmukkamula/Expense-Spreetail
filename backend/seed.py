from datetime import datetime, timezone
from app.core.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.group import Group, GroupMembership
from app.core.security import get_password_hash

def seed_database():
    # Make sure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).filter(User.email == "aisha@example.com").first():
            print("Database already seeded.")
            return

        print("Seeding database...")

        # 1. Create Users
        users_data = [
            ("aisha@example.com", "Aisha", "password"),
            ("rohan@example.com", "Rohan", "password"),
            ("priya@example.com", "Priya", "password"),
            ("meera@example.com", "Meera", "password"),
            ("sam@example.com", "Sam", "password"),
            ("dev@example.com", "Dev", "password"),
            ("kabir@example.com", "Kabir", "password"),
        ]
        
        users = {}
        for email, name, pwd in users_data:
            user = User(
                email=email,
                name=name,
                password_hash=get_password_hash(pwd)
            )
            db.add(user)
            db.flush()
            users[email] = user

        # 2. Create Roommates Group
        group = Group(
            name="Roommates",
            description="Flat 4B shared apartment expenses"
        )
        db.add(group)
        db.flush()

        # 3. Create memberships with historical timelines
        # Aisha, Rohan, Priya, Meera join on Jan 1, 2026
        jan_1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        
        for email in ["aisha@example.com", "rohan@example.com", "priya@example.com"]:
            mem = GroupMembership(
                group_id=group.id,
                user_id=users[email].id,
                joined_at=jan_1
            )
            db.add(mem)

        # Meera leaves on Sunday, March 29, 2026
        meera_left = datetime(2026, 3, 29, 12, 0, 0, tzinfo=timezone.utc)
        meera_mem = GroupMembership(
            group_id=group.id,
            user_id=users["meera@example.com"].id,
            joined_at=jan_1,
            left_at=meera_left
        )
        db.add(meera_mem)

        # Sam joins on April 5, 2026
        sam_joined = datetime(2026, 4, 5, 9, 0, 0, tzinfo=timezone.utc)
        sam_mem = GroupMembership(
            group_id=group.id,
            user_id=users["sam@example.com"].id,
            joined_at=sam_joined
        )
        db.add(sam_mem)

        db.commit()
        print("Database seeding completed successfully!")
        print(f"Group ID: {group.id}")
        
    except Exception as e:
        db.rollback()
        print(f"Failed to seed database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
