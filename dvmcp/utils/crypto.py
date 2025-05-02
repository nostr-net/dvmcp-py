"""
Cryptographic utilities for DVMCP

This module provides helper functions for cryptographic operations.
"""

import os
import json
import base64
from typing import Dict, Any, Optional, Tuple
from nostr_sdk import Keys

from dvmcp.logging import get_logger

logger = get_logger("utils.crypto")

def generate_keys() -> Keys:
    """
    Generate new Nostr keys
    
    Returns:
        Generated keys
    """
    return Keys.generate()

def load_keys_from_file(file_path: str) -> Optional[Keys]:
    """
    Load keys from a file
    
    Args:
        file_path: Path to the key file
        
    Returns:
        Loaded keys or None if file doesn't exist
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        if "private_key" in data:
            # Load from hex private key
            return Keys.parse(data["private_key"])
        elif "nsec" in data:
            # Load from nsec
            return Keys.parse(data["nsec"])
        else:
            logger.error("Invalid key file format")
            return None
    except Exception as e:
        logger.error(f"Failed to load keys: {str(e)}")
        return None

def save_keys_to_file(keys: Keys, file_path: str, include_nsec: bool = False) -> bool:
    """
    Save keys to a file
    
    Args:
        keys: Keys to save
        file_path: Path to save the keys to
        include_nsec: Whether to include the nsec (bech32 encoded private key)
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        data = {
            "public_key": keys.public_key().to_hex(),
            "private_key": keys.secret_key().to_hex()
        }
        
        if include_nsec:
            data["npub"] = keys.public_key().to_bech32()
            data["nsec"] = keys.to_bech32()
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Saved keys to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save keys: {str(e)}")
        return False

def encrypt_message(message: str, recipient_pubkey: str, sender_keys: Keys) -> Optional[str]:
    """
    Encrypt a message for a recipient
    
    Args:
        message: Message to encrypt
        recipient_pubkey: Recipient's public key (hex or bech32)
        sender_keys: Sender's keys
        
    Returns:
        Encrypted message or None if encryption failed
    """
    try:
        from nostr_sdk import PublicKey
        
        # Parse recipient public key
        if recipient_pubkey.startswith("npub"):
            recipient_key = PublicKey.from_bech32(recipient_pubkey)
        else:
            recipient_key = PublicKey.from_hex(recipient_pubkey)
        
        # Encrypt message
        encrypted = sender_keys.encrypt(message.encode(), recipient_key)
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt message: {str(e)}")
        return None

def decrypt_message(encrypted_message: str, sender_pubkey: str, recipient_keys: Keys) -> Optional[str]:
    """
    Decrypt a message from a sender
    
    Args:
        encrypted_message: Encrypted message (base64 encoded)
        sender_pubkey: Sender's public key (hex or bech32)
        recipient_keys: Recipient's keys
        
    Returns:
        Decrypted message or None if decryption failed
    """
    try:
        from nostr_sdk import PublicKey
        
        # Parse sender public key
        if sender_pubkey.startswith("npub"):
            sender_key = PublicKey.from_bech32(sender_pubkey)
        else:
            sender_key = PublicKey.from_hex(sender_pubkey)
        
        # Decrypt message
        encrypted = base64.b64decode(encrypted_message)
        decrypted = recipient_keys.decrypt(encrypted, sender_key)
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt message: {str(e)}")
        return None