from fastapi import HTTPException

class RedirectException(HTTPException):
    def __init__(self, location: str):
        super().__init__(status_code=303, detail="Redirecting...")
        self.headers = {"Location": location}