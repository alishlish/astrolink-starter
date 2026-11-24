from flask import Blueprint, abort, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import AuditEvent, CommandLog, User, db

from app.models import Satellite
from app.simulator import COMMANDS, execute_command

from app.auth import getAuthorizedRoute, record_audit_event

commands_bp = Blueprint("commands", __name__)

@commands_bp.route("/ping_command", methods=["POST"])
@login_required
def ping_command():
    allowed_roles = {"junior", "midlevel", "senior", "admin"}
    if current_user.permissions not in allowed_roles:
        abort(403)

    sat_name = request.form.get("satellite", "").strip()
    satellite = Satellite.query.filter_by(name=sat_name).first()
    if satellite is None:
        abort(404)

    execute_command(satellite, "ping", user_id=current_user.id)
    return getAuthorizedRoute()

@commands_bp.route("/power_mode_command", methods=["POST"])
@login_required
def power_mode_command():
    allowed_roles = {"junior", "midlevel", "senior", "admin"}
    if current_user.permissions not in allowed_roles:
        abort(403)

    sat_name = request.form.get("satellite", "").strip()
    satellite = Satellite.query.filter_by(name=sat_name).first()
    if satellite is None:
        abort(404)

    mode = request.form.get("mode", "").strip()
    power_modes = {"0": "low_power", "1": "normal"}
    if mode not in power_modes:
        abort(400)

    execute_command(satellite, "power_mode", power_modes[mode], user_id=current_user.id)

    return getAuthorizedRoute()

@commands_bp.route("/resume_normal_command", methods=["POST"])
@login_required
def resume_normal_command():
    allowed_roles = {"junior", "midlevel", "senior", "admin"}
    if current_user.permissions not in allowed_roles:
        abort(403)

    sat_name = request.form.get("satellite", "").strip()
    satellite = Satellite.query.filter_by(name=sat_name).first()
    if satellite is None:
        abort(404)

    execute_command(satellite, "resume", user_id=current_user.id)
    return getAuthorizedRoute()

@commands_bp.route("/safe_mode_command", methods=["POST"])
@login_required
def safe_mode_command():
    allowed_roles = {"junior", "midlevel", "senior", "admin"}
    if current_user.permissions not in allowed_roles:
        abort(403)

    sat_name = request.form.get("satellite", "").strip()
    satellite = Satellite.query.filter_by(name=sat_name).first()
    if satellite is None:
        abort(404)

    execute_command(satellite, "safe_mode", user_id=current_user.id)
    return getAuthorizedRoute()

@commands_bp.route("/aim_satellite_command", methods=["POST"])
@login_required
def aim_satellite_command():
    allowed_roles = {"junior", "midlevel", "senior", "admin"}
    if current_user.permissions not in allowed_roles:
        record_audit_event(
            event_type="command_antenna_point",
            outcome="denied",
            actor_user_id=current_user.id,
            reason_code="insufficient_permissions",
        )
        abort(403)

    sat_name = request.form.get("satellite", "").strip()
    satellite = Satellite.query.filter_by(name=sat_name).first()
    if satellite is None:
        abort(404)

    angle = request.form.get("aim_angle", "").strip()
    try:
        execute_command(satellite, "antenna_point", angle, user_id=current_user.id)
    except ValueError as e:
        db.session.rollback()
        db.session.add(CommandLog(
            satellite_id=satellite.id,
            user_id=current_user.id,
            command_type="antenna_point",
            parameter=angle[:100],
            status="failed",
            description=str(e),
        ))
        db.session.commit()
        abort(400, description=str(e))
    return getAuthorizedRoute()
    

