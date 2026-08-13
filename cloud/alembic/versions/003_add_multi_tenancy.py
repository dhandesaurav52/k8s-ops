"""003_add_multi_tenancy

Revision ID: 003_add_multi_tenancy
Revises: 1c527bd332c1
Create Date: 2026-08-13 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_add_multi_tenancy'
down_revision: Union[str, None] = '1c527bd332c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_organizations_org_id'), 'organizations', ['org_id'], unique=True)
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    # Insert default organization
    op.execute(
        "INSERT INTO organizations (org_id, name, slug, created_at, updated_at) "
        "VALUES ('org-default', 'Default Organization', 'default-org', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )

    # 2. Add user_id to users if not present
    try:
        op.add_column('users', sa.Column('user_id', sa.String(length=100), nullable=True))
        op.execute("UPDATE users SET user_id = 'user-admin' WHERE username = 'admin' OR user_id IS NULL")
        op.create_index(op.f('ix_users_user_id'), 'users', ['user_id'], unique=True)
    except Exception:
        pass

    # 3. Create memberships table
    op.create_table(
        'memberships',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('role', sa.String(length=50), server_default='admin', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.org_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Add organization_id and agent_token to clusters
    op.add_column('clusters', sa.Column('organization_id', sa.String(length=100), server_default='org-default', nullable=False))
    op.add_column('clusters', sa.Column('agent_token', sa.String(length=255), server_default='legacy-token', nullable=False))
    op.create_index(op.f('ix_clusters_organization_id'), 'clusters', ['organization_id'], unique=False)
    op.create_index(op.f('ix_clusters_agent_token'), 'clusters', ['agent_token'], unique=False)

    # 5. Add organization_id to incidents
    op.add_column('incidents', sa.Column('organization_id', sa.String(length=100), server_default='org-default', nullable=False))
    op.create_index(op.f('ix_incidents_organization_id'), 'incidents', ['organization_id'], unique=False)

    # 6. Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.String(length=100), nullable=False),
        sa.Column('cluster_id', sa.String(length=100), nullable=True),
        sa.Column('actor', sa.String(length=100), nullable=False, server_default='system'),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.org_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_incidents_organization_id'), table_name='incidents')
    op.drop_column('incidents', 'organization_id')
    op.drop_index(op.f('ix_clusters_agent_token'), table_name='clusters')
    op.drop_index(op.f('ix_clusters_organization_id'), table_name='clusters')
    op.drop_column('clusters', 'agent_token')
    op.drop_column('clusters', 'organization_id')
    op.drop_table('memberships')
    op.drop_table('organizations')
