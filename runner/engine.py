"""
Enhanced Engine with multi-cluster support.
"""
import os
import yaml
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import re

from .registry import TaskRegistry
from .storage.sqlite import RunDatabase
from .reporting.html import HTMLReporter
from .reporting.template_manager import TemplateManager
from .errors import AutomationError, TaskExecutionError

logger = logging.getLogger(__name__)


class Engine:
    """Enhanced automation engine with multi-cluster support."""
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.registry = TaskRegistry()
        self.run_db = RunDatabase()
        self.reporter = HTMLReporter()
        self.template_manager = TemplateManager()
    
    def _substitute_environment_variables(self, value: str) -> str:
        """
        Substitute environment variables in a string value.
        
        Args:
            value: String that may contain ${VAR_NAME} placeholders
            
        Returns:
            String with environment variables substituted
        """
        if not isinstance(value, str):
            return value
        
        def replace_var(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        
        return re.sub(r'\$\{([^}]+)\}', replace_var, value)
    
    def _substitute_env_vars_in_config(self, config: Any) -> Any:
        """
        Recursively substitute environment variables in configuration.
        
        Args:
            config: Configuration object (dict, list, or primitive)
            
        Returns:
            Configuration with environment variables substituted
        """
        if isinstance(config, dict):
            return {k: self._substitute_env_vars_in_config(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars_in_config(item) for item in config]
        elif isinstance(config, str):
            return self._substitute_environment_variables(config)
        else:
            return config
        
    def run_multi_cluster_pipeline(self, pipeline_config: Dict[str, Any], 
                                 output_dir: str = "reports") -> Dict[str, Any]:
        """
        Run a pipeline across multiple clusters.
        
        Args:
            pipeline_config: Pipeline configuration with clusters and health_checks
            output_dir: Directory to save reports
            
        Returns:
            Combined results from all clusters
        """
        logger.info(f"Starting multi-cluster pipeline: {pipeline_config.get('name', 'Unknown')}")
        
        # Substitute environment variables in the configuration
        pipeline_config = self._substitute_env_vars_in_config(pipeline_config)
        
        clusters = pipeline_config.get('clusters', [])
        health_checks = pipeline_config.get('health_checks', [])
        
        if not clusters:
            raise AutomationError("No clusters defined in pipeline configuration")
        
        if not health_checks:
            raise AutomationError("No health checks defined in pipeline configuration")
        
        # Validate cluster configurations
        for cluster in clusters:
            if not cluster.get('server') or not cluster.get('token'):
                raise AutomationError(f"Cluster {cluster.get('name', 'Unknown')} missing server or token")
        
        all_results = []
        cluster_results = {}
        
        # Run checks across all clusters
        with ThreadPoolExecutor(max_workers=len(clusters)) as executor:
            # Submit tasks for each cluster
            future_to_cluster = {
                executor.submit(self._run_cluster_checks, cluster, health_checks): cluster
                for cluster in clusters
            }
            
            # Collect results
            for future in as_completed(future_to_cluster):
                cluster = future_to_cluster[future]
                try:
                    cluster_result = future.result()
                    cluster_results[cluster['name']] = cluster_result
                    all_results.extend(cluster_result)
                    logger.info(f"Completed checks for cluster: {cluster['name']}")
                except Exception as e:
                    logger.error(f"Failed to run checks for cluster {cluster['name']}: {e}")
                    # Add error result for failed cluster
                    error_result = self._create_error_result(cluster, health_checks, str(e))
                    cluster_results[cluster['name']] = error_result
                    all_results.extend(error_result)
        
        # Generate multi-cluster report
        report_data = self._prepare_multi_cluster_report_data(
            pipeline_config, all_results, cluster_results
        )
        
        # Save report
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        report_file = output_path / f"multi_cluster_health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html_content = self.template_manager.render_template(
            self.template_manager.get_template('multi-cluster-health-check.html.j2', 'pipelines'),
            report_data
        )
        
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Multi-cluster report generated: {report_file}")
        
        return {
            'pipeline_name': pipeline_config.get('name'),
            'total_clusters': len(clusters),
            'total_checks': len(all_results),
            'cluster_results': cluster_results,
            'report_file': str(report_file)
        }
    
    def _run_cluster_checks(self, cluster: Dict[str, Any], 
                           health_checks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run health checks for a single cluster.
        
        Args:
            cluster: Cluster configuration
            health_checks: List of health check definitions
            
        Returns:
            List of check results for this cluster
        """
        cluster_name = cluster['name']
        logger.info(f"Running health checks for cluster: {cluster_name}")
        
        results = []
        
        for check_def in health_checks:
            try:
                # Create task configuration for this cluster
                task_config = self._create_task_config_for_cluster(check_def, cluster)
                
                # Execute the task
                result = self._execute_single_task(task_config)
                
                # Add cluster-specific metadata
                result['cluster'] = cluster_name
                result['environment'] = cluster.get('environment', 'unknown')
                result['platform'] = cluster_name  # Use cluster name as platform
                
                # Add health check specific data
                result.update({
                    'check_validated': check_def['name'],
                    'remediation_url': check_def.get('remediation_url'),
                    'auto_remediation_job_url': check_def.get('auto_remediation_job_url')
                })
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to run check {check_def['name']} on cluster {cluster_name}: {e}")
                
                # Create error result
                error_result = {
                    'cluster': cluster_name,
                    'environment': cluster.get('environment', 'unknown'),
                    'platform': cluster_name,
                    'check_validated': check_def['name'],
                    'output_details': f"Error: {str(e)}",
                    'errors_in_output': True,
                    'executed_on': datetime.now().isoformat(),
                    'time_taken': '0s',
                    'status': 'Error',
                    'remediation_url': check_def.get('remediation_url'),
                    'auto_remediation_job_url': check_def.get('auto_remediation_job_url')
                }
                results.append(error_result)
        
        return results
    
    def _create_task_config_for_cluster(self, check_def: Dict[str, Any], 
                                       cluster: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create task configuration for a specific cluster.
        
        Args:
            check_def: Health check definition
            cluster: Cluster configuration
            
        Returns:
            Task configuration for this cluster
        """
        task_config = check_def.copy()
        
        # Add cluster-specific credentials
        if task_config['type'] == 'oc_cli':
            task_config['credentials'] = {
                'method': 'token',
                'token': cluster['token'],
                'server': cluster['server']
            }
        elif task_config['type'] == 'rest_call':
            # Replace cluster placeholder in URL
            if '{cluster}' in task_config.get('url', ''):
                task_config['url'] = task_config['url'].replace('{cluster}', cluster['name'])
        
        return task_config
    
    def _execute_single_task(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single task.
        
        Args:
            task_config: Task configuration
            
        Returns:
            Task execution result
        """
        start_time = time.time()
        
        try:
            # Get task class from registry
            task_class = self.registry.get_task(task_config['type'])
            if not task_class:
                raise TaskExecutionError(f"Unknown task type: {task_config['type']}")
            
            # Create and execute task
            task = task_class(task_config)
            result = task.execute()
            
            execution_time = time.time() - start_time
            
            return {
                'name': task_config.get('name', 'Unknown Task'),
                'task_type': task_config['type'],
                'success': True,
                'output_details': str(result.get('output', result)),
                'errors_in_output': False,
                'executed_on': datetime.now().isoformat(),
                'time_taken': f"{execution_time:.1f}s",
                'status': 'Success',
                'result': result
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            return {
                'name': task_config.get('name', 'Unknown Task'),
                'task_type': task_config['type'],
                'success': False,
                'output_details': str(e),
                'errors_in_output': True,
                'executed_on': datetime.now().isoformat(),
                'time_taken': f"{execution_time:.1f}s",
                'status': 'Error',
                'error': str(e)
            }
    
    def _validate_task_config(self, config: Dict[str, Any]) -> None:
        """
        Validate a single task configuration using the TaskRegistry.
        Raises AutomationError if validation fails.
        """
        if 'type' not in config and 'task_type' in config:
            # Accept both 'type' and 'task_type' for compatibility
            config['type'] = config['task_type']
        task_type = config.get('type')
        if not task_type:
            raise AutomationError("Task configuration missing 'type' or 'task_type' field")
        errors = self.registry.validate_task_config(task_type, config)
        if errors:
            raise AutomationError(f"Task configuration validation failed: {'; '.join(errors)}")

    def _validate_pipeline_config(self, config: dict) -> None:
        """
        Validate a pipeline configuration. Raises AutomationError if invalid.
        """
        if 'tasks' not in config or not isinstance(config['tasks'], list) or not config['tasks']:
            raise AutomationError("Pipeline config missing 'tasks' list")
        for task_cfg in config['tasks']:
            self._validate_task_config(task_cfg)

    def _get_task_instance(self, config: dict):
        """
        Get a task instance from the registry given a config dict.
        """
        task_type = config.get('type') or config.get('task_type')
        if not task_type:
            raise AutomationError("Task config missing 'type' or 'task_type'")
        task_class = self.registry.get_task(task_type)
        return task_class(config)
    
    def _create_error_result(self, cluster: Dict[str, Any], 
                           health_checks: List[Dict[str, Any]], 
                           error_message: str) -> List[Dict[str, Any]]:
        """
        Create error results for a failed cluster.
        
        Args:
            cluster: Cluster configuration
            health_checks: List of health check definitions
            error_message: Error message
            
        Returns:
            List of error results
        """
        results = []
        cluster_name = cluster['name']
        
        for check_def in health_checks:
            error_result = {
                'cluster': cluster_name,
                'environment': cluster.get('environment', 'unknown'),
                'platform': cluster_name,
                'check_validated': check_def['name'],
                'output_details': f"Cluster connection failed: {error_message}",
                'errors_in_output': True,
                'executed_on': datetime.now().isoformat(),
                'time_taken': '0s',
                'status': 'Error',
                'remediation_url': check_def.get('remediation_url'),
                'auto_remediation_job_url': check_def.get('auto_remediation_job_url')
            }
            results.append(error_result)
        
        return results
    
    def _prepare_multi_cluster_report_data(self, pipeline_config: Dict[str, Any],
                                         all_results: List[Dict[str, Any]],
                                         cluster_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data for multi-cluster report.
        
        Args:
            pipeline_config: Pipeline configuration
            all_results: All check results
            cluster_results: Results grouped by cluster
            
        Returns:
            Report data for template
        """
        # Calculate environment summary
        environment_summary = {}
        for cluster_name, results in cluster_results.items():
            env = results[0].get('environment', 'unknown') if results else 'unknown'
            if env not in environment_summary:
                environment_summary[env] = {'clusters': 0, 'total_checks': 0, 'successful_checks': 0}
            
            environment_summary[env]['clusters'] += 1
            environment_summary[env]['total_checks'] += len(results)
            environment_summary[env]['successful_checks'] += len([r for r in results if r['status'] == 'Success'])
        
        # Calculate success rates
        for env in environment_summary:
            total = environment_summary[env]['total_checks']
            successful = environment_summary[env]['successful_checks']
            environment_summary[env]['success_rate'] = (successful / total * 100) if total > 0 else 0
        
        return {
            'pipeline_name': pipeline_config.get('name'),
            'execution_date': datetime.now().isoformat(),
            'total_duration': 'N/A',  # Could calculate from start/end times
            'checks': all_results,
            'clusters': pipeline_config.get('clusters', []),
            'environment_summary': environment_summary,
            'generated_at': datetime.now().isoformat(),
            'recommendations': self._generate_recommendations(all_results)
        }
    
    def _generate_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        Generate recommendations based on results.
        
        Args:
            results: All check results
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Count issues by cluster
        cluster_issues = {}
        for result in results:
            if result['status'] in ['Error', 'Fail']:
                cluster = result['cluster']
                if cluster not in cluster_issues:
                    cluster_issues[cluster] = []
                cluster_issues[cluster].append(result['check_validated'])
        
        # Generate recommendations
        for cluster, issues in cluster_issues.items():
            if len(issues) > 2:
                recommendations.append(f"Multiple issues detected in {cluster}. Consider cluster-wide investigation.")
            elif len(issues) == 1:
                recommendations.append(f"Address {issues[0]} issue in {cluster}.")
        
        # Environment-specific recommendations
        prod_issues = [r for r in results if r['status'] in ['Error', 'Fail'] and r.get('environment') == 'prod']
        if prod_issues:
            recommendations.append("Critical: Production environment has issues. Prioritize immediate resolution.")
        
        return recommendations
