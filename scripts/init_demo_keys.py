#!/usr/bin/env python3
"""
Initialize the database with demo API keys
"""
import os
import sys

import structlog
from sqlalchemy.orm import Session

from app.database import SessionLocal, create_tables
from app.models import ApiKey

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


logger = structlog.get_logger()


def init_demo_keys():
    """Create demo API keys in the database"""

    # Create tables first
    create_tables()

    db: Session = SessionLocal()

    try:
        # Check if demo keys already exist
        existing_demo1 = db.query(ApiKey).filter(
            ApiKey.key == "demo-key-1").first()
        existing_demo2 = db.query(ApiKey).filter(
            ApiKey.key == "demo-key-2").first()

        if existing_demo1 and existing_demo2:
            logger.info("Demo API keys already exist, skipping creation")
            return

        # Create demo keys
        demo_keys = [{"key": "demo-key-1",
                      "name": "Demo Client 1",
                      "description": "Default demo API key for testing",
                      "rate_limit": 100,
                      "active": True,
                      "created_by": "system"},
                     {"key": "demo-key-2",
                      "name": "Demo Client 2",
                      "description": "Second demo API key with higher rate limit",
                      "rate_limit": 200,
                      "active": True,
                      "created_by": "system"},
                     {"key": "admin-super-key-change-in-production",
                      "name": "Super Admin Key",
                      "description": ("Administrative key for API key "
                                      "management (CHANGE IN PRODUCTION)"),
                      "rate_limit": 1000,
                      "active": True,
                      "created_by": "system"},
                     {"key": "tvdb-demo-user-key",
                      "name": "TVDB Demo User Key",
                      "description": "Demo user-supported key requiring PIN",
                      "rate_limit": 50,
                      "active": True,
                      "created_by": "system",
                      "requires_pin": True,
                      "pin": "1234"}]

        for key_data in demo_keys:
            # Only create if it doesn't exist
            existing = db.query(ApiKey).filter(
                ApiKey.key == key_data["key"]).first()
            if not existing:
                api_key = ApiKey(**key_data)
                db.add(api_key)
                logger.info(
                    "Created demo API key",
                    name=key_data["name"],
                    key_preview=f"...{key_data['key'][-4:]}")

        db.commit()
        logger.info("Demo API keys initialization completed")

        # List all keys
        all_keys = db.query(ApiKey).all()
        logger.info("Current API keys in database", count=len(all_keys))
        for key in all_keys:
            logger.info("API Key",
                        id=key.id,
                        name=key.name,
                        rate_limit=key.rate_limit,
                        active=key.active,
                        key_preview=f"...{key.key[-4:]}")

    except Exception as e:
        logger.error("Failed to initialize demo keys", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing demo API keys...")
    init_demo_keys()
    print("Demo API keys initialization completed!")
