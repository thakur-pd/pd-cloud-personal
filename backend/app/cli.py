"""
Small CLI for one-off admin tasks. Invoked by the installer.

Usage:
    python -m app.cli create-admin <username> <password>
    python -m app.cli reset-password <username> <new_password>
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from .database import SessionLocal, init_db
from .models import User
from .security import hash_password


async def create_admin(username: str, password: str) -> None:
    await init_db()
    async with SessionLocal() as db:
        existing = (await db.execute(select(User))).scalar_one_or_none()
        if existing:
            print(f"Admin already exists ({existing.username}). Use reset-password to change.")
            return
        user = User(username=username, password_hash=hash_password(password))
        db.add(user)
        await db.commit()
        print(f"✅ Admin '{username}' created")


async def reset_password(username: str, new_password: str) -> None:
    await init_db()
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
        if not user:
            print("User not found"); return
        user.password_hash = hash_password(new_password)
        await db.commit()
        print(f"✅ Password reset for {username}")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == "create-admin" and len(args) == 2:
        asyncio.run(create_admin(args[0], args[1]))
    elif cmd == "reset-password" and len(args) == 2:
        asyncio.run(reset_password(args[0], args[1]))
    else:
        print(__doc__); sys.exit(1)


if __name__ == "__main__":
    main()
