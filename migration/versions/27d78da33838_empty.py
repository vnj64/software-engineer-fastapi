"""empty

Revision ID: 27d78da33838
Revises: e37328518eb5
Create Date: 2024-01-15 21:26:30.755985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27d78da33838'
down_revision: Union[str, None] = 'e37328518eb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
