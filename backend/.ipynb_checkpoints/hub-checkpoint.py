from backend.database import Database
from backend.user_service import UserService
from backend.response_service import ResponseService 
from backend.reviews_service import ReviewService
from backend.nat_lang_exp_service import LanguageExplanationService




# Each user has access to their db instance
class Hub:
    def __init__(self):
        database = Database()
        self.user_service = UserService(database)
        self.reviews_service = ReviewService(database)
        self.response_service = ResponseService(database)
        self.nat_lang_exp_service = LanguageExplanationService(database)