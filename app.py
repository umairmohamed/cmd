from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Customer
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///customer_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'

db.init_app(app)

with app.app_context():
    db.create_all()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    customers = Customer.query.all()
    total_credit = sum(c.credit_balance for c in customers)
    return render_template('dashboard.html', customers=customers, total_credit=total_credit)

@app.route('/add_customer', methods=['POST'])
@login_required
def add_customer():
    name = request.form['name']
    mobile = request.form['mobile']
    # Optional initial credit, defaulting to 0
    try:
        initial_credit = float(request.form.get('initial_credit', 0))
    except ValueError:
        initial_credit = 0.0

    if not re.fullmatch(r'\d{9}', mobile):
        flash('Invalid mobile number. It must be exactly 9 digits.')
        return redirect(url_for('dashboard'))

    new_customer = Customer(name=name, mobile=mobile, credit_balance=initial_credit)
    db.session.add(new_customer)
    db.session.commit()

    flash('Customer added successfully!')
    return redirect(url_for('dashboard'))

@app.route('/add_payment/<int:customer_id>', methods=['POST'])
@login_required
def add_payment(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    data = request.get_json()
    amount = float(data.get('amount', 0))

    if amount <= 0:
        return {'error': 'Invalid amount'}, 400

    customer.credit_balance -= amount
    db.session.commit()

    # Recalculate total credit
    total_credit = db.session.query(db.func.sum(Customer.credit_balance)).scalar() or 0

    return {
        'success': True,
        'new_balance': customer.credit_balance,
        'total_credit': total_credit
    }

if __name__ == '__main__':
    app.run(debug=True)
