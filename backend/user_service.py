from backend.user import User




class UserService:
    def __init__(self, database):
        self.database = database


    # Named explicitly rather than SELECT *, so that adding a column to the
    # table cannot shift the positional unpacking below.
    USER_COLUMNS = ["email", "password", "wave", "review_set"]

    def get_user(self, email):
        query = f"SELECT {', '.join(self.USER_COLUMNS)} FROM users WHERE email = :email"
        params = {'email': email}
        results = self.database.execute_query(query, params)
        return User(*results[0]) if results else None


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
            if results:
                new_user = self.get_user(email)
                return new_user
            return None


    def get_authenticated_user(self, email, password):
        user = self.get_user(email)
        if user and user.authenticate(password):
            return user
        # Differentiate between user and password issues
        return None

    def get_user_id(self, email):
        query = "SELECT user_id FROM users WHERE email = :email"
        params = {'email': email}
        results = self.database.execute_query(query, params)
        return results[0][0]

    # ------------------------------------------------------------------
    # Stage-2 review set assignment
    # ------------------------------------------------------------------
    def get_review_set(self, user_id):
        """Return the participant's assigned set, or None if unassigned."""
        query = "SELECT review_set FROM users WHERE user_id = :user_id"
        results = self.database.execute_query(query, {'user_id': user_id})
        return results[0][0] if results else None

    def get_wave(self, user_id):
        """1 = original collection (Stage-2 set 1, 75% AI accuracy)
           2 = current collection (Stage-2 sets 2-4, 50% AI accuracy)

        Recorded for the analysis - the app itself needs no branching,
        because set 1 remains in `reviews` alongside sets 2-4.
        """
        query = "SELECT wave FROM users WHERE user_id = :user_id"
        results = self.database.execute_query(query, {'user_id': user_id})
        return results[0][0] if results else None

    # Assignment is entirely the database's job:
    #   migration 002 sets existing rows to wave 1 / set 1, and puts a
    #   DEFAULT on both columns so every new registration is wave 2 with a
    #   random set from 2-4. Both columns are NOT NULL, so there is nothing
    #   for the application to backfill - read `user.wave` and
    #   `user.review_set` off the User object returned by get_user().
    












    