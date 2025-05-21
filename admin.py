from app import db, User, app

with app.app_context():
    username = 'admin'
    password = 'admin123' 

    if not User.query.filter_by(username=username).first():
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        print(f"Admin user '{username}' created.")
    else:
        print("User already exists.")
