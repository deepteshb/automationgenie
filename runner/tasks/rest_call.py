"""
REST API Call Task

Executes REST API calls with various authentication methods and response handling.
"""

import requests
import json
import structlog
from typing import Dict, Any, Optional, Union
from .base import Task
from ..errors import TaskExecutionError, ConnectionError


class RESTCallTask(Task):
    """Task for executing REST API calls."""
    
    task_type = "rest_call"
    description = "Execute REST API calls"
    
    parameters = {
        'url': {'type': str, 'description': 'API endpoint URL'},
        'method': {'type': str, 'description': 'HTTP method (GET, POST, PUT, DELETE, etc.)'},
        'headers': {'type': dict, 'description': 'HTTP headers'},
        'data': {'type': dict, 'description': 'Request data/payload'},
        'params': {'type': dict, 'description': 'URL query parameters'},
        'timeout': {'type': int, 'description': 'Request timeout in seconds'},
        'auth': {'type': dict, 'description': 'Authentication configuration'},
        'verify_ssl': {'type': bool, 'description': 'Verify SSL certificates'}
    }
    
    required_parameters = ['url', 'method']
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.session = requests.Session()
    
    def pre_execute(self) -> None:
        """Pre-execution setup for REST API calls."""
        super().pre_execute()
        
        # Configure authentication if provided
        auth_config = self.get_parameter('auth')
        if auth_config:
            self._configure_auth(auth_config)
        
        # Configure SSL verification
        verify_ssl = self.get_parameter('verify_ssl', True)
        self.session.verify = verify_ssl
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute REST API call.
        
        Returns:
            Dictionary containing API response data
        """
        url = self.require_parameter('url')
        method = self.require_parameter('method').upper()
        headers = self.get_parameter('headers', {})
        data = self.get_parameter('data')
        params = self.get_parameter('params', {})
        timeout = self.get_parameter('timeout', 30)
        
        # Prepare request
        request_kwargs = {
            'headers': headers,
            'params': params,
            'timeout': timeout
        }
        
        # Add data based on method
        if method in ['POST', 'PUT', 'PATCH'] and data:
            if headers.get('Content-Type') == 'application/json':
                request_kwargs['json'] = data
            else:
                request_kwargs['data'] = data
        
        self.logger.info("Executing REST API call", 
                        method=method,
                        url=url,
                        timeout=timeout)
        
        try:
            # Execute request
            response = self.session.request(method, url, **request_kwargs)
            
            # Parse response
            response_data = self._parse_response(response)
            
            return {
                'url': url,
                'method': method,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'response_data': response_data,
                'response_text': response.text,
                'elapsed_time': response.elapsed.total_seconds()
            }
            
        except requests.exceptions.Timeout:
            raise TaskExecutionError(
                f"Request timed out after {timeout} seconds",
                task_name=self.config.get('name'),
                task_type=self.task_type
            )
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Connection failed: {e}",
                service="REST API",
                endpoint=url
            )
        except requests.exceptions.RequestException as e:
            raise TaskExecutionError(
                f"Request failed: {e}",
                task_name=self.config.get('name'),
                task_type=self.task_type
            )
    
    def _configure_auth(self, auth_config: Dict[str, Any]) -> None:
        """Configure authentication for the session."""
        auth_type = auth_config.get('type', 'basic')
        
        if auth_type == 'basic':
            username = auth_config.get('username')
            password = auth_config.get('password')
            
            if username and password:
                self.session.auth = (username, password)
                self.log_parameter_access('username', masked=False)
                self.log_parameter_access('password', masked=True)
        
        elif auth_type == 'bearer':
            token = auth_config.get('token')
            
            if token:
                self.session.headers.update({'Authorization': f'Bearer {token}'})
                self.log_parameter_access('token', masked=True)
        
        elif auth_type == 'api_key':
            key_name = auth_config.get('key_name', 'X-API-Key')
            key_value = auth_config.get('key_value')
            
            if key_value:
                self.session.headers.update({key_name: key_value})
                self.log_parameter_access('key_value', masked=True)
        
        elif auth_type == 'custom':
            # Custom authentication headers
            headers = auth_config.get('headers', {})
            self.session.headers.update(headers)
        
        self.logger.info("Authentication configured", auth_type=auth_type)
    
    def _parse_response(self, response: requests.Response) -> Any:
        """Parse response based on content type."""
        content_type = response.headers.get('Content-Type', '').lower()
        
        if 'application/json' in content_type:
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
        
        elif 'text/plain' in content_type or 'text/html' in content_type:
            return response.text
        
        else:
            # Try to parse as JSON, fallback to text
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
    
    def post_execute(self, result: Dict[str, Any]) -> None:
        """Post-execution processing for REST calls."""
        super().post_execute(result)
        
        # Log response status
        status_code = result.get('status_code')
        if status_code:
            if 200 <= status_code < 300:
                self.logger.info("REST API call successful", 
                               status_code=status_code,
                               elapsed_time=result.get('elapsed_time'))
            else:
                self.logger.warning("REST API call returned non-success status", 
                                  status_code=status_code,
                                  elapsed_time=result.get('elapsed_time'))
    
    def test_connection(self, url: str, timeout: int = 10) -> bool:
        """
        Test connection to API endpoint.
        
        Args:
            url: URL to test
            timeout: Timeout in seconds
            
        Returns:
            True if connection is successful
        """
        try:
            response = self.session.head(url, timeout=timeout)
            return response.status_code < 500
        except requests.exceptions.RequestException:
            return False
    
    def get_endpoint_info(self, url: str) -> Dict[str, Any]:
        """
        Get information about an API endpoint.
        
        Args:
            url: URL to inspect
            
        Returns:
            Dictionary with endpoint information
        """
        try:
            response = self.session.options(url, timeout=10)
            
            return {
                'url': url,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'allowed_methods': response.headers.get('Allow', ''),
                'content_type': response.headers.get('Content-Type', '')
            }
        except requests.exceptions.RequestException as e:
            return {
                'url': url,
                'error': str(e)
            }
