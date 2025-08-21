"""
Base Credential Provider

Abstract base class for credential providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import structlog


class CredentialProvider(ABC):
    """Abstract base class for credential providers."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = structlog.get_logger(__name__)
    
    @abstractmethod
    def get_credential(self, credential_name: str) -> Dict[str, Any]:
        """
        Retrieve a credential by name.
        
        Args:
            credential_name: Name of the credential to retrieve
            
        Returns:
            Dictionary containing credential data
            
        Raises:
            CredentialError: If credential cannot be retrieved
        """
        pass
    
    @abstractmethod
    def list_credentials(self) -> list[str]:
        """
        List available credential names.
        
        Returns:
            List of available credential names
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test connection to the credential store.
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass
    
    def validate_credential(self, credential: Dict[str, Any], 
                          required_fields: list[str]) -> bool:
        """
        Validate that a credential contains required fields.
        
        Args:
            credential: Credential dictionary to validate
            required_fields: List of required field names
            
        Returns:
            True if credential is valid, False otherwise
        """
        if not isinstance(credential, dict):
            return False
        
        for field in required_fields:
            if field not in credential or credential[field] is None:
                return False
        
        return True
    
    def mask_sensitive_data(self, credential: Dict[str, Any], 
                           sensitive_fields: list[str] = None) -> Dict[str, Any]:
        """
        Create a copy of credential with sensitive fields masked.
        
        Args:
            credential: Original credential dictionary
            sensitive_fields: List of sensitive field names to mask
            
        Returns:
            Copy of credential with sensitive fields masked
        """
        if sensitive_fields is None:
            sensitive_fields = ['password', 'token', 'secret', 'key']
        
        masked = credential.copy()
        for field in sensitive_fields:
            if field in masked:
                masked[field] = '***MASKED***'
        
        return masked
    
    def log_credential_access(self, credential_name: str, 
                            success: bool, error: Optional[str] = None) -> None:
        """
        Log credential access attempt.
        
        Args:
            credential_name: Name of the credential accessed
            success: Whether access was successful
            error: Error message if access failed
        """
        if success:
            self.logger.info("Credential accessed successfully", 
                           provider=self.name, credential=credential_name)
        else:
            self.logger.error("Credential access failed", 
                            provider=self.name, credential=credential_name, error=error)
