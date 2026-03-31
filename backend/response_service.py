from typing import Optional, List
from backend.response import Response

class ResponseService:
    def __init__(self, database):
        """
        Initialize the service with a PostgreSQL connection string.
        Example: "dbname=test user=postgres password=secret host=localhost"
        """
        self.database = database


    def get_response(self, response_id: int) -> Optional[Response]:
        """
        Retrieve a response by its primary key (response_id).
        Returns a fully populated Response object or None if not found.
        """
        query = """
            SELECT 
                response_id,
                user_id,
                review_id,
                final_decision,
                final_certainty_rating,
                final_persuasion_rating,
                initial_decision,
                initial_certainty_rating,
                initial_persuasion_rating,
                influence_rating,
                decision_making_description,
                verification_queries_and_responses
            FROM Responses
            WHERE response_id = :response_id
        """
        params = {'response_id': response_id}
        
        results = self.database.execute_query(query, params)
        if not results or len(results) == 0:
            return None
            
        row = results[0]
        
        # Construct using named arguments — order-independent and type-safe
        return Response(
            response_id=row[0],
            user_id=row[1],
            review_id=row[2],
            final_decision=row[3],
            final_certainty_rating=row[4],
            final_persuasion_rating=row[5],
            initial_decision=row[6],
            initial_certainty_rating=row[7] if row[7] is not None else None,
            initial_persuasion_rating=row[8] if row[8] is not None else None,
            influence_rating=row[9] if row[9] is not None else None,
            decision_making_description=row[10],
            verification_queries_and_responses=row[11],
        )
        
    def create_response(self, response: Response) -> Response:
        """
        Create a new response entry in the database.
        Assigns a new response_id from the database and returns the created response.
        Validates required fields and constraints.
        """
        
        query = '''
            INSERT INTO Responses (
                user_id, review_id, initial_decision, final_decision,
                initial_certainty_rating, final_certainty_rating,
                initial_persuasion_rating, final_persuasion_rating,
                influence_rating, decision_making_description,
                verification_queries_and_responses
            ) VALUES (
                :user_id, :review_id, :initial_decision, :final_decision,
                :initial_certainty_rating, :final_certainty_rating,
                :initial_persuasion_rating, :final_persuasion_rating,
                :influence_rating, :decision_making_description,
                :verification_queries_and_responses
            )
            RETURNING *;
        '''
        params = {
            'user_id': response.user_id,
            'review_id': response.review_id,
            'initial_decision': response.initial_decision,
            'final_decision': response.final_decision,
            'initial_certainty_rating': response.initial_certainty_rating,
            'final_certainty_rating': response.final_certainty_rating,
            'initial_persuasion_rating': response.initial_persuasion_rating,
            'final_persuasion_rating': response.final_persuasion_rating,
            'influence_rating': response.influence_rating,
            'decision_making_description': response.decision_making_description,
            'verification_queries_and_responses': response.verification_queries_and_responses
        }
        results = self.database.execute_query(query, params, write=True)
        return Response(*results[0]) if results else None

    def get_response_id(self, user_id, review_id):
        "Get existing response id if it exists"
        query = "SELECT * FROM Responses WHERE user_id = :user_id AND review_id = :review_id"
        params = {'user_id': user_id, "review_id": review_id}
        results = self.database.execute_query(query, params)
        # print()
        # print(results)
        return results[0][0] if results else None

    
    def update_response(self, response_id: int,
                        updated_response: Response) -> Optional[Response]:
        """
        Update an existing response entry in the database by response_id.
        Only updates provided fields (non-None in updated_response), keeps others unchanged.
        Validates updated fields and constraints.
        Returns the updated response or None if not found.
        """
        set_clauses = []
        params = {}
       
        if updated_response.initial_decision is not None:
            if updated_response.initial_decision not in ['Genuine', 'Deceptive']:
                raise ValueError("initial_decision must be 'Genuine' or 'Deceptive'")
            set_clauses.append("initial_decision = :initial_decision")
            params['initial_decision'] = updated_response.initial_decision
       
        if updated_response.final_decision is not None:
            if updated_response.final_decision not in ['Genuine', 'Deceptive']:
                raise ValueError("final_decision must be 'Genuine' or 'Deceptive'")
            set_clauses.append("final_decision = :final_decision")
            params['final_decision'] = updated_response.final_decision
       
        if updated_response.initial_certainty_rating is not None:
            self._validate_rating(updated_response.initial_certainty_rating, "initial_certainty_rating")
            set_clauses.append("initial_certainty_rating = :initial_certainty_rating")
            params['initial_certainty_rating'] = updated_response.initial_certainty_rating
       
        if updated_response.final_certainty_rating is not None:
            self._validate_rating(updated_response.final_certainty_rating, "final_certainty_rating")
            set_clauses.append("final_certainty_rating = :final_certainty_rating")
            params['final_certainty_rating'] = updated_response.final_certainty_rating
       
        if updated_response.initial_persuasion_rating is not None:
            self._validate_rating(updated_response.initial_persuasion_rating, "initial_persuasion_rating")
            set_clauses.append("initial_persuasion_rating = :initial_persuasion_rating")
            params['initial_persuasion_rating'] = updated_response.initial_persuasion_rating
       
        if updated_response.final_persuasion_rating is not None:
            self._validate_rating(updated_response.final_persuasion_rating, "final_persuasion_rating")
            set_clauses.append("final_persuasion_rating = :final_persuasion_rating")
            params['final_persuasion_rating'] = updated_response.final_persuasion_rating
       
        if updated_response.influence_rating is not None:
            self._validate_rating(updated_response.influence_rating, "influence_rating")
            set_clauses.append("influence_rating = :influence_rating")
            params['influence_rating'] = updated_response.influence_rating
       
        if updated_response.decision_making_description is not None:
            set_clauses.append("decision_making_description = :decision_making_description")
            params['decision_making_description'] = updated_response.decision_making_description
       
        if updated_response.verification_queries_and_responses is not None:
            set_clauses.append("verification_queries_and_responses = :verification_queries_and_responses")
            params['verification_queries_and_responses'] = updated_response.verification_queries_and_responses
       
        if not set_clauses:
            return None  # Nothing to update
        set_sql = ", ".join(set_clauses)
        params['response_id'] = response_id
        query = f"""
            UPDATE Responses
            SET {set_sql}
            WHERE response_id = :response_id
            RETURNING *;
        """
        results = self.database.execute_query(query, params, write=True)
        return Response(*results[0]) if results else None


    def get_answer_count(self, user_id: int) -> int:
        """
        Count the number of completed responses for a given user.
        Used to determine if the user has reached the completion threshold (e.g., 28 questions).
        """
        query = "SELECT COUNT(*) FROM Responses WHERE user_id = :user_id"
        params = {'user_id': user_id}
        
        results = self.database.execute_query(query, params)
        
        # results[0][0] retrieves the first column (the count) of the first row
        if results and len(results) > 0:
            return int(results[0][0])
        return 0
   
    def _validate_rating(self, rating: Optional[int], field_name: str):
        if rating is not None and not (0 <= rating <= 7):
            raise ValueError(f"{field_name} must be between 0 and 7")