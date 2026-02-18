import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from auth_utils import role_required
from email_utils import send_email
from models import Department, Ticket, TicketComment, User, db

load_dotenv()

PRIORITIES = ["Baixa", "Média", "Alta"]
STATUSES = ["Aberto", "Em andamento", "Resolvido", "Fechado"]
ROLES = ["USER", "SUPPORT", "ADMIN"]

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///helpdesk.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def send_new_ticket_notification(ticket):
    support_email = os.getenv("SUPPORT_EMAIL", "").strip()
    body = (
        f"ID do chamado: {ticket.id}\n"
        f"Título: {ticket.title}\n"
        f"Descrição: {ticket.description}\n"
        f"Solicitante: {ticket.creator.name}\n"
        f"Data/Hora: {ticket.created_at.strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"Status inicial: {ticket.status}\n"
    )
    subject = f"Novo chamado #{ticket.id} - {ticket.title}"
    send_email(ticket.creator.email, subject, body)
    if support_email:
        send_email(support_email, subject, body)


def send_status_notification(ticket):
    if ticket.status not in {"Resolvido", "Fechado"}:
        return
    subject = f"Chamado #{ticket.id} atualizado para {ticket.status}"
    body = (
        f"Seu chamado #{ticket.id} foi atualizado.\n"
        f"Título: {ticket.title}\n"
        f"Novo status: {ticket.status}\n"
    )
    send_email(ticket.creator.email, subject, body)


def send_assignment_notification(ticket):
    if not ticket.assignee:
        return
    subject = f"Chamado #{ticket.id} atribuído"
    body = (
        f"Chamado #{ticket.id} foi atribuído ao técnico {ticket.assignee.name}.\n"
        f"Título: {ticket.title}\n"
        f"Status atual: {ticket.status}\n"
    )
    send_email(ticket.creator.email, subject, body)


def post_login_target(user):
    if user.role == "ADMIN":
        return url_for("admin_dashboard")
    if user.role == "SUPPORT":
        return url_for("support_tickets")
    return url_for("user_tickets")


def seed_defaults():
    default_dept = Department.query.filter_by(name="TI").first()
    if not default_dept:
        default_dept = Department(name="TI")
        db.session.add(default_dept)
        db.session.commit()

    any_admin = User.query.filter_by(role="ADMIN").first()
    if not any_admin:
        admin = User(
            name="Administrador",
            email="admin@local",
            password_hash=generate_password_hash("admin123"),
            role="ADMIN",
            department_id=default_dept.id,
            is_active=True,
        )
        db.session.add(admin)
        db.session.commit()


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("post_login_redirect"))
    return redirect(url_for("login"))


@app.route("/redirect")
@login_required
def post_login_redirect():
    return redirect(post_login_target(current_user))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("post_login_redirect"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Credenciais inválidas.", "danger")
            return render_template("login.html")

        if not user.is_active:
            flash("Usuário inativo. Contate o administrador.", "warning")
            return render_template("login.html")

        login_user(user)
        return redirect(post_login_target(user))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/meus_chamados")
@role_required("USER")
def user_tickets():
    tickets = Ticket.query.filter_by(created_by_user_id=current_user.id).order_by(Ticket.created_at.desc()).all()
    return render_template("user_tickets.html", tickets=tickets)


@app.route("/chamado/novo", methods=["GET", "POST"])
@role_required("USER")
def user_ticket_create():
    departments = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "Média")
        department_id = request.form.get("department_id", type=int)

        if not title or not description or priority not in PRIORITIES or not department_id:
            flash("Preencha os campos obrigatórios corretamente.", "danger")
            return render_template("user_ticket_create.html", departments=departments, priorities=PRIORITIES)

        ticket = Ticket(
            title=title,
            description=description,
            priority=priority,
            status="Aberto",
            created_by_user_id=current_user.id,
            assigned_to_user_id=None,
            department_id=department_id,
        )
        db.session.add(ticket)
        db.session.commit()

        comment = TicketComment(
            ticket_id=ticket.id,
            user_id=current_user.id,
            comment_text=f"Chamado aberto por {current_user.name}",
            is_internal=False,
        )
        db.session.add(comment)
        db.session.commit()

        send_new_ticket_notification(ticket)
        flash(f"Chamado #{ticket.id} aberto com sucesso.", "success")
        return redirect(url_for("ticket_detail", id=ticket.id))

    return render_template("user_ticket_create.html", departments=departments, priorities=PRIORITIES)


@app.route("/chamado/<int:id>")
@login_required
def ticket_detail(id):
    ticket = Ticket.query.get_or_404(id)
    if current_user.role == "USER" and ticket.created_by_user_id != current_user.id:
        flash("Você não pode acessar este chamado.", "danger")
        return redirect(url_for("user_tickets"))

    if current_user.role in {"SUPPORT", "ADMIN"}:
        return render_template("support_ticket_detail.html", ticket=ticket)

    public_comments = [c for c in ticket.comments if not c.is_internal]
    return render_template("ticket_detail.html", ticket=ticket, comments=public_comments)


@app.route("/chamado/<int:id>/comentario", methods=["POST"])
@role_required("USER")
def user_comment(id):
    ticket = Ticket.query.get_or_404(id)
    if ticket.created_by_user_id != current_user.id:
        flash("Você não pode comentar neste chamado.", "danger")
        return redirect(url_for("user_tickets"))

    comment_text = request.form.get("comment_text", "").strip()
    if not comment_text:
        flash("Comentário vazio.", "warning")
        return redirect(url_for("ticket_detail", id=id))

    db.session.add(TicketComment(ticket_id=ticket.id, user_id=current_user.id, comment_text=comment_text, is_internal=False))
    db.session.commit()
    return redirect(url_for("ticket_detail", id=id))


@app.route("/suporte/chamados")
@role_required("SUPPORT", "ADMIN")
def support_tickets():
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    department_id = request.args.get("department_id", type=int)
    q = request.args.get("q", "").strip()

    query = Ticket.query
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if department_id:
        query = query.filter_by(department_id=department_id)
    if q:
        if q.isdigit():
            query = query.filter(or_(Ticket.id == int(q), Ticket.title.ilike(f"%{q}%")))
        else:
            query = query.filter(Ticket.title.ilike(f"%{q}%"))

    tickets = query.order_by(Ticket.created_at.desc()).all()
    departments = Department.query.order_by(Department.name).all()
    return render_template(
        "support_tickets.html",
        tickets=tickets,
        departments=departments,
        statuses=STATUSES,
        priorities=PRIORITIES,
        filters={"status": status, "priority": priority, "department_id": department_id, "q": q},
    )


@app.route("/suporte/chamado/<int:id>")
@role_required("SUPPORT", "ADMIN")
def support_ticket_detail(id):
    ticket = Ticket.query.get_or_404(id)
    supporters = User.query.filter(User.role.in_(["SUPPORT", "ADMIN"]), User.is_active.is_(True)).order_by(User.name).all()
    return render_template("support_ticket_detail.html", ticket=ticket, supporters=supporters, statuses=STATUSES)


@app.route("/suporte/chamado/<int:id>/status", methods=["POST"])
@role_required("SUPPORT", "ADMIN")
def support_ticket_status(id):
    ticket = Ticket.query.get_or_404(id)
    status = request.form.get("status", "")
    if status not in STATUSES:
        flash("Status inválido.", "danger")
        return redirect(url_for("support_ticket_detail", id=id))

    ticket.status = status
    db.session.commit()
    send_status_notification(ticket)
    flash("Status atualizado.", "success")
    return redirect(url_for("support_ticket_detail", id=id))


@app.route("/suporte/chamado/<int:id>/atribuir", methods=["POST"])
@role_required("SUPPORT", "ADMIN")
def support_ticket_assign(id):
    ticket = Ticket.query.get_or_404(id)
    assigned_to = request.form.get("assigned_to_user_id", type=int)
    if not assigned_to:
        ticket.assigned_to_user_id = None
    else:
        user = User.query.get(assigned_to)
        if not user or user.role not in {"SUPPORT", "ADMIN"}:
            flash("Técnico inválido.", "danger")
            return redirect(url_for("support_ticket_detail", id=id))
        ticket.assigned_to_user_id = assigned_to

    db.session.commit()
    send_assignment_notification(ticket)
    flash("Atribuição atualizada.", "success")
    return redirect(url_for("support_ticket_detail", id=id))


@app.route("/suporte/chamado/<int:id>/comentario", methods=["POST"])
@role_required("SUPPORT", "ADMIN")
def support_ticket_comment(id):
    ticket = Ticket.query.get_or_404(id)
    comment_text = request.form.get("comment_text", "").strip()
    is_internal = request.form.get("is_internal") == "on"
    if not comment_text:
        flash("Comentário vazio.", "warning")
        return redirect(url_for("support_ticket_detail", id=id))

    db.session.add(TicketComment(ticket_id=ticket.id, user_id=current_user.id, comment_text=comment_text, is_internal=is_internal))
    db.session.commit()
    return redirect(url_for("support_ticket_detail", id=id))


@app.route("/admin/dashboard")
@role_required("ADMIN")
def admin_dashboard():
    stats = {s: Ticket.query.filter_by(status=s).count() for s in STATUSES}
    total_users = User.query.count()
    total_departments = Department.query.count()
    return render_template("admin_dashboard.html", stats=stats, total_users=total_users, total_departments=total_departments)


@app.route("/admin/chamados")
@role_required("ADMIN")
def admin_tickets():
    return redirect(url_for("support_tickets"))


@app.route("/admin/usuarios")
@role_required("ADMIN")
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=users)


@app.route("/admin/usuarios/novo", methods=["GET", "POST"])
@role_required("ADMIN")
def admin_user_create():
    departments = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if User.query.filter_by(email=email).first():
            flash("Email já cadastrado.", "danger")
            return render_template("admin_user_form.html", departments=departments, roles=ROLES, user=None)

        user = User(
            name=request.form.get("name", "").strip(),
            email=email,
            password_hash=generate_password_hash(request.form.get("password", "")),
            role=request.form.get("role", "USER"),
            department_id=request.form.get("department_id", type=int),
            is_active=request.form.get("is_active") == "on",
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("admin_users"))

    return render_template("admin_user_form.html", departments=departments, roles=ROLES, user=None)


@app.route("/admin/usuarios/<int:id>/editar", methods=["GET", "POST"])
@role_required("ADMIN")
def admin_user_edit(id):
    user = User.query.get_or_404(id)
    departments = Department.query.order_by(Department.name).all()

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        existing = User.query.filter(User.email == email, User.id != user.id).first()
        if existing:
            flash("Email já cadastrado.", "danger")
            return render_template("admin_user_form.html", departments=departments, roles=ROLES, user=user)

        user.name = request.form.get("name", "").strip()
        user.email = email
        user.role = request.form.get("role", "USER")
        user.department_id = request.form.get("department_id", type=int)
        user.is_active = request.form.get("is_active") == "on"

        password = request.form.get("password", "")
        if password:
            user.password_hash = generate_password_hash(password)

        db.session.commit()
        return redirect(url_for("admin_users"))

    return render_template("admin_user_form.html", departments=departments, roles=ROLES, user=user)


@app.route("/admin/usuarios/<int:id>/excluir", methods=["POST"])
@role_required("ADMIN")
def admin_user_delete(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash("Você não pode excluir seu próprio usuário.", "danger")
        return redirect(url_for("admin_users"))
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("admin_users"))


@app.route("/admin/usuarios/<int:id>/ativar_desativar", methods=["POST"])
@role_required("ADMIN")
def admin_user_toggle(id):
    user = User.query.get_or_404(id)
    user.is_active = not user.is_active
    db.session.commit()
    return redirect(url_for("admin_users"))


@app.route("/admin/setores")
@role_required("ADMIN")
def admin_departments():
    departments = Department.query.order_by(Department.name).all()
    return render_template("admin_departments.html", departments=departments)


@app.route("/admin/setores/novo", methods=["GET", "POST"])
@role_required("ADMIN")
def admin_department_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Nome é obrigatório.", "danger")
            return render_template("admin_department_form.html", department=None)
        if Department.query.filter_by(name=name).first():
            flash("Setor já existe.", "danger")
            return render_template("admin_department_form.html", department=None)
        db.session.add(Department(name=name))
        db.session.commit()
        return redirect(url_for("admin_departments"))

    return render_template("admin_department_form.html", department=None)


@app.route("/admin/setores/<int:id>/editar", methods=["GET", "POST"])
@role_required("ADMIN")
def admin_department_edit(id):
    department = Department.query.get_or_404(id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Nome é obrigatório.", "danger")
            return render_template("admin_department_form.html", department=department)
        existing = Department.query.filter(Department.name == name, Department.id != department.id).first()
        if existing:
            flash("Setor já existe.", "danger")
            return render_template("admin_department_form.html", department=department)
        department.name = name
        db.session.commit()
        return redirect(url_for("admin_departments"))

    return render_template("admin_department_form.html", department=department)


@app.route("/admin/setores/<int:id>/excluir", methods=["POST"])
@role_required("ADMIN")
def admin_department_delete(id):
    department = Department.query.get_or_404(id)
    has_users = User.query.filter_by(department_id=department.id).count() > 0
    has_tickets = Ticket.query.filter_by(department_id=department.id).count() > 0
    if has_users or has_tickets:
        flash("Não é possível excluir setor com usuários ou chamados vinculados.", "danger")
        return redirect(url_for("admin_departments"))

    db.session.delete(department)
    db.session.commit()
    return redirect(url_for("admin_departments"))


with app.app_context():
    db.create_all()
    seed_defaults()


if __name__ == "__main__":
    app.run(debug=True)
