"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reportes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo", name="uq_reportes_codigo"),
    )
    op.create_index("ix_reportes_activo", "reportes", ["activo"], unique=False)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre", name="uq_roles_nombre"),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
    )
    op.create_index("ix_usuarios_activo", "usuarios", ["activo"], unique=False)

    op.create_table(
        "auditorias_consultas_reportes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("reporte_id", sa.Integer(), nullable=False),
        sa.Column("filtros_json", sa.Text(), nullable=True),
        sa.Column("fecha_consulta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resultado_ok", sa.Boolean(), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["reporte_id"], ["reportes.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auditorias_consultas_reportes_reporte_id"), "auditorias_consultas_reportes", ["reporte_id"], unique=False)
    op.create_index(op.f("ix_auditorias_consultas_reportes_usuario_id"), "auditorias_consultas_reportes", ["usuario_id"], unique=False)
    op.create_index("ix_auditorias_consultas_reportes_fecha_consulta", "auditorias_consultas_reportes", ["fecha_consulta"], unique=False)
    op.create_index("ix_auditorias_consultas_reportes_resultado_ok", "auditorias_consultas_reportes", ["resultado_ok"], unique=False)

    op.create_table(
        "ejecuciones_importacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("origen", sa.String(length=120), nullable=False),
        sa.Column("fecha_desde", sa.Date(), nullable=False),
        sa.Column("fecha_hasta", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(length=40), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("fecha_hasta >= fecha_desde", name="ck_ejecuciones_importacion_rango_fechas"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ejecuciones_importacion_created_by_user_id", "ejecuciones_importacion", ["created_by_user_id"], unique=False)
    op.create_index("ix_ejecuciones_importacion_estado", "ejecuciones_importacion", ["estado"], unique=False)
    op.create_index("ix_ejecuciones_importacion_origen", "ejecuciones_importacion", ["origen"], unique=False)

    op.create_table(
        "roles_reportes_permisos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rol_id", sa.Integer(), nullable=False),
        sa.Column("reporte_id", sa.Integer(), nullable=False),
        sa.Column("puede_ver", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["reporte_id"], ["reportes.id"]),
        sa.ForeignKeyConstraint(["rol_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rol_id", "reporte_id", name="uq_roles_reportes_permisos_rol_reporte"),
    )
    op.create_index(op.f("ix_roles_reportes_permisos_reporte_id"), "roles_reportes_permisos", ["reporte_id"], unique=False)
    op.create_index(op.f("ix_roles_reportes_permisos_rol_id"), "roles_reportes_permisos", ["rol_id"], unique=False)

    op.create_table(
        "usuarios_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("rol_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["rol_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", "rol_id", name="uq_usuarios_roles_usuario_rol"),
    )
    op.create_index(op.f("ix_usuarios_roles_rol_id"), "usuarios_roles", ["rol_id"], unique=False)
    op.create_index(op.f("ix_usuarios_roles_usuario_id"), "usuarios_roles", ["usuario_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_usuarios_roles_usuario_id"), table_name="usuarios_roles")
    op.drop_index(op.f("ix_usuarios_roles_rol_id"), table_name="usuarios_roles")
    op.drop_table("usuarios_roles")

    op.drop_index(op.f("ix_roles_reportes_permisos_rol_id"), table_name="roles_reportes_permisos")
    op.drop_index(op.f("ix_roles_reportes_permisos_reporte_id"), table_name="roles_reportes_permisos")
    op.drop_table("roles_reportes_permisos")

    op.drop_index("ix_ejecuciones_importacion_origen", table_name="ejecuciones_importacion")
    op.drop_index("ix_ejecuciones_importacion_estado", table_name="ejecuciones_importacion")
    op.drop_index("ix_ejecuciones_importacion_created_by_user_id", table_name="ejecuciones_importacion")
    op.drop_table("ejecuciones_importacion")

    op.drop_index("ix_auditorias_consultas_reportes_resultado_ok", table_name="auditorias_consultas_reportes")
    op.drop_index("ix_auditorias_consultas_reportes_fecha_consulta", table_name="auditorias_consultas_reportes")
    op.drop_index(op.f("ix_auditorias_consultas_reportes_usuario_id"), table_name="auditorias_consultas_reportes")
    op.drop_index(op.f("ix_auditorias_consultas_reportes_reporte_id"), table_name="auditorias_consultas_reportes")
    op.drop_table("auditorias_consultas_reportes")

    op.drop_index("ix_usuarios_activo", table_name="usuarios")
    op.drop_table("usuarios")

    op.drop_table("roles")
    op.drop_index("ix_reportes_activo", table_name="reportes")
    op.drop_table("reportes")
