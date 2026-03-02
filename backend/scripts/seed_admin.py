"""Seed script to create initial users."""

import asyncio
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.security.password import get_password_hash
from app.infrastructure.database.models.organization import Organization
from app.infrastructure.database.models.user import User, Role


async def seed_users():
    """Create initial users and organization."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.email == "admin@comptrac.com")
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("Users already seeded!")
            return

        # Get all roles
        result = await session.execute(select(Role))
        roles = {role.name: role for role in result.scalars().all()}

        if "admin" not in roles:
            print("ERROR: Roles not found! Run migrations first.")
            return

        # Create organization
        org = Organization(
            name="CompTrac",
            slug="comptrac",
            description="CompTrac Organization",
            is_active=True,
            subscription_tier="enterprise",
            max_users=100,
            max_models=100,
            max_datasets=100,
        )
        session.add(org)
        await session.flush()  # Get org ID

        # Create admin user
        admin_user = User(
            email="admin@comptrac.com",
            hashed_password=await get_password_hash("admin123"),
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_superuser=True,
            is_verified=True,
            organization_id=org.id,
        )
        admin_user.roles.append(roles["admin"])
        session.add(admin_user)

        # Create analyst user
        analyst_user = User(
            email="analyst@comptrac.com",
            hashed_password=await get_password_hash("analyst123"),
            first_name="Analyst",
            last_name="User",
            is_active=True,
            is_superuser=False,
            is_verified=True,
            organization_id=org.id,
        )
        analyst_user.roles.append(roles["analyst"])
        session.add(analyst_user)

        # Create viewer user
        viewer_user = User(
            email="viewer@comptrac.com",
            hashed_password=await get_password_hash("viewer123"),
            first_name="Viewer",
            last_name="User",
            is_active=True,
            is_superuser=False,
            is_verified=True,
            organization_id=org.id,
        )
        viewer_user.roles.append(roles["viewer"])
        session.add(viewer_user)

        # Update org owner
        await session.flush()
        org.owner_id = admin_user.id

        await session.commit()
        print("\n" + "=" * 50)
        print("Users created successfully!")
        print("=" * 50)
        print("\n1. Admin User:")
        print("   Email: admin@comptrac.com")
        print("   Password: admin123")
        print("   Role: admin (full access)")
        print("\n2. Analyst User:")
        print("   Email: analyst@comptrac.com")
        print("   Password: analyst123")
        print("   Role: analyst (read/write models)")
        print("\n3. Viewer User:")
        print("   Email: viewer@comptrac.com")
        print("   Password: viewer123")
        print("   Role: viewer (read-only)")
        print("\nOrganization: CompTrac")
        print("=" * 50 + "\n")

    await engine.dispose()


# Keep backward compatibility
seed_admin = seed_users


if __name__ == "__main__":
    asyncio.run(seed_users())
