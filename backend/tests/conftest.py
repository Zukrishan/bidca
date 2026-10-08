"""
Shared test setup.

Each test module creates "its own" mongomock client and patches AsyncIOMotorClient before
importing `server`, but `server` (and `app.db`) is imported only once per run, so whichever
module imports first decides which client the app uses. Making every AsyncMongoMockClient()
the same instance keeps all modules looking at the same in-memory database, regardless of
file order.
"""

import mongomock_motor  # type: ignore

_shared_client = mongomock_motor.AsyncMongoMockClient()
mongomock_motor.AsyncMongoMockClient = lambda *args, **kwargs: _shared_client
