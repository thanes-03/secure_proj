from flask import render_template, redirect, url_for, request, flash, abort, session

from . import bp
from ..decorators import admin_required
from ..extensions import db
from ..models import User, AuditLog


@bp.route('/users')
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@bp.route('/users/<int:user_id>/suspend', methods=['POST'])
@admin_required
def suspend_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot suspend another admin.', 'danger')
        return redirect(url_for('admin.users'))
    user.is_active = False
    db.session.add(AuditLog(
        user_id=session.get('user_id'),
        action=f'suspend_user:{user_id}',
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
    ))
    db.session.commit()
    flash(f'User {user.email} suspended.', 'warning')
    return redirect(url_for('admin.users'))


@bp.route('/users/<int:user_id>/activate', methods=['POST'])
@admin_required
def activate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = True
    db.session.add(AuditLog(
        user_id=session.get('user_id'),
        action=f'activate_user:{user_id}',
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
    ))
    db.session.commit()
    flash(f'User {user.email} activated.', 'success')
    return redirect(url_for('admin.users'))


@bp.route('/audit-logs')
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50)
    return render_template('admin/audit_logs.html', logs=logs)
