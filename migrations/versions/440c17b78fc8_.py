"""empty message

Revision ID: 440c17b78fc8
Revises: 7c675bb74a08
Create Date: 2020-04-02 09:47:43.457280

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '440c17b78fc8'
down_revision = '7c675bb74a08'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('grade_criteria',
    sa.Column('grade_rank', sa.Integer(), nullable=False),
    sa.Column('grade', sa.String(), nullable=False),
    sa.Column('threshold', sa.Float(), nullable=False),
    sa.Column('min_score', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('grade_rank')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('grade_criteria')
    # ### end Alembic commands ###
