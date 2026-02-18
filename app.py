import os
import smtplib
from email.mime.text import MIMEText
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from models import Attachment, Ticket, TicketMessage, User, db

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

CATEGORIES = ["Rede", "Hardware", "Software", "Impressora", "Acesso", "Outros"]
PRIORITIES = ["Baixa", "Média", "Alta", "Crítica"]
STATUSES = ["Aberto", "Em andamento", "Resolvido", "Fechado"]

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///helpdesk.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Faça login para acessar o sistema."


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin():
            flash("Acesso permitido apenas para ADMIN.", "danger")
            return redirect(url_for("dashboard"))
        return func(*args, **kwargs)

    return wrapper


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def send_email(subject, body, recipients):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_tls = os.getenv("SMTP_TLS", "true").lower() == "true"

    if not smtp_host or not recipients:
        return

    sender = smtp_user or "no-reply@helpdesk.local"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if smtp_tls:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(sender, recipients, msg.as_string())
    except Exception as exc:
        app.logger.warning("Falha ao enviar email: %s", exc)


def notify_new_ticket(ticket):
    support_email = os.getenv("EMAIL_SUPORTE", "suporte@empresa.com")
    subject = f"Novo chamado #{ticket.id} aberto"
    body = (
        f"Chamado #{ticket.id}\n"
        f"Assunto: {ticket.subject}\n"
        f"Categoria: {ticket.category}\n"
        f"Prioridade: {ticket.priority}\n"
        f"Status: {ticket.status}\n"
    )
    send_email(subject, body, [ticket.owner.email, support_email])


def notify_status_change(ticket):
    subject = f"Atualização do chamado #{ticket.id}"
    body = (
        f"Seu chamado #{ticket.id} foi atualizado.\n"
        f"Novo status: {ticket.status}\n"
        f"Assunto: {ticket.subject}\n"
    )
    send_email(subject, body, [ticket.owner.email])


def bootstrap_admin_user():
    if User.query.filter_by(email="admin@local").first():
        return
    admin = User(
        name="Administrador",
        email="admin@local",
        department="TI",
        password_hash=generate_password_hash("admin123"),
        role="ADMIN",
    )
    db.session.add(admin)
    db.session.commit()


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Login realizado com sucesso.", "success")
            return redirect(url_for("dashboard"))

        flash("Credenciais inválidas.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin():
        status_counts = {
            status: Ticket.query.filter_by(status=status).count() for status in STATUSES
        }
        total = Ticket.query.count()
        return render_template("dashboard_admin.html", status_counts=status_counts, total=total)

    recent_tickets = (
        Ticket.query.filter_by(user_id=current_user.id)
        .order_by(Ticket.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template("dashboard_user.html", recent_tickets=recent_tickets)


@app.route("/users")
@login_required
@admin_required
def users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("users_list.html", users=users)


@app.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def users_create():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if User.query.filter_by(email=email).first():
            flash("Já existe usuário com este email.", "danger")
            return redirect(url_for("users_create"))

        user = User(
            name=request.form.get("name", "").strip(),
            email=email,
            department=request.form.get("department", "").strip(),
            password_hash=generate_password_hash(request.form.get("password", "")),
            role=request.form.get("role", "USER"),
        )
        db.session.add(user)
        db.session.commit()
        flash("Usuário criado com sucesso.", "success")
        return redirect(url_for("users_list"))

    return render_template("users_form.html", user=None)


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def users_edit(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        exists = User.query.filter(User.email == email, User.id != user.id).first()
        if exists:
            flash("Email já está em uso.", "danger")
            return redirect(url_for("users_edit", user_id=user.id))

        user.name = request.form.get("name", "").strip()
        user.email = email
        user.department = request.form.get("department", "").strip()
        user.role = request.form.get("role", "USER")

        new_password = request.form.get("password", "")
        if new_password:
            user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        flash("Usuário atualizado com sucesso.", "success")
        return redirect(url_for("users_list"))

    return render_template("users_form.html", user=user)


@app.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def users_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Você não pode remover seu próprio usuário.", "danger")
        return redirect(url_for("users_list"))

    db.session.delete(user)
    db.session.commit()
    flash("Usuário removido com sucesso.", "success")
    return redirect(url_for("users_list"))


@app.route("/tickets/new", methods=["GET", "POST"])
@login_required
def ticket_new():
    if request.method == "POST":
        ticket = Ticket(
            user_id=current_user.id,
            category=request.form.get("category", "Outros"),
            priority=request.form.get("priority", "Baixa"),
            subject=request.form.get("subject", "").strip(),
            description=request.form.get("description", "").strip(),
            status="Aberto",
        )
        db.session.add(ticket)
        db.session.commit()

        message = TicketMessage(
            ticket_id=ticket.id,
            user_id=current_user.id,
            message=f"Chamado aberto por {current_user.name}.\n\n{ticket.description}",
        )
        db.session.add(message)

        file = request.files.get("attachment")
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_name = f"ticket_{ticket.id}_{filename}"
            save_path = UPLOAD_FOLDER / save_name
            file.save(save_path)
            attachment = Attachment(
                ticket_id=ticket.id,
                filename=filename,
                filepath=save_name,
            )
            db.session.add(attachment)

        db.session.commit()
        notify_new_ticket(ticket)
        flash(f"Chamado #{ticket.id} aberto com sucesso.", "success")
        return redirect(url_for("ticket_detail", ticket_id=ticket.id))

    return render_template("ticket_new.html", categories=CATEGORIES, priorities=PRIORITIES)


@app.route("/tickets")
@login_required
def tickets_list():
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    category = request.args.get("category", "")
    department = request.args.get("department", "")
    query_text = request.args.get("q", "").strip()

    query = Ticket.query.join(User, Ticket.user_id == User.id)

    if not current_user.is_admin():
        query = query.filter(Ticket.user_id == current_user.id)

    if status:
        query = query.filter(Ticket.status == status)
    if priority:
        query = query.filter(Ticket.priority == priority)
    if category:
        query = query.filter(Ticket.category == category)
    if department and current_user.is_admin():
        query = query.filter(User.department == department)
    if query_text:
        if query_text.isdigit():
            query = query.filter(or_(Ticket.id == int(query_text), Ticket.subject.ilike(f"%{query_text}%")))
        else:
            query = query.filter(Ticket.subject.ilike(f"%{query_text}%"))

    tickets = query.order_by(Ticket.created_at.desc()).paginate(page=page, per_page=10)

    departments = []
    if current_user.is_admin():
        departments = [
            row[0]
            for row in db.session.query(User.department)
            .distinct()
            .order_by(User.department)
            .all()
        ]

    return render_template(
        "tickets_list.html",
        tickets=tickets,
        statuses=STATUSES,
        priorities=PRIORITIES,
        categories=CATEGORIES,
        departments=departments,
        filters={
            "status": status,
            "priority": priority,
            "category": category,
            "department": department,
            "q": query_text,
        },
    )


@app.route("/tickets/<int:ticket_id>", methods=["GET", "POST"])
@login_required
def ticket_detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)

    if not current_user.is_admin() and ticket.user_id != current_user.id:
        flash("Você não tem permissão para acessar este chamado.", "danger")
        return redirect(url_for("tickets_list"))

    if request.method == "POST":
        message_text = request.form.get("message", "").strip()
        if message_text:
            message = TicketMessage(ticket_id=ticket.id, user_id=current_user.id, message=message_text)
            db.session.add(message)
            db.session.commit()
            flash("Mensagem registrada no chamado.", "success")
        return redirect(url_for("ticket_detail", ticket_id=ticket.id))

    admins = User.query.filter_by(role="ADMIN").order_by(User.name).all() if current_user.is_admin() else []
    return render_template("ticket_detail.html", ticket=ticket, statuses=STATUSES, admins=admins)


@app.route("/tickets/<int:ticket_id>/update", methods=["POST"])
@login_required
@admin_required
def ticket_update(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    ticket.status = request.form.get("status", ticket.status)
    assigned_to = request.form.get("assigned_to", "")
    solution = request.form.get("solution", "").strip()

    ticket.assigned_to = int(assigned_to) if assigned_to.isdigit() else None

    if solution and ticket.status in {"Resolvido", "Fechado"}:
        message = TicketMessage(
            ticket_id=ticket.id,
            user_id=current_user.id,
            message=f"Solução final registrada:\n{solution}",
        )
        db.session.add(message)

    db.session.commit()
    notify_status_change(ticket)
    flash("Chamado atualizado com sucesso.", "success")
    return redirect(url_for("ticket_detail", ticket_id=ticket.id))


@app.route("/tickets/export/csv")
@login_required
@admin_required
def tickets_export_csv():
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()

    def generate():
        yield "id,usuario,email,setor,categoria,prioridade,assunto,status,aberto_em\n"
        for t in tickets:
            row = [
                str(t.id),
                t.owner.name,
                t.owner.email,
                t.owner.department,
                t.category,
                t.priority,
                t.subject.replace(",", " "),
                t.status,
                t.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ]
            yield ",".join(row) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=chamados.csv"},
    )


@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


with app.app_context():
    db.create_all()
    bootstrap_admin_user()


if __name__ == "__main__":
    app.run(debug=True)
