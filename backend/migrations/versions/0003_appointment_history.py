"""Appointment history projection, including unknown historical dates."""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0799a5ced593'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('club_officer') as batch:
        batch.alter_column('term_start', existing_type=sa.Date(), nullable=True)
        batch.add_column(sa.Column('person_id', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('org_slot_snapshot', sa.String(10), nullable=True))
        batch.add_column(sa.Column('record_source', sa.String(20), nullable=False, server_default='legacy'))
        batch.add_column(sa.Column('source_note', sa.String(500), nullable=True))
        batch.add_column(sa.Column('historical_year', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('appointed_at', sa.DateTime(), nullable=True))
        batch.add_column(sa.Column('ended_at', sa.DateTime(), nullable=True))
        batch.create_index('ix_club_officer_person_id', ['person_id'])
    op.execute("UPDATE club_officer SET person_id=(SELECT person_id FROM directory_user WHERE directory_user.id=club_officer.user_id)")


def downgrade():
    # Unknown dates cannot be converted to NOT NULL without inventing facts.
    raise RuntimeError('Appointment history downgrade needs an explicit data-preserving recovery plan')
