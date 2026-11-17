from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import AuditEvent, User, db

from app.models import Satellite
from app.simulator import COMMANDS, execute_command

from app.auth import getAuthorizedRoute

commands_bp = Blueprint("commands", __name__)

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

