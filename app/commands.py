from flask import Blueprint, abort, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user

from app.models import (
    AuditEvent, User, Satellite, GroundStation, TelemetryReading,
    CommandLog, Subscriber, LegacyAccessLog, db
)

from app.simulator import COMMANDS, execute_command

from app.auth import getAuthorizedRoute, record_audit_event

from show_data import fmt

commands_bp = Blueprint("commands", __name__)


def require_roles(event_type, allowed_roles):
    if current_user.permissions not in allowed_roles:
        record_audit_event(
            event_type=event_type,
            outcome="denied",
            actor_user_id=current_user.id,
            reason_code="insufficient_permissions",
        )
        abort(403)


def run_satellite_command(command_type, parameter=None):
    sat_name = request.form.get("satellite", "").strip()
    satellite = Satellite.query.filter_by(name=sat_name).first()
    if satellite is None:
        abort(404)

    try:
        execute_command(satellite, command_type, parameter, user_id=current_user.id)
    except ValueError as exc:
        db.session.rollback()
        db.session.add(CommandLog(
            satellite_id=satellite.id,
            user_id=current_user.id,
            command_type=command_type,
            parameter=(parameter or "")[:100] or None,
            description=str(exc),
            status="failed",
        ))
        db.session.commit()
        abort(400, description=str(exc))

    return getAuthorizedRoute()


@commands_bp.route("/display_satellites_command", methods=["GET"])
@login_required
def display_satellites_command():
    require_roles("display_satellites_command", {"junior", "midlevel", "senior", "admin"})
    sats = []
    for s in Satellite.query.order_by(Satellite.name):
        sats.append(f"  {s.name}  {s.status:<11} {s.orbit_altitude_km:>6} km  fuel {s.fuel_remaining_pct:>5}%  "
              f"fw {s.firmware_version:<10} antenna {s.antenna_bearing_deg:>5}  {s.power_mode:<9} "
              f"{s.subscribers_served:>5} customers  {s.coverage_region}")
    return sats
        
@commands_bp.route("/display_ground_stations_command", methods=["GET"])
@login_required
def display_ground_stations_command():
    require_roles("display_ground_stations_command", {"junior", "midlevel", "senior", "admin"})
    stats = []
    for g in GroundStation.query.order_by(GroundStation.name):
        stats.append(f"  {g.name}  {g.status:<9} {g.ip_address:<12} {g.location}")
    return stats

@commands_bp.route("/display_telemetry_command", methods=["GET"])
@login_required
def display_telemetry_command():
    require_roles("display_telemetry_command", {"midlevel", "senior", "admin"})
    tels = []
    for t in TelemetryReading.query.order_by(TelemetryReading.timestamp.desc()).limit(20):
        gs = t.ground_station.name if t.ground_station else "NONE"
        tels.append(f"  {fmt(t.timestamp)}  {t.satellite.name}  via {gs:<6} battery {t.battery_pct:>5}%  "
              f"temp {t.temperature_c:>6} C  signal {t.signal_dbm} dBm  alt {t.altitude_km} km")

    return tels


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
    

@commands_bp.route("/adjust_orbit_command", methods=["POST"])
@login_required
def adjust_orbit_command():
    require_roles("command_orbit_adjust", {"senior"})
    return run_satellite_command("orbit_adjust", request.form.get("km_change", "").strip())

@commands_bp.route("/firmware_update_command", methods=["POST"])
@login_required
def firmware_update_command():
    require_roles("command_firmware_update", {"senior"})
    return run_satellite_command("firmware_update", request.form.get("version", "").strip())

@commands_bp.route("/deorbit_satellite_command", methods=["POST"])
@login_required
def deorbit_satellite_command():
    require_roles("command_deorbit", {"senior"})
    return run_satellite_command("deorbit")

@commands_bp.route("/display_subscribers_command", methods=["GET"])
@login_required
def display_subscribers_command():
    require_roles("display_subscribers_command", {"admin"})
    subscribers = []
    for s in Subscriber.query.order_by(Subscriber.id):
        subscribers.append(f"  {s.full_name:<16} {s.email:<30} {s.phone}  {s.home_address}")
    return subscribers

@commands_bp.route("/display_users_command", methods=["GET"])
@login_required
def display_users_command():
    require_roles("display_users_command", {"admin"})
    users = []
    for u in User.query.order_by(User.id):
        users.append(f"  {u.username:<10} {u.display_name:<17} {u.job_title:<20} {u.permissions:<20} {u.employment_status}")
    return users

@commands_bp.route("/display_LegacyAccessLog_command", methods=["GET"])
@login_required
def display_LegacyAccessLog_command():
    require_roles("display_LegacyAccessLog_command", {"admin"})
    access_log = []
    for a in LegacyAccessLog.query.order_by(LegacyAccessLog.timestamp.desc()).limit(40):
        access_log.append(f"  {fmt(a.timestamp)}  {a.username:<10} {a.ip_address:<14} {'ok' if a.success else 'FAILED'}")    
    return access_log

@commands_bp.route("/display_AuditEvents_command", methods=["GET"])
@login_required
def display_AuditEvents_command():
    require_roles("display_AuditEvents_command", {"admin"})
    events = []
    for a in AuditEvent.query.order_by(AuditEvent.timestamp.desc()):
        events.append(f"  {fmt(a.timestamp)}  {a.event_type:<14} {a.outcome:<14}")  
    return events

@commands_bp.route("/add_user_command", methods=["POST"])
@login_required
def add_user_command():
    require_roles("add_user_command", {"admin"})
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    display_name = request.form.get("display_name", "").strip()
    job_title = request.form.get("job_title", "").strip()
    permissions = request.form.get("permissions", "").strip()
    if permissions not in {"visitor", "junior", "midlevel", "senior", "admin"}:
        abort(400)

    if not username or not password:
        abort(400)
    if User.query.filter_by(username=username).first() is not None:
        abort(409)

    user = User(
        username=username,
        display_name=display_name,
        job_title=job_title,
        permissions=permissions,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return getAuthorizedRoute()

@commands_bp.route("/remove_user_command", methods=["POST"])
@login_required
def remove_user_command():
    require_roles("remove_user_command", {"admin"})
    username = request.form.get("username", "").strip()
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)

    user.employment_status = "left"
    db.session.commit()

    return getAuthorizedRoute()

@commands_bp.route("/assign_user_permissions_command", methods=["POST"])
@login_required
def assign_user_permissions_command():
    require_roles("assign_user_permissions_command", {"admin"})
    username = request.form.get("username", "").strip()
    permissions = request.form.get("permissions", "").strip()
    if permissions not in {"visitor", "junior", "midlevel", "senior", "admin"}:
        abort(400)

    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    user.permissions = permissions
    db.session.commit()

    return getAuthorizedRoute()
