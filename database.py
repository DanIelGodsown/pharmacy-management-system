from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

def init_db(app):
    """Initialize the database with sample data"""
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        from models import User
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
        from models import Drug
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