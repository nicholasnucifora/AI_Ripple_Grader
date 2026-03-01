# Import every model module here so Alembic's autogenerate can detect all tables.
from app.models.user import User  # noqa: F401
from app.models.dev_session import MockUser, DevSession  # noqa: F401
