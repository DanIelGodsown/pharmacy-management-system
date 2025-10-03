from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, timedelta
from models import db, User, Drug, Sale, Purchase, Supplier
from functools import wraps
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pharmacy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Inject today's date into all templates
@app.context_processor
def inject_today():
    return {'today': datetime.now().date()}

# Login required decorator
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('Access denied. Insufficient permissions.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required()
def dashboard():
    # Get dashboard statistics
    total_drugs = Drug.query.count()
    low_stock_drugs = Drug.query.filter(Drug.quantity < 10).count()
    
    # Expiry alerts
    soon_date = datetime.now().date() + timedelta(days=90)
    expiring_soon = Drug.query.filter(Drug.expiry_date <= soon_date, Drug.expiry_date > datetime.now().date()).count()
    expired_drugs = Drug.query.filter(Drug.expiry_date <= datetime.now().date()).count()
    
    # Recent sales
    recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                         total_drugs=total_drugs,
                         low_stock_drugs=low_stock_drugs,
                         expiring_soon=expiring_soon,
                         expired_drugs=expired_drugs,
                         recent_sales=recent_sales)

# Drug Management Routes - FIXED
@app.route('/drugs')
@login_required()
def drugs():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    expiry_filter = request.args.get('expiry_filter', '')
    stock_filter = request.args.get('stock_filter', '')
    
    query = Drug.query
    
    if search:
        query = query.filter(Drug.name.ilike(f'%{search}%'))
    if category:
        query = query.filter_by(category=category)
    if expiry_filter:
        today = datetime.now().date()
        if expiry_filter == 'expired':
            query = query.filter(Drug.expiry_date <= today)
        elif expiry_filter == 'expiring_soon':
            soon_date = today + timedelta(days=90)
            query = query.filter(Drug.expiry_date <= soon_date, Drug.expiry_date > today)
    if stock_filter == 'low_stock':
        query = query.filter(Drug.quantity < 10)
    
    drugs = query.order_by(Drug.name).all()
    
    # Get distinct categories for filter dropdown
    categories = db.session.query(Drug.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]  # Extract from tuple and filter None
    
    return render_template('drugs.html', drugs=drugs, categories=categories)

@app.route('/add_drug', methods=['GET', 'POST'])
@login_required(role='admin')
def add_drug():
    if request.method == 'POST':
        try:
            # Convert empty string to None for optional fields
            batch_no = request.form['batch_no'] or 'N/A'
            manufacturer = request.form['manufacturer'] or 'Unknown'
            
            drug = Drug(
                name=request.form['name'],
                category=request.form['category'],
                batch_no=batch_no,
                manufacturer=manufacturer,
                quantity=int(request.form['quantity']),
                cost_price=float(request.form['cost_price']),
                selling_price=float(request.form['selling_price']),
                expiry_date=datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
            )
            db.session.add(drug)
            db.session.commit()
            flash('Drug added successfully!', 'success')
            return redirect(url_for('drugs'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding drug: {str(e)}', 'danger')
    
    return render_template('add_drug.html')

@app.route('/edit_drug/<int:drug_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_drug(drug_id):
    drug = Drug.query.get_or_404(drug_id)
    
    if request.method == 'POST':
        try:
            drug.name = request.form['name']
            drug.category = request.form['category']
            drug.batch_no = request.form['batch_no']
            drug.manufacturer = request.form['manufacturer']
            drug.quantity = int(request.form['quantity'])
            drug.cost_price = float(request.form['cost_price'])
            drug.selling_price = float(request.form['selling_price'])
            drug.expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
            
            db.session.commit()
            flash('Drug updated successfully!', 'success')
            return redirect(url_for('drugs'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating drug: {str(e)}', 'danger')
    
    return render_template('edit_drug.html', drug=drug)

@app.route('/delete_drug/<int:drug_id>')
@login_required(role='admin')
def delete_drug(drug_id):
    try:
        drug = Drug.query.get_or_404(drug_id)
        db.session.delete(drug)
        db.session.commit()
        flash('Drug deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting drug: {str(e)}', 'danger')
    
    return redirect(url_for('drugs'))

# Sales Management
@app.route('/sales', methods=['GET', 'POST'])
@login_required()
def sales():
    if request.method == 'POST':
        try:
            drug_id = int(request.form['drug_id'])
            quantity = int(request.form['quantity'])
            staff_name = session['username']
            
            drug = Drug.query.get(drug_id)
            
            if not drug:
                flash('Drug not found!', 'danger')
                return redirect(url_for('sales'))
            
            if drug.quantity < quantity:
                flash('Insufficient stock!', 'danger')
                return redirect(url_for('sales'))
            
            # Update drug quantity
            drug.quantity -= quantity
            
            # Create sale record
            sale = Sale(
                drug_id=drug_id,
                quantity=quantity,
                unit_price=drug.selling_price,
                total_price=quantity * drug.selling_price,
                staff_name=staff_name,
                sale_date=datetime.now()
            )
            
            db.session.add(sale)
            db.session.commit()
            flash('Sale recorded successfully!', 'success')
            return redirect(url_for('sales'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error recording sale: {str(e)}', 'danger')
    
    drugs = Drug.query.filter(Drug.quantity > 0).all()
    sales_history = Sale.query.order_by(Sale.sale_date.desc()).all()
    return render_template('sales.html', drugs=drugs, sales=sales_history)

# Purchase Management
@app.route('/purchases', methods=['GET', 'POST'])
@login_required(role='admin')
def purchases():
    if request.method == 'POST':
        try:
            drug_id = int(request.form['drug_id'])
            quantity = int(request.form['quantity'])
            cost_price = float(request.form['cost_price'])
            supplier_name = request.form['supplier_name']
            batch_no = request.form['batch_no']
            
            drug = Drug.query.get(drug_id)
            
            if not drug:
                flash('Drug not found!', 'danger')
                return redirect(url_for('purchases'))
            
            # Update drug
            drug.quantity += quantity
            drug.cost_price = cost_price
            drug.batch_no = batch_no
            
            # Create purchase record
            purchase = Purchase(
                drug_id=drug_id,
                quantity=quantity,
                cost_price=cost_price,
                total_cost=quantity * cost_price,
                supplier_name=supplier_name,
                batch_no=batch_no,
                purchase_date=datetime.now()
            )
            
            db.session.add(purchase)
            db.session.commit()
            flash('Purchase recorded successfully!', 'success')
            return redirect(url_for('purchases'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error recording purchase: {str(e)}', 'danger')
    
    drugs = Drug.query.all()
    purchases_history = Purchase.query.order_by(Purchase.purchase_date.desc()).all()
    return render_template('purchases.html', drugs=drugs, purchases=purchases_history)

# Reports - FIXED
@app.route('/reports')
@login_required()
def reports():
    report_type = request.args.get('type', 'stock')
    period = request.args.get('period', 'daily')
    
    data = []
    template = 'reports.html'
    
    if report_type == 'stock':
        data = Drug.query.order_by(Drug.name).all()
        report_title = "Stock Report"
        
    elif report_type == 'expiry':
        today = datetime.now().date()
        soon_date = today + timedelta(days=90)
        expired = Drug.query.filter(Drug.expiry_date <= today).all()
        expiring_soon = Drug.query.filter(Drug.expiry_date <= soon_date, Drug.expiry_date > today).all()
        data = {
            'expired': expired, 
            'expiring_soon': expiring_soon,
            'report_title': 'Expiry Report'
        }
        
    elif report_type == 'sales':
        today = datetime.now().date()
        if period == 'daily':
            start_date = today
            sales_data = Sale.query.filter(db.func.date(Sale.sale_date) == start_date).all()
        elif period == 'weekly':
            start_date = today - timedelta(days=7)
            sales_data = Sale.query.filter(Sale.sale_date >= start_date).all()
        else:  # monthly
            start_date = today - timedelta(days=30)
            sales_data = Sale.query.filter(Sale.sale_date >= start_date).all()
        
        data = {
            'sales': sales_data,
            'period': period,
            'start_date': start_date,
            'report_title': f'Sales Report - {period.capitalize()}'
        }
    
    return render_template('reports.html', 
                         data=data, 
                         report_type=report_type, 
                         period=period,
                         today=datetime.now().date())

# User Management (Admin only)
@app.route('/users')
@login_required(role='admin')
def users():
    users_list = User.query.all()
    return render_template('users.html', users=users_list)

@app.route('/add_user', methods=['POST'])
@login_required(role='admin')
def add_user():
    try:
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('users'))
        
        user = User(username=username, role=role)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        flash('User added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding user: {str(e)}', 'danger')
    
    return redirect(url_for('users'))

# API endpoints for AJAX calls
@app.route('/api/drugs/search')
@login_required()
def api_drugs_search():
    query = request.args.get('q', '')
    drugs = Drug.query.filter(Drug.name.ilike(f'%{query}%')).limit(10).all()
    return jsonify([{
        'id': drug.id, 
        'name': drug.name, 
        'quantity': drug.quantity, 
        'selling_price': float(drug.selling_price)
    } for drug in drugs])

@app.route('/api/alerts')
@login_required()
def api_alerts():
    low_stock = Drug.query.filter(Drug.quantity < 10).count()
    soon_date = datetime.now().date() + timedelta(days=30)
    expiring_soon = Drug.query.filter(Drug.expiry_date <= soon_date, Drug.expiry_date > datetime.now().date()).count()
    expired = Drug.query.filter(Drug.expiry_date <= datetime.now().date()).count()
    
    return jsonify({
        'low_stock': low_stock,
        'expiring_soon': expiring_soon,
        'expired': expired
    })

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            
        # Create sample pharmacist user
        if not User.query.filter_by(username='pharmacist').first():
            pharmacist = User(username='pharmacist', role='pharmacist')
            pharmacist.set_password('pharma123')
            db.session.add(pharmacist)
            
        # Create sample drugs if none exist
        if Drug.query.count() == 0:
            sample_drugs = [
                Drug(
                    name='Paracetamol 500mg',
                    category='Analgesic',
                    batch_no='BATCH001',
                    manufacturer='Pharma Inc',
                    quantity=100,
                    cost_price=0.50,
                    selling_price=1.00,
                    expiry_date=datetime(2025, 12, 31).date()
                ),
                Drug(
                    name='Amoxicillin 250mg',
                    category='Antibiotic',
                    batch_no='BATCH002',
                    manufacturer='Med Labs',
                    quantity=15,
                    cost_price=1.20,
                    selling_price=2.50,
                    expiry_date=datetime(2024, 6, 30).date()
                ),
                Drug(
                    name='Vitamin C 100mg',
                    category='Supplement',
                    batch_no='BATCH003',
                    manufacturer='Health Plus',
                    quantity=5,
                    cost_price=0.30,
                    selling_price=0.75,
                    expiry_date=datetime(2023, 12, 15).date()
                )
            ]
            db.session.add_all(sample_drugs)
            
        db.session.commit()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)