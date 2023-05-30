"""add ondelete cascade

Revision ID: 8529cf42bb11
Revises: 864d43c0baca
Create Date: 2023-05-30 17:03:02.270707

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8529cf42bb11'
down_revision = '864d43c0baca'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('favorite_prompt_blank_favorite_prompt_id_fkey', 'favorite_prompt_blank', type_='foreignkey')
    op.create_foreign_key(None, 'favorite_prompt_blank', 'favorite_prompt', ['favorite_prompt_id'], ['id'], ondelete='cascade')
    op.drop_constraint('filled_prompt_gpt_interaction_id_fkey', 'filled_prompt', type_='foreignkey')
    op.create_foreign_key(None, 'filled_prompt', 'gpt_interaction', ['gpt_interaction_id'], ['id'], ondelete='cascade')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'filled_prompt', type_='foreignkey')
    op.create_foreign_key('filled_prompt_gpt_interaction_id_fkey', 'filled_prompt', 'gpt_interaction', ['gpt_interaction_id'], ['id'])
    op.drop_constraint(None, 'favorite_prompt_blank', type_='foreignkey')
    op.create_foreign_key('favorite_prompt_blank_favorite_prompt_id_fkey', 'favorite_prompt_blank', 'favorite_prompt', ['favorite_prompt_id'], ['id'])
    # ### end Alembic commands ###
