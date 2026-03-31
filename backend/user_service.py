from backend.user import User




class UserService:
    def __init__(self, database):
        self.database = database


    def get_user(self, email):
        query = "SELECT * FROM users WHERE email = :email"
        params = {'email': email}
        results = self.database.execute_query(query, params)
        return User(*results[0][1:]) if results else None


    def create_user(self, email, password):
        # Check if user exists
        existing_user = self.get_user(email)
        # if does not exist
        if not existing_user:
            query = '''
            INSERT INTO users (email, password)
            VALUES (:email, :password)
            RETURNING email, password
            '''
            # Hash password
            password_hash = User.hash_password(password)
            # Create params
            params = {'email': email, 'password': password_hash}
            # Write to DB
            results = self.database.execute_query(query, params, write=True)
            # Return a User instance
            return User(*results[0]) if results else None
        return None


    def get_authenticated_user(self, email, password):
        user = self.get_user(email)
        if user and user.authenticate(password):
            return user
        # Differentiate between user and password issues
        return None

    def get_user_id(self, email):
        query = "SELECT * FROM users WHERE email = :email"
        params = {'email': email}
        results = self.database.execute_query(query, params)
        return results[0][0]
    












    