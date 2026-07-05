import os
import random
import string
from datetime import datetime, timedelta

import bleach
from flask import render_template, redirect, url_for, session, request, flash, current_app
from flask_mail import Message

from . import bp
from .forms import RegistrationForm, LoginForm, OTPForm
from ..extensions import db, bcrypt, mail
from ..models import User, OTPToken, AuditLog
from ..crypto import derive_vault_key, generate_rsa_keypair, aes_encrypt_sealed

_MAX_ATTEMPTS = 5
_LOCKOUT = timedelta(minutes=15)
_OTP_TTL = timedelta(minutes=10)


def _audit(user_id, action):
    db.session.add(AuditLog(
        user_id=user_id,
        action=action,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
    ))
    db.session.commit()


def _send_otp(user: User) -> None:
    otp = ''.join(random.choices(string.digits, k=6))
    token_hash = bcrypt.generate_password_hash(otp, rounds=8).decode()
    db.session.add(OTPToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + _OTP_TTL,
    ))
    db.session.commit()
    msg = Message('UTM SecureNotes — Verification Code', recipients=[user.email])
    msg.body = f'Your code: {otp}\n\nExpires in 10 minutes. Do not share this.'
    mail.send(msg)
    if current_app.config.get('OTP_DEV_ECHO'):
        current_app.logger.warning('DEV OTP for %s: %s', user.email, otp)
        flash(f'[DEV MODE] Your verification code is {otp}', 'info')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = bleach.clean(form.email.data.strip().lower())
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('auth/register.html', form=form)

        vault_salt = os.urandom(32)
        password_hash = bcrypt.generate_password_hash(form.password.data, rounds=12).decode()

        vault_key = derive_vault_key(form.password.data, vault_salt)
        private_pem, public_pem = generate_rsa_keypair()
        rsa_private_key_encrypted = aes_encrypt_sealed(vault_key, private_pem)

        user = User(
            email=email,
            password_hash=password_hash,
            vault_salt=vault_salt,
            rsa_public_key=public_pem.decode(),
            rsa_private_key_encrypted=rsa_private_key_encrypted,
        )
        db.session.add(user)
        db.session.flush()
        _send_otp(user)
        db.session.commit()

        session['pending_user_id'] = user.id
        flash('A verification code has been sent to your UTM email.', 'info')
        return redirect(url_for('auth.verify_otp'))
    return render_template('auth/register.html', form=form)


@bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    user_id = session.get('pending_user_id')
    if not user_id:
        return redirect(url_for('auth.register'))
    form = OTPForm()
    if form.validate_on_submit():
        record = OTPToken.query.filter_by(user_id=user_id, used=False).order_by(OTPToken.id.desc()).first()
        if not record or datetime.utcnow() > record.expires_at:
            flash('Code expired. Request a new one.', 'danger')
            return render_template('auth/verify_otp.html', form=form)
        if not bcrypt.check_password_hash(record.token_hash, form.token.data):
            flash('Invalid code.', 'danger')
            return render_template('auth/verify_otp.html', form=form)
        record.used = True
        user = User.query.get(user_id)
        user.is_verified = True
        db.session.commit()
        session.pop('pending_user_id', None)
        flash('Account verified. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/verify_otp.html', form=form)


@bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    user_id = session.get('pending_user_id')
    if not user_id:
        return redirect(url_for('auth.register'))
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.register'))
    _send_otp(user)
    flash('A new code has been sent.', 'info')
    return redirect(url_for('auth.verify_otp'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = bleach.clean(form.email.data.strip().lower())
        user = User.query.filter_by(email=email).first()

        if user:
            since = datetime.utcnow() - _LOCKOUT
            failures = AuditLog.query.filter(
                AuditLog.user_id == user.id,
                AuditLog.action == 'login_failed',
                AuditLog.created_at > since,
            ).count()
            if failures >= _MAX_ATTEMPTS:
                flash('Too many failed attempts. Try again in 15 minutes.', 'danger')
                return render_template('auth/login.html', form=form)

        if not user or not user.is_verified or not user.is_active:
            flash('Invalid credentials.', 'danger')
            if user:
                _audit(user.id, 'login_failed')
            return render_template('auth/login.html', form=form)

        if not bcrypt.check_password_hash(user.password_hash, form.password.data):
            _audit(user.id, 'login_failed')
            flash('Invalid credentials.', 'danger')
            return render_template('auth/login.html', form=form)

        vault_key = derive_vault_key(form.password.data, user.vault_salt)
        # Session fixation defense: Flask uses stateless, signed client-side
        # cookie sessions (no server-side session store/ID to "regenerate").
        # Clearing here discards any pre-auth keys (incl. one an attacker may
        # have fixed) before the new authenticated cookie is signed below, so
        # a pre-login cookie can never carry post-login privileges.
        session.clear()
        session['user_id'] = user.id
        session['is_admin'] = (user.role == 'admin')
        session['vault_key'] = vault_key.hex()
        session.permanent = True

        user.last_login_at = datetime.utcnow()
        _audit(user.id, 'login')
        return redirect(url_for('notes.list_notes'))
    return render_template('auth/login.html', form=form)


@bp.route('/logout', methods=['POST'])
def logout():
    user_id = session.get('user_id')
    if user_id:
        _audit(user_id, 'logout')
    session.clear()
    return redirect(url_for('auth.login'))
