"""profiles settings notifications security expansion

Revision ID: b4e2c1d9f0a1
Revises: a12a4b7309a8
Create Date: 2026-11-10 04:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b4e2c1d9f0a1'
down_revision = 'a12a4b7309a8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('gender', sa.String(length=30), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('biography', sa.Text(), nullable=True),
        sa.Column('profile_picture_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_profiles_id', 'user_profiles', ['id'], unique=False)
    op.create_index('ix_user_profiles_user_id', 'user_profiles', ['user_id'], unique=True)

    op.create_table(
        'student_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=True),
        sa.Column('emergency_contact_name', sa.String(length=255), nullable=True),
        sa.Column('emergency_contact_phone', sa.String(length=50), nullable=True),
        sa.Column('emergency_contact_relation', sa.String(length=100), nullable=True),
        sa.Column('admission_date', sa.Date(), nullable=True),
        sa.Column('academic_status', sa.String(length=50), nullable=True),
        sa.Column('academic_progress_summary', sa.Text(), nullable=True),
        sa.Column('compliance_status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_student_profiles_id', 'student_profiles', ['id'], unique=False)
    op.create_index('ix_student_profiles_user_id', 'student_profiles', ['user_id'], unique=True)
    op.create_index('ix_student_profiles_student_id', 'student_profiles', ['student_id'], unique=True)

    op.create_table(
        'lecturer_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lecturer_id', sa.Integer(), nullable=True),
        sa.Column('professional_title', sa.String(length=100), nullable=True),
        sa.Column('professional_details', sa.Text(), nullable=True),
        sa.Column('office_location', sa.String(length=255), nullable=True),
        sa.Column('office_hours', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['lecturer_id'], ['lecturers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_lecturer_profiles_id', 'lecturer_profiles', ['id'], unique=False)
    op.create_index('ix_lecturer_profiles_user_id', 'lecturer_profiles', ['user_id'], unique=True)
    op.create_index('ix_lecturer_profiles_lecturer_id', 'lecturer_profiles', ['lecturer_id'], unique=True)

    op.create_table(
        'staff_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('staff_role', sa.String(length=50), nullable=False),
        sa.Column('staff_number', sa.String(length=50), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('office', sa.String(length=255), nullable=True),
        sa.Column('responsibilities', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_staff_profiles_id', 'staff_profiles', ['id'], unique=False)
    op.create_index('ix_staff_profiles_user_id', 'staff_profiles', ['user_id'], unique=True)
    op.create_index('ix_staff_profiles_staff_role', 'staff_profiles', ['staff_role'], unique=False)
    op.create_index('ix_staff_profiles_staff_number', 'staff_profiles', ['staff_number'], unique=False)

    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token_hash', sa.String(length=128), nullable=False),
        sa.Column('device_info', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('last_active_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token_hash'),
    )
    op.create_index('ix_user_sessions_id', 'user_sessions', ['id'], unique=False)
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'], unique=False)
    op.create_index('ix_user_sessions_session_token_hash', 'user_sessions', ['session_token_hash'], unique=True)
    op.create_index('ix_user_sessions_is_active', 'user_sessions', ['is_active'], unique=False)

    op.create_table(
        'login_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('institution_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('method', sa.String(length=50), nullable=False, server_default='password'),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('failure_reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_login_history_id', 'login_history', ['id'], unique=False)
    op.create_index('ix_login_history_user_id', 'login_history', ['user_id'], unique=False)
    op.create_index('ix_login_history_institution_id', 'login_history', ['institution_id'], unique=False)
    op.create_index('ix_login_history_email', 'login_history', ['email'], unique=False)
    op.create_index('ix_login_history_success', 'login_history', ['success'], unique=False)
    op.create_index('ix_login_history_created_at', 'login_history', ['created_at'], unique=False)

    op.create_table(
        'user_activity_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('institution_id', sa.Integer(), nullable=True),
        sa.Column('activity_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_activity_logs_id', 'user_activity_logs', ['id'], unique=False)
    op.create_index('ix_user_activity_logs_user_id', 'user_activity_logs', ['user_id'], unique=False)
    op.create_index('ix_user_activity_logs_institution_id', 'user_activity_logs', ['institution_id'], unique=False)
    op.create_index('ix_user_activity_logs_activity_type', 'user_activity_logs', ['activity_type'], unique=False)
    op.create_index('ix_user_activity_logs_created_at', 'user_activity_logs', ['created_at'], unique=False)

    op.create_table(
        'user_notification_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('academic_announcements', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('course_notifications', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('registration_notifications', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('attendance_alerts', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('compliance_alerts', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('assessment_notifications', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('security_notifications', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('in_app_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('frequency', sa.String(length=30), nullable=False, server_default='immediate'),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_notification_preferences_id', 'user_notification_preferences', ['id'], unique=False)
    op.create_index('ix_user_notification_preferences_user_id', 'user_notification_preferences', ['user_id'], unique=True)

    op.create_table(
        'user_privacy_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('show_profile_picture', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('show_email', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('show_phone', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('allow_contact', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_privacy_preferences_id', 'user_privacy_preferences', ['id'], unique=False)
    op.create_index('ix_user_privacy_preferences_user_id', 'user_privacy_preferences', ['user_id'], unique=True)

    op.create_table(
        'notification_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('notification_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(length=30), nullable=False, server_default='email'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('recipient', sa.String(length=255), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notification_deliveries_id', 'notification_deliveries', ['id'], unique=False)
    op.create_index('ix_notification_deliveries_notification_id', 'notification_deliveries', ['notification_id'], unique=False)
    op.create_index('ix_notification_deliveries_user_id', 'notification_deliveries', ['user_id'], unique=False)
    op.create_index('ix_notification_deliveries_channel', 'notification_deliveries', ['channel'], unique=False)
    op.create_index('ix_notification_deliveries_status', 'notification_deliveries', ['status'], unique=False)

    op.create_table(
        'support_ticket_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ticket_id'], ['support_tickets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_support_ticket_messages_id', 'support_ticket_messages', ['id'], unique=False)
    op.create_index('ix_support_ticket_messages_ticket_id', 'support_ticket_messages', ['ticket_id'], unique=False)
    op.create_index('ix_support_ticket_messages_author_id', 'support_ticket_messages', ['author_id'], unique=False)
    op.create_index('ix_support_ticket_messages_created_at', 'support_ticket_messages', ['created_at'], unique=False)

    op.add_column('notifications', sa.Column('category', sa.String(length=50), nullable=True))
    op.add_column('notifications', sa.Column('priority', sa.String(length=20), nullable=False, server_default='normal'))
    op.add_column('notifications', sa.Column('related_type', sa.String(length=100), nullable=True))
    op.add_column('notifications', sa.Column('related_id', sa.Integer(), nullable=True))
    op.add_column('notifications', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('notifications', sa.Column('archived_at', sa.DateTime(), nullable=True))
    op.add_column('notifications', sa.Column('delivery_status', sa.String(length=30), nullable=False, server_default='in_app'))
    op.create_index('ix_notifications_category', 'notifications', ['category'], unique=False)
    op.create_index('ix_notifications_priority', 'notifications', ['priority'], unique=False)
    op.create_index('ix_notifications_is_archived', 'notifications', ['is_archived'], unique=False)

    op.add_column('user_settings', sa.Column('date_format', sa.String(length=30), nullable=False, server_default='YYYY-MM-DD'))
    op.add_column('user_settings', sa.Column('font_size', sa.String(length=20), nullable=False, server_default='medium'))
    op.add_column('user_settings', sa.Column('dashboard_preferences', sa.JSON(), nullable=True))
    op.add_column('user_settings', sa.Column('privacy_preferences', sa.JSON(), nullable=True))

    op.add_column('support_tickets', sa.Column('assigned_to_id', sa.Integer(), nullable=True))
    op.add_column('support_tickets', sa.Column('category', sa.String(length=50), nullable=False, server_default='general'))
    op.add_column('support_tickets', sa.Column('resolution_note', sa.Text(), nullable=True))
    op.add_column('support_tickets', sa.Column('closed_at', sa.DateTime(), nullable=True))
    op.create_index('ix_support_tickets_status', 'support_tickets', ['status'], unique=False)
    op.create_index('ix_support_tickets_assigned_to_id', 'support_tickets', ['assigned_to_id'], unique=False)
    op.create_foreign_key('fk_support_tickets_assigned_to_id_users', 'support_tickets', 'users', ['assigned_to_id'], ['id'], ondelete='SET NULL')


def downgrade():
    op.drop_constraint('fk_support_tickets_assigned_to_id_users', 'support_tickets', type_='foreignkey')
    op.drop_index('ix_support_tickets_assigned_to_id', table_name='support_tickets')
    op.drop_index('ix_support_tickets_status', table_name='support_tickets')
    op.drop_column('support_tickets', 'closed_at')
    op.drop_column('support_tickets', 'resolution_note')
    op.drop_column('support_tickets', 'category')
    op.drop_column('support_tickets', 'assigned_to_id')

    op.drop_column('user_settings', 'privacy_preferences')
    op.drop_column('user_settings', 'dashboard_preferences')
    op.drop_column('user_settings', 'font_size')
    op.drop_column('user_settings', 'date_format')

    op.drop_index('ix_notifications_is_archived', table_name='notifications')
    op.drop_index('ix_notifications_priority', table_name='notifications')
    op.drop_index('ix_notifications_category', table_name='notifications')
    op.drop_column('notifications', 'delivery_status')
    op.drop_column('notifications', 'archived_at')
    op.drop_column('notifications', 'is_archived')
    op.drop_column('notifications', 'related_id')
    op.drop_column('notifications', 'related_type')
    op.drop_column('notifications', 'priority')
    op.drop_column('notifications', 'category')

    op.drop_table('support_ticket_messages')
    op.drop_table('notification_deliveries')
    op.drop_table('user_privacy_preferences')
    op.drop_table('user_notification_preferences')
    op.drop_table('user_activity_logs')
    op.drop_table('login_history')
    op.drop_table('user_sessions')
    op.drop_table('staff_profiles')
    op.drop_table('lecturer_profiles')
    op.drop_table('student_profiles')
    op.drop_table('user_profiles')
