import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib

class StorageManager:
    """Manages data storage for users and tokens"""
    
    def __init__(self, output_folder: str, use_json: bool = True):
        self.output_folder = output_folder
        self.use_json = use_json
        self.users_file = os.path.join(output_folder, 'users.json')
        self.tokens_file = os.path.join(output_folder, 'tokens.json')
        self.reset_tokens_file = os.path.join(output_folder, 'reset_tokens.json')
        
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
    
    def _load_json_file(self, filepath: str) -> Dict[str, Any]:
        """Load data from JSON file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_json_file(self, filepath: str, data: Dict[str, Any]):
        """Save data to JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving to {filepath}: {e}")
    
    # User management
    def load_users(self) -> Dict[str, Any]:
        """Load users from storage"""
        if self.use_json:
            return self._load_json_file(self.users_file)
        # For production, this would load from database
        return {}
    
    def save_users(self, users: Dict[str, Any]):
        """Save users to storage"""
        if self.use_json:
            self._save_json_file(self.users_file, users)
        # For production, this would save to database
    
    def add_user(self, email: str, name: str, password: str, plan: str = "Pro"):
        """Add a new user"""
        users = self.load_users()
        
        # Hash password
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        users[email] = {
            'name': name,
            'email': email,
            'password_hash': password_hash,
            'created_at': datetime.now().isoformat(),
            'plan': plan,
            'plan_updated_at': datetime.now().isoformat()
        }
        
        self.save_users(users)
        return users[email]
    
    def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        users = self.load_users()
        return users.get(email)
    
    def verify_user(self, email: str, password: str) -> bool:
        """Verify user credentials"""
        user = self.get_user(email)
        if not user:
            return False
        
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return user['password_hash'] == password_hash
    
    # Token management
    def load_tokens(self) -> Dict[str, Any]:
        """Load tokens from storage"""
        if self.use_json:
            return self._load_json_file(self.tokens_file)
        return {}
    
    def save_tokens(self, tokens: Dict[str, Any]):
        """Save tokens to storage"""
        if self.use_json:
            self._save_json_file(self.tokens_file, tokens)
    
    def get_or_create_token(self, unique_id: str) -> str:
        """Get existing token or create new one"""
        tokens = self.load_tokens()
        
        if unique_id not in tokens:
            import secrets
            tokens[unique_id] = secrets.token_hex(16)
            self.save_tokens(tokens)
        
        return tokens[unique_id]
    
    def verify_token(self, unique_id: str, token: str) -> bool:
        """Verify token for a document"""
        tokens = self.load_tokens()
        return tokens.get(unique_id) == token
    
    # Reset token management
    def load_reset_tokens(self) -> Dict[str, Any]:
        """Load reset tokens from storage"""
        if self.use_json:
            return self._load_json_file(self.reset_tokens_file)
        return {}
    
    def save_reset_tokens(self, tokens: Dict[str, Any]):
        """Save reset tokens to storage"""
        if self.use_json:
            self._save_json_file(self.reset_tokens_file, tokens)
    
    def create_reset_token(self, email: str) -> str:
        """Create a password reset token"""
        tokens = self.load_reset_tokens()
        
        # Clean up expired tokens
        current_time = datetime.now()
        expired_emails = []
        for email_addr, token_data in tokens.items():
            try:
                expires = datetime.fromisoformat(token_data['expires'])
                if expires < current_time:
                    expired_emails.append(email_addr)
            except:
                expired_emails.append(email_addr)
        
        for expired_email in expired_emails:
            del tokens[expired_email]
        
        # Generate new token
        import secrets
        token = secrets.token_hex(16)
        expires = (current_time + datetime.timedelta(hours=1)).isoformat()
        
        tokens[email] = {
            'token': token,
            'expires': expires
        }
        
        self.save_reset_tokens(tokens)
        return token
    
    def verify_reset_token(self, email: str, token: str) -> bool:
        """Verify a password reset token"""
        tokens = self.load_reset_tokens()
        token_data = tokens.get(email)
        
        if not token_data:
            return False
        
        try:
            expires = datetime.fromisoformat(token_data['expires'])
            if expires < datetime.now():
                return False
        except:
            return False
        
        return token_data['token'] == token
