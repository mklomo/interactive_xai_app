from dataclasses import dataclass
import bcrypt


@dataclass
class User:
    email: str
    password: str

    @staticmethod
    def hash_password(password):
        return  bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


    def authenticate(self, password):
        # Check password passed with encoded user password
        return  bcrypt.checkpw(password.encode(), self.password.encode()) 