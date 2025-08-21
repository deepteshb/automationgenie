"""
Command-line interface for the automation tool.
"""

import click
import yaml
import os
from pathlib import Path
from typing import Optional

from .engine import Engine
from .errors import AutomationError


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Automation Tool - Multi-platform automation framework."""
    pass


@cli.command()
@click.argument('pipeline_file', type=click.Path(exists=True))
@click.option('-o', '--output-dir', default='reports', help='Output directory for reports')
@click.option('--dry-run', is_flag=True, help='Show what would be executed without running')
def run(pipeline_file: str, output_dir: str, dry_run: bool):
    """Run a pipeline from configuration file."""
    try:
        engine = Engine()
        
        # Load pipeline configuration
        with open(pipeline_file, 'r') as f:
            pipeline_config = yaml.safe_load(f)
        
        if dry_run:
            click.echo(f"Would run pipeline: {pipeline_config.get('name', 'Unknown')}")
            click.echo(f"Tasks: {len(pipeline_config.get('tasks', []))}")
            return
        
        # Check if this is a multi-cluster pipeline
        if 'clusters' in pipeline_config and 'health_checks' in pipeline_config:
            click.echo(f"Running multi-cluster pipeline: {pipeline_config.get('name', 'Unknown')}")
            result = engine.run_multi_cluster_pipeline(pipeline_config, output_dir)
            click.echo(f"✅ Multi-cluster pipeline completed!")
            click.echo(f"📊 Clusters checked: {result['total_clusters']}")
            click.echo(f"📋 Total checks: {result['total_checks']}")
            click.echo(f"📄 Report: {result['report_file']}")
        else:
            # Regular pipeline execution
            click.echo(f"Running pipeline: {pipeline_config.get('name', 'Unknown')}")
            # This would use the original pipeline execution logic
            click.echo("Regular pipeline execution not yet implemented")
            
    except AutomationError as e:
        click.echo(f"❌ Pipeline execution failed: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('task_file', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True, help='Show what would be executed without running')
def task(task_file: str, dry_run: bool):
    """Run a single task from configuration file."""
    try:
        engine = Engine()
        
        if dry_run:
            click.echo(f"Would run task from: {task_file}")
            return
        
        # Load task configuration
        with open(task_file, 'r') as f:
            task_config = yaml.safe_load(f)
        
        click.echo(f"Running task: {task_config.get('name', 'Unknown')}")
        # This would use the original task execution logic
        click.echo("Task execution not yet implemented")
        
    except AutomationError as e:
        click.echo(f"❌ Task execution failed: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@cli.command()
def list_tasks():
    """List all available tasks."""
    try:
        engine = Engine()
        tasks = engine.registry.list_tasks()
        click.echo("Available tasks:")
        for task_name, task_info in tasks.items():
            click.echo(f"  {task_name}: {task_info.get('description', 'No description')}")
    except AutomationError as e:
        click.echo(f"Error listing tasks: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--config-dir', default='configs', help='Configuration directory')
def list_pipelines(config_dir: str):
    """List all available pipelines."""
    try:
        config_path = Path(config_dir)
        if not config_path.exists():
            click.echo(f"Configuration directory not found: {config_dir}")
            return
        
        pipeline_dir = config_path / 'pipelines'
        if not pipeline_dir.exists():
            click.echo(f"Pipelines directory not found: {pipeline_dir}")
            return
        
        click.echo("Available pipelines:")
        for pipeline_file in pipeline_dir.glob('*.yaml'):
            try:
                with open(pipeline_file, 'r') as f:
                    pipeline_config = yaml.safe_load(f)
                name = pipeline_config.get('name', pipeline_file.stem)
                description = pipeline_config.get('description', 'No description')
                
                # Check if it's a multi-cluster pipeline
                if 'clusters' in pipeline_config:
                    cluster_count = len(pipeline_config['clusters'])
                    click.echo(f"  {name} (Multi-cluster: {cluster_count} clusters): {description}")
                else:
                    click.echo(f"  {name}: {description}")
                    
            except Exception as e:
                click.echo(f"  {pipeline_file.name}: Error reading configuration")
                
    except Exception as e:
        click.echo(f"Error listing pipelines: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('cluster_names', nargs=-1)
@click.option('--check-type', default='PendingPods', help='Type of health check to run')
@click.option('-o', '--output-dir', default='reports', help='Output directory for reports')
def health_check(cluster_names, check_type: str, output_dir: str):
    """Run health checks on specified clusters."""
    try:
        if not cluster_names:
            click.echo("Please specify at least one cluster name")
            return
        
        engine = Engine()
        
        # Create a simple multi-cluster configuration
        pipeline_config = {
            'name': f'Health Check - {check_type}',
            'clusters': [],
            'health_checks': [
                {
                    'name': check_type,
                    'type': 'oc_cli',
                    'command': 'get',
                    'args': ['pods', '--all-namespaces', '--field-selector=status.phase=Pending', '-o', 'json'],
                    'output_format': 'json',
                    'remediation_url': f'https://docs.example.com/{check_type.lower()}',
                    'auto_remediation_job_url': f'https://jenkins.example.com/job/fix-{check_type.lower()}'
                }
            ]
        }
        
        # Add clusters based on environment variables
        for cluster_name in cluster_names:
            server_var = f'{cluster_name}_SERVER'
            token_var = f'{cluster_name}_TOKEN'
            
            server = os.environ.get(server_var)
            token = os.environ.get(token_var)
            
            if not server or not token:
                click.echo(f"⚠️  Missing environment variables for {cluster_name}: {server_var}, {token_var}")
                continue
            
            # Determine environment based on cluster name
            if 'PROD' in cluster_name:
                environment = 'prod'
            elif 'NON_PROD' in cluster_name:
                environment = 'non-prod'
            else:
                environment = 'sandbox'
            
            pipeline_config['clusters'].append({
                'name': cluster_name,
                'server': server,
                'token': token,
                'environment': environment
            })
        
        if not pipeline_config['clusters']:
            click.echo("❌ No valid clusters found. Please check environment variables.")
            return
        
        click.echo(f"Running {check_type} health check on {len(pipeline_config['clusters'])} clusters...")
        result = engine.run_multi_cluster_pipeline(pipeline_config, output_dir)
        
        click.echo(f"✅ Health check completed!")
        click.echo(f"📊 Clusters checked: {result['total_clusters']}")
        click.echo(f"📋 Total checks: {result['total_checks']}")
        click.echo(f"📄 Report: {result['report_file']}")
        
    except AutomationError as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli()
