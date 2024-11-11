from app import db
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('statistics', sa.Column('rank', sa.Integer(), nullable=True))
    op.add_column('statistics', sa.Column('group', sa.String(20), nullable=True))

def downgrade():
    op.drop_column('statistics', 'rank')
    op.drop_column('statistics', 'group')
