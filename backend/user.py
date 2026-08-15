from dataclasses import dataclass
from typing import Optional
import bcrypt


@dataclass
class User:
    email: str
    password: str
    wave: Optional[int] = None        # 1 = original collection, 2 = current
    review_set: Optional[int] = None  # Stage-2 set: 1 for wave 1, 2-4 for wave 2

    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def authenticate(self, password):
        # Check password passed with encoded user password
        return bcrypt.checkpw(password.encode(), self.password.encode())
