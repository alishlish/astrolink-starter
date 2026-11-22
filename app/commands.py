from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user

from app.models import (
    AuditEvent, User, Satellite, GroundStation, TelemetryReading,
    CommandLog, Subscriber, LegacyAccessLog
)

from app.simulator import COMMANDS, execute_command

from app.auth import getAuthorizedRoute

commands_bp = Blueprint("commands", __name__)

@commands_bp.route("/display_satellites_command", methods=["GET"])
def display_satellites_command():
    sats = []
    for s in Satellite.query.order_by(Satellite.name):
        sats.append(f"  {s.name}  {s.status:<11} {s.orbit_altitude_km:>6} km  fuel {s.fuel_remaining_pct:>5}%  "
              f"fw {s.firmware_version:<10} antenna {s.antenna_bearing_deg:>5}  {s.power_mode:<9} "
              f"{s.subscribers_served:>5} customers  {s.coverage_region}")
    return sats
        
@commands_bp.route("/display_ground_stations_command", methods=["GET"])
def display_ground_stations_command():
    stats = []
    for g in GroundStation.query.order_by(GroundStation.name):
        stats.append(f"  {g.name}  {g.status:<9} {g.ip_address:<12} {g.location}")
    return stats

@commands_bp.route("/ping_command", methods=["GET", "POST"])
def ping_command():
    if request.method == "POST":
        sat_name = request.form.get("satellite", "").strip()
        satellite = Satellite.query.filter_by(name=sat_name).first()
    execute_command(satellite, "ping")
    return getAuthorizedRoute()

@commands_bp.route("/power_mode_command", methods=["GET", "POST"])
def power_mode_command():
    if request.method == "POST":
        sat_name = request.form.get("satellite", "").strip()
        satellite = Satellite.query.filter_by(name=sat_name).first()
        mode = request.form.get("mode", "").strip()
        if mode == 1:
            mode = "normal"
        else:
            mode = "low_power"

    execute_command(satellite, "power_mode", mode)
    return getAuthorizedRoute()

@commands_bp.route("/resume_normal_command", methods=["GET", "POST"])
def resume_normal_command():
    if request.method == "POST":
        sat_name = request.form.get("satellite", "").strip()
        satellite = Satellite.query.filter_by(name=sat_name).first()
    execute_command(satellite, "resume")
    return getAuthorizedRoute()

@commands_bp.route("/safe_mode_command", methods=["GET", "POST"])
def safe_mode_command():
    if request.method == "POST":
        sat_name = request.form.get("satellite", "").strip()
        satellite = Satellite.query.filter_by(name=sat_name).first()
    execute_command(satellite, "safe_mode")
    return getAuthorizedRoute()

@commands_bp.route("/aim_satellite_command", methods=["GET", "POST"])
def aim_satellite_command():
    if request.method == "POST":
        sat_name = request.form.get("satellite", "").strip()
        satellite = Satellite.query.filter_by(name=sat_name).first()
        angle = request.form.get("aim_angle", "").strip()
    execute_command(satellite, "antenna_point", angle)
    return getAuthorizedRoute()

