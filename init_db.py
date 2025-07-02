from app import app, db, User
from werkzeug.security import generate_password_hash

def init_database():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create admin user if it doesn't exist
        admin = User.query.filter_by(email='admin@pss.com').first()
        if not admin:
            admin = User(
                full_name='PSS Administrator',
                email='admin@pss.com',
                phone='08000000000',
                password_hash=generate_password_hash('admin123'),
                bank_name='Admin Bank',
                account_number='0000000000',
                account_name='PSS Admin',
                category='Elite',
                referral_code='ADMIN001',
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print('Admin user created successfully!')
            print('Email: admin@pss.com')
            print('Password: admin123')
        else:
            print('Admin user already exists')

if __name__ == '__main__':
    init_database()
