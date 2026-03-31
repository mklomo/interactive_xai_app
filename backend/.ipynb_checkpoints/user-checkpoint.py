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
        return  bcrypt.checkpw(password.encode(), self.password.encode()) 