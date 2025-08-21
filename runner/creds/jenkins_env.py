"""
Jenkins Environment Credential Provider

Reads credentials from Jenkins environment variables and credential bindings.
"""

import os
from typing import Dict, Any, List
from .base import CredentialProvider
from ..errors import CredentialError


class JenkinsCredentialProvider(CredentialProvider):
    """Credential provider that reads from Jenkins environment variables."""
    
    def __init__(self):
        super().__init__("jenkins_env")
        self.credential_prefix = "CREDENTIAL_"
    
    def get_credential(self, credential_name: str) -> Dict[str, Any]:
        """
        Retrieve credential from Jenkins environment variables.
        
        Args:
            credential_name: Name of the credential to retrieve
            
        Returns:
            Dictionary containing credential data
            
        Raises:
            CredentialError: If credential cannot be retrieved
        """
        try:
            # Try different environment variable patterns
            env_vars = [
                credential_name,
                f"{self.credential_prefix}{credential_name}",
                credential_name.upper(),
                f"{self.credential_prefix}{credential_name.upper()}"
            ]
            
            credential_data = {}
            
            for env_var in env_vars:
                value = os.environ.get(env_var)
                if value:
                    # Try to parse as JSON or use as simple value
                    try:
                        import json
                        credential_data = json.loads(value)
                        break
                    except (json.JSONDecodeError, ValueError):
                        # If not JSON, treat as simple key-value
                        credential_data = {
                            'value': value,
                            'type': 'simple'
                        }
                        break
            
            if not credential_data:
                raise CredentialError(
                    f"Credential '{credential_name}' not found in environment variables",
                    credential_name=credential_name,
                    checked_vars=env_vars
                )
            
            # Add metadata
            credential_data['_source'] = 'jenkins_env'
            credential_data['_name'] = credential_name
            
            self.log_credential_access(credential_name, True)
            return credential_data
            
        except Exception as e:
            self.log_credential_access(credential_name, False, str(e))
            raise CredentialError(
                f"Failed to retrieve credential '{credential_name}': {e}",
                credential_name=credential_name
            )
    
    def list_credentials(self) -> List[str]:
        """
        List available credentials from environment variables.
        
        Returns:
            List of available credential names
        """
        credentials = []
        
        for env_var, value in os.environ.items():
            # Look for credential-related environment variables
            if (env_var.startswith(self.credential_prefix) or 
                env_var.lower() in ['username', 'password', 'token', 'secret', 'key']):
                
                # Extract credential name
                if env_var.startswith(self.credential_prefix):
                    credential_name = env_var[len(self.credential_prefix):]
                else:
                    credential_name = env_var
                
                credentials.append(credential_name)
        
        return list(set(credentials))  # Remove duplicates
    
    def test_connection(self) -> bool:
        """
        Test if running in Jenkins environment.
        
        Returns:
            True if Jenkins environment variables are present
        """
        jenkins_vars = [
            'JENKINS_URL',
            'BUILD_NUMBER',
            'JOB_NAME',
            'WORKSPACE'
        ]
        
        return any(os.environ.get(var) for var in jenkins_vars)
    
    def get_jenkins_context(self) -> Dict[str, Any]:
        """
        Get Jenkins build context information.
        
        Returns:
            Dictionary with Jenkins build context
        """
        context = {}
        
        jenkins_context_vars = {
            'JENKINS_URL': 'jenkins_url',
            'BUILD_NUMBER': 'build_number',
            'JOB_NAME': 'job_name',
            'BUILD_ID': 'build_id',
            'WORKSPACE': 'workspace',
            'NODE_NAME': 'node_name',
            'EXECUTOR_NUMBER': 'executor_number'
        }
        
        for env_var, context_key in jenkins_context_vars.items():
            value = os.environ.get(env_var)
            if value:
                context[context_key] = value
        
        return context
