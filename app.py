
import multiprocessing,os,sys
import psycopg2,psycopg2.extras

from flask import Flask,current_app,abort,flash,g,redirect,request,render_template, \
                  session,url_for
from flask.ext.login import LoginManager,login_required,login_user,logout_user, \
                            fresh_login_required,confirm_login,current_user
from flask_mail import Mail,Message,email_dispatched

import db
from gmail import GMail

from user import User
from forms import LoginForm
from admin import admin_required

# Config
DEBUG = os.environ.get('DEBUG',False)
SECRET_KEY = os.urandom(32)
MAIL_USERNAME = 'paul.chakravarti@gmail.com'
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
MAIL_FAIL_SILENTLY = False
DEFAULT_MAIL_SENDER = ('Paul Chakravarti', 'paul.chakravarti@gmail.com')

# Create App
app = Flask(__name__)
app.config.from_object(__name__)

gmail = GMail(app)

# Database connection
TABLES = (
    ('users',   '''id SERIAL PRIMARY KEY,
                   name TEXT NOT NULL,
                   password TEXT NOT NULL,
                   active BOOLEAN NOT NULL DEFAULT true,
                   admin BOOLEAN NOT NULL DEFAULT false,
                   properties HSTORE NOT NULL DEFAULT ''::hstore,
                   inserted TIMESTAMP NOT NULL DEFAULT now()'''),
)

DB_URL = None
db.connect(DB_URL)
db.init_db(TABLES)

# Flask-Login
login_manager = LoginManager()
login_manager.setup_app(app)
login_manager.login_view = "login"
login_manager.refresh_view = "refresh"
login_manager.needs_refresh_message = u"Please re-authenticate to access this page"

@login_manager.user_loader
def load_user(userid):
    user = db.select_one('users',{'id':int(userid)})
    return User(user) if user else None 

def text(msg,code=200):
    return (msg,code,{'Content-type':'text/plain'})

@app.route('/')
def index():
    return render_template("index.html",message="Hello",user=current_user)

@app.route('/msg/<to>/<subject>/<content>')
def msg(to,subject,content):
    msg = Message(subject,recipients=[to])
    msg.body = content
    pid = gmail.bg_send(msg)
    return text("Sent Message: %d" % pid)

@app.route('/login',methods=('GET','POST',))
def login():
    form = LoginForm()
    if form.validate_on_submit():
        login_user(form.user,remember=True)
        flash("Logged In (%s)" % form.user.name,"success")
        return redirect(request.args.get("next") or url_for("index"))
    return render_template('login.html',login_form=form)

@app.route('/users')
@login_required
def users():
    return render_template('users.html',rows=db.select('users',order=('id',)),
                                        columns=('id','name','active','admin','properties'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged Out","success")
    return redirect(url_for("index"))

@app.route('/refresh',methods=('GET','POST',))
def refresh():
    form = LoginForm()
    if form.validate_on_submit():
        confirm_login()
        flash("Authentication refreshed","success")
        return redirect(request.args.get("next") or url_for("index"))
    return render_template('login.html',login_form=form)

@app.route('/admin')
@login_required
@admin_required
def admin():
    return render_template("index.html",message="Admin",user=current_user) 

@app.route('/fresh')
@fresh_login_required
def fresh():
    return render_template("index.html",message="Fresh",user=current_user) 

@app.route('/ping')
@login_required
def ping():
    return text(db.query_one('select version()')['version'])

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

