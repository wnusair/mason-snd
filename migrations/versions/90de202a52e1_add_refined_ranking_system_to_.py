"""add_refined_ranking_system_to_tournament_performance

Revision ID: 90de202a52e1
Revises: b1c2d3e4f5g6
Create Date: 2025-11-09 18:14:38.896291

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90de202a52e1'
down_revision = 'b1c2d3e4f5g6'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns for refined ranking system
    with op.batch_alter_table('tournament__performance', schema=None) as batch_op:
        batch_op.add_column(sa.Column('overall_rank', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('total_competitors', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('decay_coefficient', sa.Float(), nullable=True))


def downgrade():
    # Remove the new columns
    with op.batch_alter_table('tournament__performance', schema=None) as batch_op:
        batch_op.drop_column('decay_coefficient')
        batch_op.drop_column('total_competitors')
        batch_op.drop_column('overall_rank')
