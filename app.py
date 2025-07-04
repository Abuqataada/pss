from flask import Flask, session, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import requests
import secrets
import string
from config import Config
from flask_moment import Moment

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
mail = Mail(app)
moment = Moment(app)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(20), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    referral_code = db.Column(db.String(10), unique=True, nullable=False)
    referred_by = db.Column(db.String(10), nullable=True)
    total_balance = db.Column(db.Float, default=0.0)
    total_commission = db.Column(db.Float, default=0.0)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    investments = db.relationship('Investment', backref='user', lazy=True)
    referrals = db.relationship('Referral', backref='user', lazy=True)
    withdrawals = db.relationship('Withdrawal', backref='user', lazy=True)

class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    package_amount = db.Column(db.Float, nullable=False)
    duration_months = db.Column(db.Integer, nullable=False)
    roi_percentage = db.Column(db.Float, default=10.0)
    start_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    end_date = db.Column(db.DateTime, nullable=False)
    total_returns = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_withdrawn = db.Column(db.Boolean, default=False)
    payment_reference = db.Column(db.String(100), nullable=True)

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_user_id = db.Column(db.Integer, nullable=False)
    commission_amount = db.Column(db.Float, nullable=False)
    commission_percentage = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, declined
    request_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_date = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Helper Functions
def generate_referral_code():
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

def get_category_packages():
    return {
        'Bronze': {'packages': [500, 1000, 2000], 'commission': 5},
        'Silver': {'packages': [5000, 10000], 'commission': 7},
        'Gold': {'packages': [20000, 50000], 'commission': 9},
        'Platinum': {'packages': [100000, 250000, 500000], 'commission': 10},
        'Diamond': {'packages': [1000000, 2000000, 5000000], 'commission': 11},
        'Elite': {'packages': [10000000, 20000000, 30000000, 50000000], 'commission': 12.5}
    }

def can_refer_category(referrer_category, referee_category):
    categories = ['Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Elite']
    referrer_index = categories.index(referrer_category)
    referee_index = categories.index(referee_category)
    return referee_index <= referrer_index

def send_email(to, subject, template, **kwargs):
    msg = Message(
        subject=subject,
        recipients=[to],
        html=template,
        sender=app.config['MAIL_USERNAME']
    )
    mail.send(msg)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        
        # Validate referral code if provided
        referrer = None
        if data.get('referral_code'):
            referrer = User.query.filter_by(referral_code=data['referral_code']).first()
            if not referrer:
                flash('Invalid referral code', 'error')
                return render_template('register.html', categories=get_category_packages().keys())
            
            # Check if referrer can refer this category
            if not can_refer_category(referrer.category, data['category']):
                flash('Referrer cannot refer to this category', 'error')
                return render_template('register.html', categories=get_category_packages().keys())
        
        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            flash('Email already registered', 'error')
            return render_template('register.html', categories=get_category_packages().keys())
        
        # Create new user
        user = User(
            full_name=data['full_name'],
            email=data['email'],
            phone=data['phone'],
            password_hash=generate_password_hash(data['password']),
            bank_name=data['bank_name'],
            account_number=data['account_number'],
            account_name=data['account_name'],
            category=data['category'],
            referral_code=generate_referral_code(),
            referred_by=data.get('referral_code')
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', categories=get_category_packages().keys())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.is_active:
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Account suspended. Contact admin.', 'error')
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


























@app.route('/tc')
def tc():
    # Terms and Conditions
    return render_template('terms_and_conditions.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user stats
    total_referrals = Referral.query.filter_by(user_id=current_user.id).count()
    active_investments = Investment.query.filter_by(user_id=current_user.id, is_active=True).all()

    for investment in active_investments:
        # Convert naive datetime to aware
        if investment.end_date.tzinfo is None:
            investment.end_date = investment.end_date.replace(tzinfo=timezone.utc)
        # Compare end_date with current datetime
        investment.ready_for_withdrawal = investment.end_date <= datetime.now(timezone.utc)

    # Calculate next withdrawal date
    next_withdrawal = None
    if active_investments:
        next_withdrawal = min([inv.end_date for inv in active_investments])
    
    return render_template('dashboard.html', 
                         total_referrals=total_referrals,
                         active_investments=active_investments,
                         next_withdrawal=next_withdrawal)

@app.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    if request.method == 'POST':
        package_amount = float(request.form['package_amount'])
        duration_months = int(request.form['duration_months'])
        
        category_data = get_category_packages().get(current_user.category, {})
        packages = category_data.get('packages', [])
        commission = category_data.get('commission', 0)

        if package_amount not in packages:
            flash('Invalid package amount for your category', 'error')
            return render_template('deposit.html', packages=packages, commission=commission)
        
        # Calculate returns
        total_returns = package_amount * (1 + (0.10 * duration_months))
        
        # Store investment details in the session
        session['investment'] = {
            'package_amount': package_amount,
            'duration_months': duration_months,
            'total_returns': total_returns
        }
        
        # Redirect to Paystack payment
        return redirect(url_for('paystack_payment'))
    
    category_data = get_category_packages().get(current_user.category, {})
    return render_template('deposit.html', packages=category_data.get('packages', []), commission=category_data.get('commission', 0))

@app.route('/paystack_payment')
@login_required
def paystack_payment():
    # Retrieve investment details from the session
    investment_details = session.get('investment', {})
    
    if not investment_details:
        flash('Payment session expired or invalid', 'error')
        return redirect(url_for('deposit'))
    
    return render_template(
        'paystack_payment.html', 
        investment=investment_details,
        paystack_public_key=app.config['PAYSTACK_PUBLIC_KEY']
    )

@app.route('/verify_payment', methods=['POST'])
@login_required
def verify_payment():
    reference = request.json.get('reference')
    
    headers = {
        'Authorization': f'Bearer {app.config["PAYSTACK_SECRET_KEY"]}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['data']['status'] == 'success':
            # Retrieve investment details from the session
            investment_details = session.get('investment', {})
            
            if investment_details:
                # Create investment record
                investment = Investment(
                    user_id=current_user.id,
                    package_amount=investment_details['package_amount'],
                    duration_months=investment_details['duration_months'],
                    end_date=datetime.now(timezone.utc) + timedelta(days=30 * investment_details['duration_months']),
                    total_returns=investment_details['total_returns'],
                    payment_reference=reference
                )
                
                db.session.add(investment)
                db.session.commit()
                
                # Update user balance
                current_user.total_balance += investment.total_returns
                db.session.commit()
                
                # Process referral commission if applicable
                if current_user.referred_by:
                    referrer = User.query.filter_by(referral_code=current_user.referred_by).first()
                    if referrer:
                        category_data = get_category_packages().get(current_user.category, {})
                        commission_rate = category_data.get('commission', 0) / 100
                        commission_amount = investment_details['package_amount'] * commission_rate
                        
                        referrer.total_commission += commission_amount
                        referral = Referral(
                            user_id=referrer.id,
                            referred_user_id=current_user.id,
                            commission_amount=commission_amount,
                            commission_percentage=category_data.get('commission', 0)
                        )
                        db.session.add(referral)
                        db.session.commit()
                
                # Clear the session
                session.pop('investment', None)
                
                return jsonify({'status': 'success'})
    
    # Clear the session in case of failure
    session.pop('investment', None)
    
    return jsonify({'status': 'failed'})

@app.route('/withdrawal', methods=['GET', 'POST'])
@login_required
def withdrawal():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        
        # Check if user has withdrawable balance
        withdrawable_investments = Investment.query.filter(
            Investment.user_id == current_user.id,
            Investment.is_active == True,
            Investment.end_date <= datetime.now(timezone.utc),
            Investment.is_withdrawn == False
        ).all()
        
        total_withdrawable = sum([inv.total_returns for inv in withdrawable_investments])
        
        if amount > total_withdrawable:
            flash('Insufficient withdrawable balance', 'error')
            return render_template('withdrawal.html', withdrawable_amount=total_withdrawable)
        
        # Create withdrawal request
        withdrawal_request = Withdrawal(
            user_id=current_user.id,
            amount=amount
        )
        
        db.session.add(withdrawal_request)
        db.session.commit()
        
        flash('Withdrawal request submitted successfully', 'success')
        return redirect(url_for('dashboard'))
    
    # Calculate withdrawable amount
    withdrawable_investments = Investment.query.filter(
        Investment.user_id == current_user.id,
        Investment.is_active == True,
        Investment.end_date <= datetime.now(timezone.utc),
        Investment.is_withdrawn == False
    ).all()
    
    withdrawable_amount = sum([inv.total_returns for inv in withdrawable_investments])
    
    return render_template('withdrawal.html', withdrawable_amount=withdrawable_amount)







































@app.route('/recent-activity')
def recent_activity():
    # Get latest 3 users
    new_users = User.query.order_by(User.created_at.desc()).limit(3).all()
    
    # Get latest 3 withdrawals
    withdrawals = Withdrawal.query.order_by(Withdrawal.request_date.desc()).limit(3).all()
    
    # Get latest 3 investments
    investments = Investment.query.order_by(Investment.start_date.desc()).limit(3).all()
    
    # Combine and format all activities
    activities = []
    
    # Add new users
    for user in new_users:
        activities.append({
            'type': 'New User Registration',
            'description': f"{user.full_name} joined {user.category} category",
            'timestamp': user.created_at
        })
    
    # Add withdrawals
    for withdrawal in withdrawals:
        activities.append({
            'type': 'Withdrawal Request',
            'description': f"₦{withdrawal.amount:n} {withdrawal.status}",
            'timestamp': withdrawal.request_date
        })
    
    # Add investments
    for investment in investments:
        activities.append({
            'type': 'New Investment',
            'description': f"₦{investment.package_amount:n} investment made",
            'timestamp': investment.start_date
        })
    
    # Sort by timestamp (most recent first)
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('recent_activity.html', activities=activities[:5])  # Show top 5

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get admin stats
    total_users = User.query.count()
    total_investments = Investment.query.count()
    pending_withdrawals = Withdrawal.query.filter_by(status='pending').count()
    total_commission_paid = db.session.query(db.func.sum(Referral.commission_amount)).scalar() or 0
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_investments=total_investments,
                         pending_withdrawals=pending_withdrawals,
                         total_commission_paid=total_commission_paid)

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/suspend-user', methods=['POST'])
@login_required
def suspend_user():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json()
    user_id = data.get('user_id')
    
    # Check if the user ID provided is the same as the current user's ID
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot suspend yourself'}), 400

    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    user.is_active = False
    db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/activate-user', methods=['POST'])
@login_required
def activate_user():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json()
    user_id = data.get('user_id')
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    user.is_active = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/user-details/<int:user_id>')
@login_required
def get_user_details(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    return jsonify({
        'success': True,
        'user': {
            'full_name': user.full_name,
            'email': user.email,
            'category': user.category,
            'total_balance': user.total_balance,
            'total_commission': user.total_commission,
            'is_active': user.is_active
        }
    })

@app.route('/admin/withdrawals')
@login_required
def admin_withdrawals():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    withdrawals = Withdrawal.query.order_by(Withdrawal.request_date.desc()).all()
    return render_template('admin/withdrawals.html', withdrawals=withdrawals)

@app.route('/admin/change-password', methods=['POST'])
@login_required  # only if your admin is logged in
def change_password_admin():
    data = request.get_json()
    user_id = data.get('user_id')
    new_password = data.get('new_password')
    print(user_id)

    if not user_id or not new_password:
        return jsonify({'success': False, 'message': 'Missing data'}), 400

    user = User.query.get(user_id)
    print(user.full_name)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/admin/approve_withdrawal/<int:withdrawal_id>')
@login_required
def approve_withdrawal(withdrawal_id):
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    withdrawal = Withdrawal.query.get_or_404(withdrawal_id)
    withdrawal.status = 'approved'
    withdrawal.processed_date = datetime.now(timezone.utc)
    
    # Mark related investments as withdrawn
    user_investments = Investment.query.filter(
        Investment.user_id == withdrawal.user_id,
        Investment.is_active == True,
        Investment.end_date <= datetime.now(timezone.utc),
        Investment.is_withdrawn == False
    ).all()
    
    remaining_amount = withdrawal.amount
    for investment in user_investments:
        if remaining_amount <= 0:
            break
        if investment.total_returns <= remaining_amount:
            investment.is_withdrawn = True
            remaining_amount -= investment.total_returns
    
    db.session.commit()
    flash('Withdrawal approved successfully', 'success')
    return redirect(url_for('admin_withdrawals'))

























## Utility/helper functions
def timeago(timestamp):
    now = datetime.now(timezone.utc)
    diff = now - timestamp
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        return f"{int(seconds/60)} minutes ago"
    elif seconds < 86400:
        return f"{int(seconds/3600)} hours ago"
    else:
        return f"{int(seconds/86400)} days ago"

# Adding the filter to Jinja
app.jinja_env.filters['timeago'] = timeago


with app.app_context():
        db.create_all()

        
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
