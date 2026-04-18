from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class Usuario(db.Model):
    __tablename__ = "usuarios"
    __table_args__ = (
        db.UniqueConstraint("email", name="uq_usuarios_email"),
        db.Index("ix_usuarios_activo", "activo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    roles = db.relationship("UsuarioRol", back_populates="usuario", cascade="all, delete-orphan")
    auditorias_consultas = db.relationship("AuditoriaConsultaReporte", back_populates="usuario")
    ejecuciones_importacion_creadas = db.relationship("EjecucionImportacion", back_populates="created_by_user")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    @property
    def role_names(self) -> list[str]:
        return [usuario_rol.rol.nombre for usuario_rol in self.roles if usuario_rol.rol is not None]

    def to_auth_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "email": self.email,
            "roles": self.role_names,
        }


class UsuarioRol(db.Model):
    __tablename__ = "usuarios_roles"
    __table_args__ = (
        db.UniqueConstraint("usuario_id", "rol_id", name="uq_usuarios_roles_usuario_rol"),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    rol_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)

    usuario = db.relationship("Usuario", back_populates="roles")
    rol = db.relationship("Rol", back_populates="usuarios")
