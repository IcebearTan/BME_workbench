"""Independent many-to-many organization membership periods."""
from alembic import op
import sqlalchemy as sa
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('internal_group_member',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('directory_user.id'), nullable=False),
        sa.Column('person_id', sa.Integer(), sa.ForeignKey('person.id'), nullable=False),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('club_group.id'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False), sa.Column('status', sa.String(20), nullable=False),
        sa.Column('active_key', sa.String(80), unique=True), sa.Column('started_on', sa.Date(), nullable=False),
        sa.Column('ended_on', sa.Date()), sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('recorded_by', sa.Integer(), nullable=False), sa.Column('ended_at', sa.DateTime()),
        sa.Column('ended_by', sa.Integer()), sa.Column('reason', sa.String(200), nullable=False),
        sa.Column('end_reason', sa.String(200)),
        sa.Column('source_note', sa.String(500)), sa.Column('group_name_snapshot', sa.String(50), nullable=False),
        sa.CheckConstraint("role IN ('member','coordinator')", name='internal_member_role'),
        sa.CheckConstraint("status IN ('active','ended')", name='internal_member_status'))
    for column in ('user_id', 'person_id', 'group_id'):
        op.create_index('ix_internal_group_member_' + column, 'internal_group_member', [column])


def downgrade():
    raise RuntimeError('Preserve independent membership history before any schema rollback')
