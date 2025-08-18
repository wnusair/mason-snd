"""Add publishing feature to rosters and user published rosters tracking

Revision ID: 7a522f566f44
Revises: e1493ff6b768
Create Date: 2025-08-17 21:45:52.807672

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a522f566f44'
down_revision = 'e1493ff6b768'
branch_labels = None
depends_on = None


def upgrade():
    # Roster table already has the columns, just create user_published_rosters table
    op.create_table('user_published_rosters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('roster_id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('notified', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['event.id'], ),
        sa.ForeignKeyConstraint(['roster_id'], ['roster.id'], ),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournament.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop user_published_rosters table
    op.drop_table('user_published_rosters')
    
    # Remove publishing fields from roster table
    op.drop_column('roster', 'tournament_id')
    op.drop_column('roster', 'published_at')
    op.drop_column('roster', 'published')
