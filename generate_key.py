#!/usr/bin/env python3
"""
Generate a secure secret key for Flask applications
"""
import secrets

def generate_secret_key():
    """Generate a secure 32-byte hex secret key"""
    return secrets.token_hex(32)

if __name__ == "__main__":
    key = generate_secret_key()
    print(f"Generated SECRET_KEY: {key}")
    print("\nCopy this to your .env file:")
    print(f"SECRET_KEY={key}")
