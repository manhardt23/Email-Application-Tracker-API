from DB.models import Base, get_engine, ApplicationEmail

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
