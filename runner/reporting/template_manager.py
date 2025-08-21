"""
Template Manager for modular report generation.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
import logging

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages template loading and rendering with hierarchical template selection."""
    
    def __init__(self, template_dir: str = "templates"):
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Template hierarchy paths
        self.template_paths = {
            'base': self.template_dir / 'base',
            'global': self.template_dir / 'global',
            'task_types': self.template_dir / 'task-types',
            'pipelines': self.template_dir / 'pipelines',
            'custom': self.template_dir / 'custom'
        }
        
        # Ensure template directories exist
        for path in self.template_paths.values():
            path.mkdir(parents=True, exist_ok=True)
    
    def select_template(self, 
                       task_config: Dict[str, Any] = None,
                       pipeline_config: Dict[str, Any] = None,
                       task_type: str = None) -> Template:
        """Select template based on configuration hierarchy."""
        # 1. Custom task template
        if task_config and task_config.get('template'):
            template = self.get_template(task_config['template'], 'custom')
            if template:
                return template
        
        # 2. Task type template
        if task_type:
            template_name = f"{task_type}.html.j2"
            template = self.get_template(template_name, 'task_types')
            if template:
                return template
        
        # 3. Pipeline template
        if pipeline_config and pipeline_config.get('template'):
            template = self.get_template(pipeline_config['template'], 'pipelines')
            if template:
                return template
        
        # 4. Global default
        return self.get_template('default-pipeline.html.j2', 'global')
    
    def get_template(self, template_name: str, template_type: str = 'global') -> Optional[Template]:
        """Get a template by name and type."""
        try:
            return self.env.get_template(f"{template_type}/{template_name}")
        except TemplateNotFound:
            logger.warning(f"Template not found: {template_name} in {template_type}")
            return None
    
    def render_template(self, template: Template, data: Dict[str, Any], **kwargs) -> str:
        """Render a template with the provided data."""
        template_data = {**data, **kwargs}
        template_data.update({
            'generated_at': template_data.get('generated_at', 'Unknown'),
            'version': template_data.get('version', '1.0.0')
        })
        return template.render(**template_data)
    
    def render_health_check_report(self, checks: List[Dict[str, Any]], **kwargs) -> str:
        """Render a health check report."""
        template = self.get_template('health-check.html.j2', 'pipelines')
        if not template:
            template = self.select_template()
        
        data = {
            'checks': checks,
            'title': 'Daily Health Check Report',
            'subtitle': 'Health check results'
        }
        return self.render_template(template, data, **kwargs)
    
    def render_multi_cluster_health_check_report(self, checks: List[Dict[str, Any]], 
                                               clusters: List[Dict[str, Any]],
                                               environment_summary: Dict[str, Any],
                                               **kwargs) -> str:
        """Render a multi-cluster health check report."""
        template = self.get_template('multi-cluster-health-check.html.j2', 'pipelines')
        if not template:
            # Fallback to regular health check template
            template = self.get_template('health-check.html.j2', 'pipelines')
            if not template:
                template = self.select_template()
        
        data = {
            'checks': checks,
            'clusters': clusters,
            'environment_summary': environment_summary,
            'title': 'Multi-Cluster Health Check Report',
            'subtitle': 'Health check results across multiple clusters'
        }
        return self.render_template(template, data, **kwargs)
