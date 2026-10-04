from functools import wraps
from flask import Flask, render_template, request, redirect, flash, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blue.db'
app.config['SECRET_KEY'] = 'blue-accounting-secret-key-2026-pro'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(100), default='fa-calculator')


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    image = db.Column(db.String(200))


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.utcnow)


class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)


# =========================
# ADMIN LOGIN PROTECTION
# =========================

@app.before_request
def requires_admin_login():

    if request.path.startswith('/admin'):

        # Login page should remain accessible
        if request.path == '/admin/login':
            return

        # If not logged in, send user to login page
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))


# =========================
# ADMIN LOGIN
# =========================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():

    if session.get('admin_logged_in'):
        return redirect('/admin/')

    message = ""

    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')

        user = AdminUser.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):

            session['admin_logged_in'] = True
            session['admin_user_id'] = user.id
            session['admin_username'] = user.username

            return redirect('/admin/')

        message = "Invalid username or password."

    return render_template(
        'admin_login.html',
        message=message
    )


# =========================
# ADMIN LOGOUT
# =========================

@app.route('/admin/logout')
def admin_logout():

    session.pop('admin_logged_in', None)
    session.pop('admin_user_id', None)
    session.pop('admin_username', None)

    return redirect(url_for('admin_login'))


# =========================
# CHANGE ADMIN PASSWORD
# =========================

class changepasswordView(BaseView):

    @expose('/', methods=['GET', 'POST'])
    def index(self):

        msg = ""

        user_id = session.get('admin_user_id')

        user = AdminUser.query.get(user_id)

        if not user:
            return redirect(url_for('admin_login'))

        if request.method == 'POST':

            new_password = request.form.get('password')
            new_username = request.form.get('username')

            if new_username and new_password:

                # Check if another admin already uses this username
                existing_user = AdminUser.query.filter(
                    AdminUser.username == new_username,
                    AdminUser.id != user.id
                ).first()

                if existing_user:

                    msg = "This username is already in use."

                else:

                    user.username = new_username
                    user.password_hash = generate_password_hash(new_password)

                    db.session.commit()

                    session['admin_username'] = new_username

                    msg = (
                        "Success! Username and password "
                        "changed successfully."
                    )

        return self.render(
            'admin_change_password.html',
            message=msg,
            current_user=user.username
        )


# =========================
# FLASK ADMIN
# =========================

admin = Admin(
    app,
    name='Blue. Accounting'
)

admin.add_view(ModelView(Service, db.session))
admin.add_view(ModelView(BlogPost, db.session))
admin.add_view(ModelView(ContactMessage, db.session))

admin.add_view(
    changepasswordView(
        name='Change Password',
        endpoint='change_password'
    )
)


# =========================
# EMAIL NOTIFICATION
# =========================

def send_email_notification(name, user_email, message_body):

    print(
        f"New Contact: {name} ({user_email}) - {message_body}"
    )

    return True


# =========================
# WEBSITE ROUTES
# =========================

@app.route('/')
def home():

    services = Service.query.all()

    return render_template(
        'home.html',
        services=services
    )


@app.route('/about')
def about():

    return render_template('about.html')


@app.route('/services')
def services_page():

    all_services = Service.query.all()

    return render_template(
        'services.html',
        services=all_services
    )


@app.route('/blog')
def blog():

    posts = BlogPost.query.order_by(
        BlogPost.date_posted.desc()
    ).all()

    return render_template(
        'blog.html',
        posts=posts
    )


@app.route('/testimonials')
def testimonials():

    return render_template('testimonials.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():

    if request.method == 'POST':

        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        new_msg = ContactMessage(
            name=name,
            email=email,
            message=message
        )

        db.session.add(new_msg)
        db.session.commit()

        send_email_notification(
            name,
            email,
            message
        )

        flash(
            'Your message has been sent successfully!',
            'success'
        )

        return redirect(url_for('contact'))

    return render_template('contact.html')


# =========================
# DATABASE SETUP
# =========================

if __name__ == '__main__':

    with app.app_context():

        db.create_all()

        # Create default admin only if one does not exist
        if AdminUser.query.count() == 0:

            default_admin = AdminUser(
                username='client',
                password_hash=generate_password_hash('Blue@2026')
            )

            db.session.add(default_admin)
            db.session.commit()

        if Service.query.count() == 0:

            default_services = [

                Service(
                    title="Full Cycle Bookkeeping",
                    description="Complete bookkeeping from start to finish.",
                    icon="fa-book"
                ),

                Service(
                    title="Accounts Receivable",
                    description="Manage incoming payments and invoicing.",
                    icon="fa-hand-holding-usd"
                ),

                Service(
                    title="Accounts Payable",
                    description="Track vendor bills and outgoing payments.",
                    icon="fa-file-invoice-dollar"
                ),

                Service(
                    title="Backlog Cleanup",
                    description="Clean up messy books and make them audit-ready.",
                    icon="fa-broom"
                ),

                Service(
                    title="Bank & Account Reconciliation",
                    description="Reconcile bank accounts with 100%  accuracy.",
                    icon="fa-university"
                ),

                Service(
                    title="Financial Reporting",
                    description="P&L, Balance Sheet and custom reports.",
                    icon="fa-chart-line"
                )
            ]

            db.session.add_all(default_services)
            db.session.commit()

    app.run(debug=True)
