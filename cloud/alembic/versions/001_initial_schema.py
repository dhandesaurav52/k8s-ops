"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-08 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create clusters table
    op.create_table(
        'clusters',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cluster_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, server_default='unknown'),
        sa.Column('kubernetes_version', sa.String(length=50), nullable=False, server_default='unknown'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='CONNECTED'),
        sa.Column('node_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pod_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('namespace_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cluster_id')
    )
    op.create_index(op.f('ix_clusters_cluster_id'), 'clusters', ['cluster_id'], unique=True)
    op.create_index(op.f('ix_clusters_id'), 'clusters', ['id'], unique=False)

    # Create incidents table
    op.create_table(
        'incidents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cluster_id', sa.String(length=100), nullable=False),
        sa.Column('incident_id', sa.String(length=50), nullable=False),
        sa.Column('resource_kind', sa.String(length=50), nullable=False, server_default='Pod'),
        sa.Column('resource_namespace', sa.String(length=100), nullable=False, server_default='default'),
        sa.Column('resource_name', sa.String(length=255), nullable=False),
        sa.Column('resource_uid', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='OPEN'),
        sa.Column('current_state', sa.Text(), nullable=False, server_default=''),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='MEDIUM'),
        sa.Column('occurrences', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('diagnosis', sa.JSON(), nullable=False),
        sa.Column('investigation', sa.JSON(), nullable=False),
        sa.Column('ai_analysis', sa.JSON(), nullable=False),
        sa.Column('state_history', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'], ['clusters.cluster_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cluster_id', 'incident_id', name='uq_cluster_incident')
    )
    op.create_index(op.f('ix_incidents_cluster_id'), 'incidents', ['cluster_id'], unique=False)
    op.create_index(op.f('ix_incidents_id'), 'incidents', ['id'], unique=False)
    op.create_index(op.f('ix_incidents_incident_id'), 'incidents', ['incident_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_incidents_incident_id'), table_name='incidents')
    op.drop_index(op.f('ix_incidents_id'), table_name='incidents')
    op.drop_index(op.f('ix_incidents_cluster_id'), table_name='incidents')
    op.drop_table('incidents')

    op.drop_index(op.f('ix_clusters_id'), table_name='clusters')
    op.drop_index(op.f('ix_clusters_cluster_id'), table_name='clusters')
    op.drop_table('clusters')
