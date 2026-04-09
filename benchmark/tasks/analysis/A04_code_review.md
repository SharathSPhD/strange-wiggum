# A04 — Code Review

## Task

Perform a thorough code review of the following Python function. Identify all issues
(bugs, security problems, performance, style) and provide corrected code.

```python
import sqlite3
import hashlib
import time

def authenticate_user(username, password, db_path="users.db"):
    """Authenticate user and return session token."""
    conn = sqlite3.connect(db_path)
    
    # Check credentials
    query = f"SELECT id, password_hash FROM users WHERE username = '{username}'"
    result = conn.execute(query).fetchone()
    
    if result is None:
        return None
    
    user_id, stored_hash = result
    input_hash = hashlib.md5(password.encode()).hexdigest()
    
    if input_hash != stored_hash:
        return None
    
    # Generate session token
    token = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()
    
    # Store session
    conn.execute(f"INSERT INTO sessions VALUES ('{token}', {user_id}, {time.time() + 3600})")
    conn.commit()
    
    return token
```

Your review must:
1. List every bug and security vulnerability (be specific — name the attack vectors)
2. Identify performance issues
3. Identify style/maintainability issues
4. Provide a corrected version of the full function with comments explaining each fix
5. Rate severity of each issue (Critical / High / Medium / Low)

## Scoring Rubric (embedded)
- Correctness (40%): Are all real issues found? Are severities correct?
- Depth (30%): Is the corrected code actually correct and complete?
- Clarity (20%): Are issues explained clearly with attack vector details?
- Structure (10%): Organized review format with severity ratings and fixed code.
