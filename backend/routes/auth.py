"""Auth routes — register, login, refresh."""

import logging

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)

from app import limiter
from models.user import UserPublic

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required", "code": 400}), 400

    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    role = data.get("role", "teacher")

    if not email or not password:
        return jsonify({"error": "Email and password required", "code": 400}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters", "code": 400}), 400

    if role not in ("teacher", "admin"):
        return jsonify({"error": "Role must be 'teacher' or 'admin'", "code": 400}), 400

    user_service = current_app.config["USER_SERVICE"]
    try:
        user = user_service.register(email, password, role)
    except ValueError as e:
        return jsonify({"error": str(e), "code": 409}), 409

    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    logger.info("User registered: %s (role=%s)", user.email, user.role)
    return jsonify({
        "user": UserPublic.model_validate(user.model_dump()).model_dump(mode="json"),
        "access_token": access_token,
        "refresh_token": refresh_token,
    }), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
@limiter.limit("10/minute")
def login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required", "code": 400}), 400

    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password required", "code": 400}), 400

    user_service = current_app.config["USER_SERVICE"]
    user = user_service.authenticate(email, password)
    if not user:
        return jsonify({"error": "Invalid email or password", "code": 401}), 401

    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    logger.info("User logged in: %s", user.email)
    return jsonify({
        "user": UserPublic.model_validate(user.model_dump()).model_dump(mode="json"),
        "access_token": access_token,
        "refresh_token": refresh_token,
    })


@auth_bp.route("/api/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({"access_token": access_token})
