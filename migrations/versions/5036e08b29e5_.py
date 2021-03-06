"""empty message

Revision ID: 5036e08b29e5
Revises: bcc2b193de63
Create Date: 2021-03-23 08:05:48.159192

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5036e08b29e5'
down_revision = 'bcc2b193de63'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('posts', sa.Column('n_likes', sa.Integer(), nullable=False))
    op.add_column('posts', sa.Column('summary', sa.String(length=200), nullable=False))
    op.add_column('users', sa.Column('name', sa.String(length=50), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'name')
    op.drop_column('posts', 'summary')
    op.drop_column('posts', 'n_likes')
    # ### end Alembic commands ###
