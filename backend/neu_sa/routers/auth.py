from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import snowflake.connector
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt
from datetime import datetime, timedelta
import os
import re
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Initialize router
auth_router = APIRouter()

# Security setup
security = HTTPBearer()

# Password hashing configuration
ph = PasswordHasher()
SECRET_KEY = os.getenv("SECRET_KEY", "hahahahaha")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Predefined campus options
VALID_CAMPUSES = [
    "Boston",
    "Online",
    "Seattle, WA",
    "Silicon Valley, CA",
    "Oakland, CA",
    "Arlington, VA",
    "Miami, FL",
    "Toronto, Canada",
    "Vancouver, Canada"
]

# Predefined program names and their IDs
PROGRAM_ID_MAP = {
    "Information Systems, MSIS": "MP_IS_MSIS",
    "Cyber-Physical Systems, MS": "MP_CPS_MS",
    "Data Architecture and Management, MS": "MP_DAM_MS",
    "Software Engineering Systems, MS": "MP_SES_MS",
    "Telecommunication Networks, MS": "MP_TN_MS",
    "Information Systems MSIS-Bridge": "MP_IS_MSIS_BR",
    "Information Systems MSIS—Bridge—Online": "MP_IS_MSIS_BRO",
    "Information Systems MSIS—Online": "MP_IS_MSIS_O",
    "Blockchain and Smart Contract Engineering Graduate Certificate": "MP_BC_SC_CERT",
    "Broadband Wireless Systems Graduate Certificate": "MP_BW_CERT",
    "IP Telephony Systems Graduate Certificate": "MP_IPT_CERT",
    "Software Engineering Systems Graduate Certificate": "MP_SES_CERT",
}

VALID_PROGRAM_NAMES = list(PROGRAM_ID_MAP.keys())

# Predefined college options
VALID_COLLEGES = [
    "College of Engineering"
]

# Snowflake connection function
def get_snowflake_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "WH_NEU_SA"),
        database=os.getenv("SNOWFLAKE_DATABASE", "DB_NEU_SA"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "NEU_SA"),
    )

# Models
class RegisterModel(BaseModel):
    username: str
    password: str
    campus: str
    program_name: str  # Added program_name field
    college: str       # Added college field

class ValidateTokenModel(BaseModel):
    token: str

class LoginModel(BaseModel):
    username: str
    password: str

def validate_jwt(token: str = None, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if token is None:
        token = credentials.credentials
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Extract claims
        user_id = payload.get("user_id")
        username = payload.get("sub")

        # Validate mandatory claims
        if not user_id or not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token. Missing required user details.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {"user_id": user_id, "username": username}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Helper function to validate password
def validate_password(password: str):
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not any(char.isupper() for char in password):
        return "Password must contain at least one uppercase letter."
    if not any(char.isdigit() for char in password):
        return "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character."
    return None

# Registration endpoint
@auth_router.post("/register")
async def register_user(user: RegisterModel):
    # Validate campus
    if user.campus not in VALID_CAMPUSES:
        raise HTTPException(status_code=400, detail="Invalid campus selected.")

    # Validate program name
    if user.program_name not in VALID_PROGRAM_NAMES:
        raise HTTPException(status_code=400, detail="Invalid program name selected.")

    # Map program name to program ID
    program_id = PROGRAM_ID_MAP[user.program_name]

    # Validate college
    if user.college not in VALID_COLLEGES:
        raise HTTPException(status_code=400, detail="Invalid college selected.")

    # Validate password
    password_error = validate_password(user.password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)

    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        # Check if username already exists
        cursor.execute("SELECT COUNT(*) FROM USER_PROFILE WHERE USERNAME = %s", (user.username,))
        if cursor.fetchone()[0] > 0:
            raise HTTPException(status_code=400, detail="Username already exists.")

        # Hash password
        hashed_password = ph.hash(user.password)

        # Insert user into the database
        cursor.execute("""
            INSERT INTO USER_PROFILE (USERNAME, PASSWORD, CAMPUS, PROGRAM_NAME, PROGRAM_ID, COLLEGE)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user.username, hashed_password, user.campus, user.program_name, program_id, user.college))
        conn.commit()
        return {"message": "Registration successful"}
    finally:
        cursor.close()
        conn.close()

# Login endpoint
@auth_router.post("/login")
async def login_user(user: LoginModel):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT PASSWORD, USER_ID FROM USER_PROFILE WHERE USERNAME = %s", (user.username,))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="User not found.")

        hashed_password, user_id = result

        try:
            ph.verify(hashed_password, user.password)
        except VerifyMismatchError:
            raise HTTPException(status_code=401, detail="Incorrect password.")

        token_data = {
            "sub": user.username,
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        }
        access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "username": user.username,
            "message": "Login successful."
        }
    finally:
        cursor.close()
        conn.close()

# Token validation endpoint
@auth_router.post("/validate-token")
async def validate_token(token_data: ValidateTokenModel):
    try:
        payload = validate_jwt(token=token_data.token)
        return {"valid": True, "payload": payload}
    except HTTPException as e:
        return {"valid": False, "detail": e.detail}
