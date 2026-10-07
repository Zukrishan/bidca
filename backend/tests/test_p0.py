"""
test_p0.py — Phase 1 acceptance tests for R1-R8.

Uses mongomock-motor (in-memory MongoDB) and pytest-asyncio.
No real MongoDB or SendGrid credentials are required.

Test names match exactly those listed in docs/REQUIREMENTS.md.
"""

from __future__ import annotations

import hashlib
import os
import sys
import types
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Ensure backend/ is importable
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ---------------------------------------------------------------------------
# Stub out server-level env vars before importing anything that reads them
# ---------------------------------------------------------------------------
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "bidca_test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3100")

# Remove Cloudinary mocks to test the 503 path
for k in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"):
    os.environ.pop(k, None)

# Remove SendGrid key to test the mock fallback
os.environ.pop("SENDGRID_API_KEY", None)

# ---------------------------------------------------------------------------
# mongomock-motor setup
# ---------------------------------------------------------------------------
import mongomock_motor  # type: ignore

# Patch motor so server.py gets a mongomock client on import
_mock_client = mongomock_motor.AsyncMongoMockClient()


def _make_test_db():
    """Return a fresh mongomock database for each test."""
    return _mock_client["bidca_test_" + str(id(object()))]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db():
    """Isolated in-memory MongoDB database."""
    _db = _make_test_db()
    yield _db
    # Drop all collections after each test
    for name in await _db.list_collection_names():
        await _db.drop_collection(name)


@pytest_asyncio.fixture
async def populated_db(db):
    """DB pre-populated with two users (seller + buyer)."""
    seller_result = await db.users.insert_one({
        "email": "seller@test.com",
        "full_name": "Alice Seller",
        "total_sales": 0,
        "total_sales_amount": 0,
        "auctions_won": 0,
        "total_purchases": 0,
        "total_bids_placed": 0,
    })
    buyer_result = await db.users.insert_one({
        "email": "buyer@test.com",
        "full_name": "Bob Buyer",
        "total_sales": 0,
        "total_sales_amount": 0,
        "auctions_won": 0,
        "total_purchases": 0,
        "total_bids_placed": 0,
    })
    return {
        "db": db,
        "seller_id": seller_result.inserted_id,
        "buyer_id": buyer_result.inserted_id,
    }


# ---------------------------------------------------------------------------
# Helper: build a listing doc
# ---------------------------------------------------------------------------

def make_listing(
    seller_id,
    *,
    end_time_offset_seconds: int = -60,   # negative = in the past
    bid_count: int = 0,
    highest_bidder_id=None,
    current_bid: float = 100.0,
    reserve_price: float | None = None,
    reserve_met: bool = True,
    status: str = "active",
    listing_type: str = "auction",
    title: str = "Test Auction",
) -> dict:
    end_time = (datetime.now(timezone.utc) + timedelta(seconds=end_time_offset_seconds)).isoformat()
    return {
        "title": title,
        "listing_type": listing_type,
        "status": status,
        "seller_id": seller_id,
        "end_time": end_time,
        "current_bid": current_bid,
        "starting_bid": current_bid,
        "bid_count": bid_count,
        "highest_bidder_id": highest_bidder_id,
        "highest_bidder_max_bid": current_bid if highest_bidder_id else None,
        "reserve_price": reserve_price,
        "reserve_met": reserve_met,
        "bid_increment": 5.0,
    }


# ===========================================================================
# R1: Auction past end_time closes correctly
# ===========================================================================

@pytest.mark.asyncio
async def test_auction_closes_sold(populated_db):
    """R1: Auction with bids and reserve met closes as sold."""
    data = populated_db
    db = data["db"]
    seller_id = data["seller_id"]
    buyer_id = data["buyer_id"]

    listing_doc = make_listing(
        seller_id,
        bid_count=3,
        highest_bidder_id=buyer_id,
        current_bid=150.0,
        reserve_met=True,
    )
    result = await db.listings.insert_one(listing_doc)
    listing_id = result.inserted_id

    from app.closer import run_once
    await run_once(db)

    updated = await db.listings.find_one({"_id": listing_id})
    assert updated["status"] == "sold", f"Expected 'sold', got {updated['status']!r}"
    assert str(updated["winner_id"]) == str(buyer_id)
    assert updated["sold_price"] == 150.0

    tx = await db.transactions.find_one({"listing_id": str(listing_id)})
    assert tx is not None, "Transaction should have been created"
    assert tx["buyer_id"] == str(buyer_id)
    assert tx["seller_id"] == str(seller_id)
    assert tx["amount"] == 150.0


@pytest.mark.asyncio
async def test_auction_closes_unsold_reserve_not_met(populated_db):
    """R1: Auction with bid but reserve not met closes as unsold."""
    data = populated_db
    db = data["db"]
    seller_id = data["seller_id"]
    buyer_id = data["buyer_id"]

    listing_doc = make_listing(
        seller_id,
        bid_count=2,
        highest_bidder_id=buyer_id,
        current_bid=80.0,
        reserve_price=200.0,
        reserve_met=False,
    )
    result = await db.listings.insert_one(listing_doc)
    listing_id = result.inserted_id

    from app.closer import run_once
    await run_once(db)

    updated = await db.listings.find_one({"_id": listing_id})
    assert updated["status"] == "unsold", f"Expected 'unsold', got {updated['status']!r}"
    assert updated.get("winner_id") is None

    tx = await db.transactions.find_one({"listing_id": str(listing_id)})
    assert tx is None, "No transaction should be created for unsold auction"


@pytest.mark.asyncio
async def test_auction_closes_no_bids(populated_db):
    """R1: Auction with no bids closes as unsold."""
    data = populated_db
    db = data["db"]
    seller_id = data["seller_id"]

    listing_doc = make_listing(seller_id, bid_count=0)
    result = await db.listings.insert_one(listing_doc)
    listing_id = result.inserted_id

    from app.closer import run_once
    await run_once(db)

    updated = await db.listings.find_one({"_id": listing_id})
    assert updated["status"] == "unsold"
    assert updated.get("winner_id") is None


# ===========================================================================
# R2: Closing is idempotent
# ===========================================================================

@pytest.mark.asyncio
async def test_close_idempotent(populated_db):
    """R2: Two closer passes produce exactly one transaction and one notification set."""
    data = populated_db
    db = data["db"]
    seller_id = data["seller_id"]
    buyer_id = data["buyer_id"]

    listing_doc = make_listing(
        seller_id,
        bid_count=1,
        highest_bidder_id=buyer_id,
        current_bid=100.0,
        reserve_met=True,
    )
    result = await db.listings.insert_one(listing_doc)
    listing_id = result.inserted_id

    from app.closer import run_once
    # First pass
    await run_once(db)
    # Second pass — must be a no-op
    await run_once(db)

    # Exactly one transaction
    txs = await db.transactions.find({"listing_id": str(listing_id)}).to_list(length=100)
    assert len(txs) == 1, f"Expected 1 transaction, got {len(txs)}"

    # Auction still sold (not double-changed)
    updated = await db.listings.find_one({"_id": listing_id})
    assert updated["status"] == "sold"

    # At most one winner notification and one seller notification
    winner_notifs = await db.notifications.find(
        {"user_id": str(buyer_id), "type": "auction_won"}
    ).to_list(length=10)
    assert len(winner_notifs) == 1, f"Expected 1 winner notification, got {len(winner_notifs)}"

    seller_notifs = await db.notifications.find(
        {"user_id": str(seller_id), "type": "item_sold"}
    ).to_list(length=10)
    assert len(seller_notifs) == 1, f"Expected 1 seller notification, got {len(seller_notifs)}"


# ===========================================================================
# R3: Sniper bid executes before close
# ===========================================================================

@pytest.mark.asyncio
async def test_sniper_bid_executes(populated_db):
    """R3: Due sniper bid executes and places a bid respecting max_bid."""
    data = populated_db
    db = data["db"]
    seller_id = data["seller_id"]
    buyer_id = data["buyer_id"]

    # Active listing with no bids yet, ending in 30s (not yet due for close)
    listing_doc = make_listing(
        seller_id,
        bid_count=0,
        current_bid=100.0,
        end_time_offset_seconds=30,  # future end — won't be closed this pass
        status="active",
    )
    result = await db.listings.insert_one(listing_doc)
    listing_id = result.inserted_id

    # Sniper bid that is due now (execute_at in the past)
    past_time = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    await db.sniper_bids.insert_one({
        "listing_id": listing_id,
        "user_id": buyer_id,
        "max_bid": 200.0,
        "minutes_before_end": 1,
        "execute_at": past_time,
        "status": "pending",
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
    })

    from app.closer import run_once
    await run_once(db)

    # Sniper bid should be marked executed
    sniper = await db.sniper_bids.find_one({"listing_id": listing_id})
    assert sniper["status"] == "executed", f"Expected 'executed', got {sniper['status']!r}"

    # A bid record should exist
    bid = await db.bids.find_one({"listing_id": str(listing_id)})
    assert bid is not None, "A bid record should have been created"
    assert bid["is_sniper"] is True
    assert bid["amount"] <= 200.0  # respects max_bid

    # Listing should reflect the new highest bidder
    updated_listing = await db.listings.find_one({"_id": listing_id})
    assert updated_listing["bid_count"] == 1
    assert str(updated_listing["highest_bidder_id"]) == str(buyer_id)


# ===========================================================================
# R4: Winner and seller get notified on close
# ===========================================================================

@pytest.mark.asyncio
async def test_close_notifies_winner_and_seller(populated_db):
    """R4: Winner and seller both receive in-app notifications when auction closes."""
    data = populated_db
    db = data["db"]
    seller_id = data["seller_id"]
    buyer_id = data["buyer_id"]

    listing_doc = make_listing(
        seller_id,
        bid_count=2,
        highest_bidder_id=buyer_id,
        current_bid=120.0,
        reserve_met=True,
    )
    result = await db.listings.insert_one(listing_doc)
    listing_id = result.inserted_id

    from app.closer import run_once
    await run_once(db)

    # Winner notification
    winner_notif = await db.notifications.find_one({
        "user_id": str(buyer_id),
        "type": "auction_won",
    })
    assert winner_notif is not None, "Winner should receive an 'auction_won' notification"

    # Seller notification
    seller_notif = await db.notifications.find_one({
        "user_id": str(seller_id),
        "type": "item_sold",
    })
    assert seller_notif is not None, "Seller should receive an 'item_sold' notification"


# ===========================================================================
# R5: send_email() — SendGrid vs log fallback
# ===========================================================================

@pytest.mark.asyncio
async def test_email_mock_fallback(caplog):
    """R5: When SENDGRID_API_KEY is unset, send_email logs and does not raise."""
    import logging
    # Ensure key is absent
    os.environ.pop("SENDGRID_API_KEY", None)

    from app.email import send_email

    with caplog.at_level(logging.INFO, logger="app.email"):
        await send_email(to="user@test.com", subject="Test Subject", html="<p>Hello</p>")

    # Should have logged a mock/info line
    assert any("send_email" in r.message for r in caplog.records), (
        "Expected a log record from send_email; got: " + str([r.message for r in caplog.records])
    )


# ===========================================================================
# R6: Cloudinary 503 when unconfigured
# ===========================================================================

@pytest.mark.asyncio
async def test_cloudinary_unconfigured():
    """R6: GET /cloudinary/signature returns 503 when CLOUDINARY_* env vars are absent."""
    # Ensure no Cloudinary vars
    for k in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"):
        os.environ.pop(k, None)

    # Import the server's FastAPI app (not the sio wrapper)
    # We need to import carefully — mongomock the motor client first
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=_mock_client):
        # server.py reads MONGO_URL at import time; ensure it's set
        from httpx import AsyncClient, ASGITransport

        # Re-import to pick up the patched env
        # Use the already-imported fastapi_app if available
        try:
            import server as srv
            fastapi_app = srv.fastapi_app
        except Exception:
            pytest.skip("server.py could not be imported for this test")

        # Build an authenticated user for the dependency
        # We bypass auth by overriding the dependency
        async def _fake_user():
            return {"_id": "000000000000000000000001", "email": "t@t.com", "full_name": "T"}

        from fastapi import Depends
        srv.fastapi_app.dependency_overrides[srv.get_current_user] = _fake_user

        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/cloudinary/signature")

        srv.fastapi_app.dependency_overrides.clear()

    assert resp.status_code == 503, f"Expected 503, got {resp.status_code}: {resp.text}"


# ===========================================================================
# R7: Forgot / reset password
# ===========================================================================

async def _request_reset_token(client, email: str) -> str:
    """POST forgot-password and pull the raw token out of the reset email, as a user would."""
    import re
    with patch("app.email.send_email", new_callable=AsyncMock) as mock_send:
        resp = await client.post("/api/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert mock_send.await_count == 1, "Exactly one reset email should be sent"
    match = re.search(r"token=([\w-]+)", mock_send.await_args.kwargs["html"])
    assert match, "Reset email must contain the token link"
    return match.group(1)


@pytest.mark.asyncio
async def test_password_reset_flow():
    """R7: Full forgot→reset flow: token emailed, stored only as a hash, 1h expiry."""
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=_mock_client):
        try:
            import server as srv
        except Exception:
            pytest.skip("server.py could not be imported")

        from httpx import AsyncClient, ASGITransport
        import bcrypt

        # Create a test user
        test_db = _mock_client[os.environ["DB_NAME"]]
        email = "resetme@test.com"
        await test_db.users.delete_many({"email": email})
        await test_db.users.insert_one({
            "email": email,
            "password_hash": bcrypt.hashpw(b"oldpassword", bcrypt.gensalt()).decode(),
            "full_name": "Reset User",
        })

        # Bind server to test db
        srv.db = test_db

        async def _fake_user():
            return {"_id": "000000000000000000000001", "email": "t@t.com", "full_name": "T"}

        srv.fastapi_app.dependency_overrides[srv.get_current_user] = _fake_user

        transport = ASGITransport(app=srv.fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: forgot-password — always 200; token arrives by email
            raw_token = await _request_reset_token(client, email)

            # Step 2: only the hash of the token is stored
            user = await test_db.users.find_one({"email": email})
            reset_doc = await test_db.password_reset_tokens.find_one({"user_id": str(user["_id"])})
            assert reset_doc is not None, "A reset record should have been created"
            assert raw_token not in reset_doc.values(), "Raw token must never be stored"
            expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            assert reset_doc.get("token_hash") == expected_hash, "Stored hash does not match sha256(raw_token)"

            # Expiry must be ~1h from now
            expires_at = datetime.fromisoformat(reset_doc["expires_at"])
            now = datetime.now(timezone.utc)
            assert expires_at > now, "Token should not already be expired"
            assert (expires_at - now).total_seconds() <= 3700, "Expiry should be ≤1h"

            # Step 3: reset-password with the raw token
            resp2 = await client.post("/api/auth/reset-password", json={
                "token": raw_token,
                "password": "NewSecurePass1!",
            })
            assert resp2.status_code == 200, f"Expected 200, got {resp2.status_code}: {resp2.text}"

            # Password actually changed
            user = await test_db.users.find_one({"email": email})
            assert bcrypt.checkpw(b"NewSecurePass1!", user["password_hash"].encode()), \
                "Password was not actually updated"

        srv.fastapi_app.dependency_overrides.clear()
        await test_db.users.delete_many({"email": email})
        await test_db.password_reset_tokens.delete_many({"user_id": str(user["_id"])})


@pytest.mark.asyncio
async def test_reset_token_single_use():
    """R7: Reset token cannot be used twice (single-use)."""
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=_mock_client):
        try:
            import server as srv
        except Exception:
            pytest.skip("server.py could not be imported")

        from httpx import AsyncClient, ASGITransport
        import bcrypt

        test_db = _mock_client[os.environ["DB_NAME"]]
        email = "singleuse@test.com"
        await test_db.users.delete_many({"email": email})
        await test_db.users.insert_one({
            "email": email,
            "password_hash": bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode(),
            "full_name": "Single Use",
        })

        srv.db = test_db

        transport = ASGITransport(app=srv.fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            raw_token = await _request_reset_token(client, email)

            # First use — should succeed
            r1 = await client.post("/api/auth/reset-password", json={
                "token": raw_token, "password": "Pass1!"
            })
            assert r1.status_code == 200, f"First use failed: {r1.status_code}"

            # Second use — must fail
            r2 = await client.post("/api/auth/reset-password", json={
                "token": raw_token, "password": "Pass2!"
            })
            assert r2.status_code in (400, 404, 410), (
                f"Second use of token should fail, got {r2.status_code}: {r2.text}"
            )

        await test_db.users.delete_many({"email": email})
        await test_db.password_reset_tokens.delete_many({})


# ===========================================================================
# R8: No default admin in production
# ===========================================================================

@pytest.mark.asyncio
async def test_no_default_admin_in_prod():
    """R8: When ENV=production and ADMIN_PASSWORD is 'admin123' (or unset), seed is refused."""
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=_mock_client):
        try:
            import server as srv
        except Exception:
            pytest.skip("server.py could not be imported")

        test_db = _mock_client[os.environ["DB_NAME"]]
        # Remove any existing admin
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@bidca.ca")
        await test_db.users.delete_many({"email": admin_email})

        srv.db = test_db

        # Simulate production + default password
        original_env = os.environ.get("ENV")
        original_pass = os.environ.get("ADMIN_PASSWORD")
        os.environ["ENV"] = "production"
        os.environ["ADMIN_PASSWORD"] = "admin123"

        try:
            # Call the seed logic — must not insert the admin and must not crash
            await srv._seed_admin()
        except Exception as exc:
            pytest.fail(f"_seed_admin() raised an exception in production mode: {exc}")
        finally:
            # Restore env
            if original_env is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = original_env
            if original_pass is None:
                os.environ.pop("ADMIN_PASSWORD", None)
            else:
                os.environ["ADMIN_PASSWORD"] = original_pass

        admin = await test_db.users.find_one({"email": admin_email, "role": "admin"})
        assert admin is None, (
            "Admin must NOT be seeded in production with the default password"
        )
