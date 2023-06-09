"""add favorite history

Revision ID: 4ce0babdaa1d
Revises: 1e96b22a1867
Create Date: 2023-06-04 18:16:15.796489

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4ce0babdaa1d'
down_revision = '1e96b22a1867'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('gpt_interaction', sa.Column('favorite', sa.BOOLEAN(), nullable=False, server_default='False'))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('gpt_interaction', 'favorite')
    # ### end Alembic commands ###
