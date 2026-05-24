<%page args="context"/>
"""${message}
Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
definition_labels = ${repr(definition_labels)}


def upgrade():
    pass


def downgrade():
    pass
