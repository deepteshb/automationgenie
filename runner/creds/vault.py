"""
HashiCorp Vault Credential Provider

Integrates with HashiCorp Vault for secure credential management.
"""

import os
from typing import Dict, Any, List, Optional
from .base import CredentialProvider
from ..errors import CredentialError, ConnectionError


class VaultCredentialProvider(CredentialProvider):
    """Credential provider that integrates with HashiCorp Vault."""
    
    def __init__(self, vault_url: Optional[str] = None, 
                 auth_method: str = "token", **kwargs):
        super().__init__("vault")
        
        self.vault_url = vault_url or os.environ.get('VAULT_ADDR')
        self.auth_method = auth_method
        self.auth_config = kwargs
        
        if not self.vault_url:
            raise CredentialError("Vault URL not provided and VAULT_ADDR not set")
        
        # Initialize Vault client
        self._init_vault_client()
    
    def _init_vault_client(self) -> None:
        """Initialize the Vault client."""
        try:
            import hvac
            
            self.client = hvac.Client(url=self.vault_url)
            
            # Authenticate based on method
            if self.auth_method == "token":
                token = self.auth_config.get('token') or os.environ.get('VAULT_TOKEN')
                if not token:
                    raise CredentialError("Vault token not provided")
                self.client.token = token
                
            elif self.auth_method == "approle":
                role_id = self.auth_config.get('role_id') or os.environ.get('VAULT_ROLE_ID')
                secret_id = self.auth_config.get('secret_id') or os.environ.get('VAULT_SECRET_ID')
                
                if not role_id or not secret_id:
                    raise CredentialError("Vault AppRole credentials not provided")
                
                self.client.auth.approle.login(
                    role_id=role_id,
                    secret_id=secret_id
                )
                
            elif self.auth_method == "kubernetes":
                jwt = self.auth_config.get('jwt') or self._get_kubernetes_jwt()
                role = self.auth_config.get('role') or os.environ.get('VAULT_K8S_ROLE')
                
                if not jwt or not role:
                    raise CredentialError("Kubernetes JWT or role not provided")
                
                self.client.auth.kubernetes.login(
                    role=role,
                    jwt=jwt
                )
            
            # Test connection
            if not self.client.is_authenticated():
                raise CredentialError("Failed to authenticate with Vault")
                
        except ImportError:
            raise CredentialError("hvac library not installed. Install with: pip install hvac")
        except Exception as e:
            raise CredentialError(f"Failed to initialize Vault client: {e}")
    
    def _get_kubernetes_jwt(self) -> Optional[str]:
        """Get Kubernetes JWT token from service account."""
        try:
            with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return None
    
    def get_credential(self, credential_name: str) -> Dict[str, Any]:
        """
        Retrieve credential from Vault.
        
        Args:
            credential_name: Path to the secret in Vault (e.g., 'secret/myapp/db')
            
        Returns:
            Dictionary containing credential data
            
        Raises:
            CredentialError: If credential cannot be retrieved
        """
        try:
            # Read secret from Vault
            response = self.client.secrets.kv.v2.read_secret_version(
                path=credential_name
            )
            
            if not response or 'data' not in response:
                raise CredentialError(f"Invalid response from Vault for {credential_name}")
            
            secret_data = response['data']['data']
            
            # Add metadata
            secret_data['_source'] = 'vault'
            secret_data['_name'] = credential_name
            secret_data['_vault_path'] = credential_name
            
            self.log_credential_access(credential_name, True)
            return secret_data
            
        except Exception as e:
            self.log_credential_access(credential_name, False, str(e))
            raise CredentialError(
                f"Failed to retrieve credential '{credential_name}' from Vault: {e}",
                credential_name=credential_name
            )
    
    def list_credentials(self) -> List[str]:
        """
        List available credentials from Vault.
        
        Returns:
            List of available credential paths
        """
        try:
            # This is a simplified implementation
            # In practice, you might want to implement a more sophisticated listing
            # based on your Vault structure
            
            # For now, return an empty list as listing all secrets
            # requires specific permissions and structure knowledge
            self.logger.warning("Vault credential listing not fully implemented")
            return []
            
        except Exception as e:
            self.logger.error("Failed to list Vault credentials", error=str(e))
            return []
    
    def test_connection(self) -> bool:
        """
        Test connection to Vault.
        
        Returns:
            True if connection is successful
        """
        try:
            return self.client.is_authenticated()
        except Exception:
            return False
    
    def create_secret(self, path: str, data: Dict[str, Any]) -> bool:
        """
        Create a new secret in Vault.
        
        Args:
            path: Path where to store the secret
            data: Secret data to store
            
        Returns:
            True if secret was created successfully
        """
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret_dict=data
            )
            return True
        except Exception as e:
            self.logger.error("Failed to create secret in Vault", path=path, error=str(e))
            return False
    
    def update_secret(self, path: str, data: Dict[str, Any]) -> bool:
        """
        Update an existing secret in Vault.
        
        Args:
            path: Path of the secret to update
            data: New secret data
            
        Returns:
            True if secret was updated successfully
        """
        return self.create_secret(path, data)  # Vault handles create/update the same way
    
    def delete_secret(self, path: str) -> bool:
        """
        Delete a secret from Vault.
        
        Args:
            path: Path of the secret to delete
            
        Returns:
            True if secret was deleted successfully
        """
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(path=path)
            return True
        except Exception as e:
            self.logger.error("Failed to delete secret from Vault", path=path, error=str(e))
            return False
