"""Initial database schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-02-26

Creates the core tables:
- users: GitHub OAuth users
- runs: Agent run sessions
- fixes: Individual fixes applied per run
- ci_events: CI pipeline events per run iteration
"""
from alembic import op
import sqlalchemy as sa


revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === users table ===
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('github_id', sa.Integer(), nullable=False),
        sa.Column('github_username', sa.String(255), nullable=False),
        sa.Column('github_email', sa.String(255), nullable=True),
        sa.Column('github_avatar_url', sa.String(512), nullable=True),
        sa.Column('github_access_token', sa.String(512), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_users'),
        sa.UniqueConstraint('github_id', name='uq_users_github_id'),
        sa.UniqueConstraint('github_username', name='uq_users_github_username'),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_github_id', 'users', ['github_id'])
    op.create_index('ix_users_github_username', 'users', ['github_username'])

    # === runs table ===
    op.create_table(
        'runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('repo_url', sa.String(512), nullable=False),
        sa.Column('repo_owner', sa.String(255), nullable=False),
        sa.Column('repo_name', sa.String(255), nullable=False),
        sa.Column('team_name', sa.String(255), nullable=False),
        sa.Column('team_leader', sa.String(255), nullable=False),
        sa.Column('mode', sa.String(50), nullable=False, default='run-agent'),
        sa.Column('max_iterations', sa.Integer(), nullable=False, default=5),
        sa.Column('branch_name', sa.String(255), nullable=True),
        sa.Column('pr_url', sa.String(512), nullable=True),
        sa.Column('final_status', sa.String(20), nullable=False, default='RUNNING'),
        sa.Column('total_failures_detected', sa.Integer(), nullable=False, default=0),
        sa.Column('total_fixes_applied', sa.Integer(), nullable=False, default=0),
        sa.Column('total_commits', sa.Integer(), nullable=False, default=0),
        sa.Column('iterations_used', sa.Integer(), nullable=False, default=0),
        sa.Column('base_score', sa.Integer(), nullable=False, default=100),
        sa.Column('speed_bonus', sa.Integer(), nullable=False, default=0),
        sa.Column('efficiency_penalty', sa.Integer(), nullable=False, default=0),
        sa.Column('final_score', sa.Integer(), nullable=False, default=0),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_time_seconds', sa.Float(), nullable=True),
        sa.Column('results_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_runs'),
        sa.UniqueConstraint('run_id', name='uq_runs_run_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_runs_user_id_users', ondelete='CASCADE'),
    )
    op.create_index('ix_runs_id', 'runs', ['id'])
    op.create_index('ix_runs_run_id', 'runs', ['run_id'])
    op.create_index('ix_runs_user_id', 'runs', ['user_id'])
    op.create_index('ix_runs_repo_url', 'runs', ['repo_url'])
    op.create_index('ix_runs_repo_owner', 'runs', ['repo_owner'])
    op.create_index('ix_runs_repo_name', 'runs', ['repo_name'])
    op.create_index('ix_runs_final_status', 'runs', ['final_status'])

    # === fixes table ===
    op.create_table(
        'fixes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('bug_type', sa.String(50), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('commit_message', sa.String(512), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('diff', sa.Text(), nullable=True),
        sa.Column('before_snippet', sa.Text(), nullable=True),
        sa.Column('after_snippet', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_fixes'),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], name='fk_fixes_run_id_runs', ondelete='CASCADE'),
    )
    op.create_index('ix_fixes_id', 'fixes', ['id'])
    op.create_index('ix_fixes_run_id', 'fixes', ['run_id'])
    op.create_index('ix_fixes_bug_type', 'fixes', ['bug_type'])
    op.create_index('ix_fixes_status', 'fixes', ['status'])

    # === ci_events table ===
    op.create_table(
        'ci_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('iteration', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('iteration_label', sa.String(20), nullable=True),
        sa.Column('ran_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_ci_events'),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], name='fk_ci_events_run_id_runs', ondelete='CASCADE'),
    )
    op.create_index('ix_ci_events_id', 'ci_events', ['id'])
    op.create_index('ix_ci_events_run_id', 'ci_events', ['run_id'])


def downgrade() -> None:
    op.drop_table('ci_events')
    op.drop_table('fixes')
    op.drop_table('runs')
    op.drop_table('users')
