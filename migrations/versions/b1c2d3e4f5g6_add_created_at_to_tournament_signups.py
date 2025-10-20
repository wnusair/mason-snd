"""Add created_at to Tournament_Signups

Revision ID: b1c2d3e4f5g6
Revises: f9g8h7i6j5k4
Create Date: 2025-10-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
import pytz

EST = pytz.timezone('US/Eastern')

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5g6'
down_revision = 'a86e3b5c0bea'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tournament__signups', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
    
    op.execute(f"UPDATE tournament__signups SET created_at = '{datetime.now(EST)}'")
    
    with op.batch_alter_table('tournament__signups', schema=None) as batch_op:
        batch_op.alter_column('created_at', nullable=False)


def downgrade():
    with op.batch_alter_table('tournament__signups', schema=None) as batch_op:
        batch_op.drop_column('created_at')
