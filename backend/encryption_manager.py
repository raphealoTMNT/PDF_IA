import os
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from pathlib import Path

class EncryptionManager:
    """
    Gestionnaire de chiffrement pour sécuriser les données sensibles
    """
    
    def __init__(self, password: str = None):
        """
        Initialise le gestionnaire de chiffrement
        
        Args:
            password (str): Mot de passe pour générer la clé de chiffrement
        """
        self.key_file = Path(".encryption_key")
        self.password = password or os.getenv('ENCRYPTION_PASSWORD', 'default_secure_password_2024!')
        self.fernet = self._get_or_create_key()
    
    def _generate_key_from_password(self, password: str, salt: bytes = None) -> bytes:
        """Génère une clé de chiffrement à partir d'un mot de passe"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def _get_or_create_key(self) -> Fernet:
        """Récupère ou crée une clé de chiffrement"""
        try:
            if self.key_file.exists():
                # Charger la clé existante
                with open(self.key_file, 'rb') as f:
                    data = f.read()
                    salt = data[:16]
                    key, _ = self._generate_key_from_password(self.password, salt)
                    return Fernet(key)
            else:
                # Créer une nouvelle clé
                key, salt = self._generate_key_from_password(self.password)
                with open(self.key_file, 'wb') as f:
                    f.write(salt)
                return Fernet(key)
        except Exception as e:
            print(f"Erreur lors de la gestion de la clé de chiffrement: {e}")
            # Fallback: générer une clé temporaire
            return Fernet(Fernet.generate_key())
    
    def encrypt_data(self, data: str) -> str:
        """
        Chiffre des données textuelles
        
        Args:
            data (str): Données à chiffrer
            
        Returns:
            str: Données chiffrées encodées en base64
        """
        try:
            encrypted_data = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            print(f"Erreur lors du chiffrement: {e}")
            return data  # Retourner les données non chiffrées en cas d'erreur
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Déchiffre des données
        
        Args:
            encrypted_data (str): Données chiffrées en base64
            
        Returns:
            str: Données déchiffrées
        """
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            print(f"Erreur lors du déchiffrement: {e}")
            return encrypted_data  # Retourner les données telles quelles en cas d'erreur
    
    def encrypt_json_file(self, file_path: str, sensitive_fields: list = None) -> bool:
        """
        Chiffre les champs sensibles d'un fichier JSON
        
        Args:
            file_path (str): Chemin vers le fichier JSON
            sensitive_fields (list): Liste des champs à chiffrer
            
        Returns:
            bool: True si le chiffrement a réussi
        """
        if sensitive_fields is None:
            sensitive_fields = ['full_content', 'content_preview', 'emails', 'urls']
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Chiffrer les champs sensibles
            for field in sensitive_fields:
                if field in data:
                    if isinstance(data[field], str):
                        data[field] = self.encrypt_data(data[field])
                    elif isinstance(data[field], list):
                        data[field] = [self.encrypt_data(str(item)) for item in data[field]]
            
            # Marquer le fichier comme chiffré
            data['_encrypted'] = True
            data['_encrypted_fields'] = sensitive_fields
            
            # Sauvegarder le fichier chiffré
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Erreur lors du chiffrement du fichier {file_path}: {e}")
            return False
    
    def decrypt_json_file(self, file_path: str) -> dict:
        """
        Déchiffre un fichier JSON et retourne les données déchiffrées
        
        Args:
            file_path (str): Chemin vers le fichier JSON chiffré
            
        Returns:
            dict: Données déchiffrées
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Vérifier si le fichier est chiffré
            if not data.get('_encrypted', False):
                return data
            
            encrypted_fields = data.get('_encrypted_fields', [])
            
            # Déchiffrer les champs
            for field in encrypted_fields:
                if field in data:
                    if isinstance(data[field], str):
                        data[field] = self.decrypt_data(data[field])
                    elif isinstance(data[field], list):
                        data[field] = [self.decrypt_data(item) for item in data[field]]
            
            # Nettoyer les métadonnées de chiffrement pour l'utilisation
            decrypted_data = data.copy()
            decrypted_data.pop('_encrypted', None)
            decrypted_data.pop('_encrypted_fields', None)
            
            return decrypted_data
            
        except Exception as e:
            print(f"Erreur lors du déchiffrement du fichier {file_path}: {e}")
            return {}
    
    def is_file_encrypted(self, file_path: str) -> bool:
        """
        Vérifie si un fichier JSON est chiffré
        
        Args:
            file_path (str): Chemin vers le fichier JSON
            
        Returns:
            bool: True si le fichier est chiffré
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('_encrypted', False)
        except:
            return False