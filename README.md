# Automation Tool

A comprehensive automation framework for executing pipelines and tasks across various platforms and services.

## Features

- **Multi-Platform Support**: Execute tasks on OpenShift, AWS, REST APIs, and shell commands
- **Plugin Architecture**: Extensible task system with automatic discovery
- **Structured Logging**: Comprehensive logging with JSONL and SQLite storage
- **Credential Management**: Support for Jenkins environment variables and HashiCorp Vault
- **Reporting**: HTML and CSV report generation with Jinja2 templates
- **CLI Interface**: Easy-to-use command-line interface
- **Error Handling**: Robust error handling with context-aware exceptions

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd automation-tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run a pipeline:
```bash
python -m runner.cli run configs/pipelines/daily-health.yaml
```

### Basic Usage

#### Running a Pipeline
```bash
# Run a pipeline with output directory
python -m runner.cli run configs/pipelines/daily-health.yaml -o reports/

# Dry run to see what would be executed
python -m runner.cli run configs/pipelines/daily-health.yaml --dry-run
```

#### Running a Single Task
```bash
# Run a single task
python -m runner.cli task configs/tasks/oc-project-health.yaml

# Dry run a task
python -m runner.cli task configs/tasks/oc-project-health.yaml --dry-run
```

#### Listing Available Resources
```bash
# List available tasks
python -m runner.cli list-tasks

# List available pipelines
python -m runner.cli list-pipelines
```

## Architecture

### Directory Structure

```
automation-tool/
├── Jenkinsfile                 # CI/CD pipeline configuration
├── requirements.txt            # Python dependencies
├── runner/                     # Core automation engine
│   ├── __init__.py
│   ├── cli.py                  # Command-line interface
│   ├── engine.py               # Main orchestration engine
│   ├── registry.py             # Plugin discovery and registration
│   ├── loggingx.py             # Structured logging setup
│   ├── errors.py               # Custom exceptions
│   ├── creds/                  # Credential management
│   │   ├── base.py             # Abstract credential provider
│   │   ├── jenkins_env.py      # Jenkins environment variables
│   │   └── vault.py            # HashiCorp Vault integration
│   ├── tasks/                  # Task implementations
│   │   ├── base.py             # Abstract task base class
│   │   ├── oc_cli.py           # OpenShift CLI tasks
│   │   ├── aws_cli.py          # AWS CLI tasks
│   │   ├── rest_call.py        # REST API tasks
│   │   ├── shell.py            # Shell command tasks
│   │   └── web_screenshot.py   # Web screenshot tasks
│   ├── reporting/              # Report generation
│   │   ├── html.py             # HTML report generator
│   │   └── csvx.py             # CSV utilities
│   └── storage/                # Data persistence
│       ├── sqlite.py           # SQLite database
│       └── jsonl.py            # JSONL logging
├── configs/                    # Configuration files
│   ├── pipelines/              # Pipeline definitions
│   └── tasks/                  # Task configurations
│       ├── oc-project-health.yaml
│       ├── aws-cost-snapshot.yaml
│       ├── api-tufin-ticket-pull.yaml
│       ├── web-dashboard-screenshot.yaml
│       └── authenticated-web-screenshot.yaml
├── templates/                  # Jinja2 templates
│   └── report.html.j2          # HTML report template
└── docs/                       # Documentation
    └── diagrams/               # Architecture diagrams
```

### Core Components

#### Engine
The `Engine` class orchestrates pipeline and task execution:
- Loads and validates configurations
- Manages task execution lifecycle
- Handles error recovery and logging
- Generates reports

#### Task Registry
The `TaskRegistry` provides plugin discovery:
- Automatically discovers task implementations
- Validates task configurations
- Provides metadata for available tasks

#### Credential Providers
Multiple credential management options:
- **Jenkins Environment**: Read from Jenkins environment variables
- **HashiCorp Vault**: Secure credential storage and retrieval
- **Extensible**: Add custom credential providers

#### Task Types

##### OpenShift CLI (`oc_cli`)
Execute OpenShift CLI commands:
```yaml
name: "Check Cluster Health"
type: "oc_cli"
command: "get nodes"
args: ["-o", "json"]
output_format: "json"
credentials:
  method: "token"
  token: "${OC_TOKEN}"
  server: "${OC_SERVER}"
```

##### AWS CLI (`aws_cli`)
Execute AWS CLI commands:
```yaml
name: "Get Cost Data"
type: "aws_cli"
command: "ce"
args: ["get-cost-and-usage", "--time-period", "Start=2024-01-01,End=2024-12-31"]
output_format: "json"
credentials:
  access_key_id: "${AWS_ACCESS_KEY_ID}"
  secret_access_key: "${AWS_SECRET_ACCESS_KEY}"
```

##### REST API (`rest_call`)
Make HTTP requests:
```yaml
name: "API Health Check"
type: "rest_call"
url: "https://api.example.com/health"
method: "GET"
timeout: 60
auth:
  type: "bearer"
  token: "${API_TOKEN}"
```

##### Shell Commands (`shell`)
Execute shell commands:
```yaml
name: "System Check"
type: "shell"
command: "df"
args: ["-h"]
working_dir: "/tmp"
env_vars:
  CHECK_TYPE: "disk_usage"
```

##### Web Screenshots (`web_screenshot`)
Take screenshots of web pages using Selenium WebDriver:
```yaml
name: "Dashboard Screenshot"
type: "web_screenshot"
url: "https://example.com/dashboard"
output_path: "screenshots/dashboards"
browser: "chrome"
headless: true
wait_for_element: ".dashboard-content"
delay: 3
full_page: true
pre_screenshot_script: |
  // Custom JavaScript to execute before screenshot
  document.getElementById('refresh-btn').click();
  return new Promise(resolve => setTimeout(resolve, 2000));
```

## Configuration

### Pipeline Configuration

Pipelines are defined in YAML files:

```yaml
name: "Daily Health Check"
description: "Daily health check pipeline"
schedule: "0 6 * * *"  # Daily at 6 AM
timeout: 3600  # 1 hour

tasks:
  - name: "Check OpenShift Health"
    type: "oc_cli"
    command: "get nodes"
    # ... task configuration

  - name: "Check AWS Health"
    type: "aws_cli"
    command: "health"
    # ... task configuration
```

### Task Configuration

Individual tasks can be configured with:

- **Basic Parameters**: name, type, description
- **Execution Parameters**: command, args, timeout
- **Authentication**: credentials for various services
- **Output Handling**: format, filtering, processing
- **Error Handling**: retry logic, failure conditions

### Environment Variables

The tool supports environment variable substitution:

```yaml
credentials:
  token: "${OC_TOKEN}"
  server: "${OC_SERVER}"
```

## Credential Management

### Jenkins Environment
Automatically reads from Jenkins environment variables:
- `OC_TOKEN`, `OC_SERVER` for OpenShift
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` for AWS
- `CREDENTIAL_*` prefixed variables

### HashiCorp Vault
Secure credential storage:
```python
from runner.creds import VaultCredentialProvider

provider = VaultCredentialProvider(
    vault_url="https://vault.example.com",
    auth_method="token"
)
credential = provider.get_credential("secret/myapp/db")
```

## Reporting

The tool generates comprehensive reports using a **modular template system** with Jinja2:

### 🎯 Modular Template System

The reporting system supports hierarchical template selection:

1. **Custom Task Template** (highest priority) - Specified in task config
2. **Task Type Template** - Specific to task type (e.g., `oc_cli.html.j2`)
3. **Pipeline Template** - Specified in pipeline config
4. **Global Default Template** (fallback) - Default for all reports

### 📊 Template Types

- **Base Templates** (`templates/base/`) - Common layout and styling
- **Global Templates** (`templates/global/`) - Default templates for all reports
- **Task Type Templates** (`templates/task-types/`) - Specific to task types
- **Pipeline Templates** (`templates/pipelines/`) - Pipeline-specific templates
- **Custom Templates** (`templates/custom/`) - User-defined templates

### 📋 Report Formats

- **HTML Reports**: Rich, interactive reports with charts and detailed information
- **CSV Export**: Data export for further analysis
- **JSONL Logs**: Append-only logs for audit trails

### 🔧 Template Configuration

**Pipeline Configuration:**
```yaml
name: "Daily Health Check"
template: "health-check.html.j2"  # Pipeline template
tasks:
  - name: "Check Pods"
    type: "oc_cli"
    template: "oc_cli.html.j2"  # Task-specific template
```

**Task Configuration:**
```yaml
name: "Custom Task"
type: "shell"
template: "custom-template.html.j2"  # Custom template
template_data:
  custom_field: "Custom Value"
```

### 📊 Health Check Reports

The system includes a specialized health check template with your exact requirements:

**Column Headers:**
- Platform (e.g., ROSA_SANDPIT)
- Check Validated (e.g., PendingPods)
- Output Details (Task output)
- Errors in Output (True/False)
- Check Executed On (DateTime)
- Time Taken (e.g., 10ms)
- Status (Error/Fail/Success)
- Remediation (Document link)
- Auto Remediation (Jenkins job button or "No Auto-Remediation Identified")

### 🚀 Testing Templates

Test the template system with sample data:
```bash
python test_templates.py
```

This generates example reports in the `reports/` directory.

## Logging

### Structured Logging
All operations are logged with structured data:
```python
import structlog

logger = structlog.get_logger(__name__)
logger.info("Task completed", task_name="health_check", duration=5.2)
```

### Storage Options
- **SQLite Database**: Persistent storage for run history
- **JSONL Files**: Append-only log files with compression
- **Console Output**: Human-readable and JSON formats

## Error Handling

### Custom Exceptions
The tool provides context-aware exceptions:
- `AutomationError`: Base exception class
- `TaskExecutionError`: Task-specific errors
- `CredentialError`: Authentication failures
- `ConfigurationError`: Invalid configurations

### Error Recovery
- Automatic retry for transient failures
- Graceful degradation for non-critical tasks
- Detailed error reporting with context

## Development

### Testing

The project includes a comprehensive test suite to ensure code quality and prevent regressions:

```bash
# Run all tests
python run_tests.py

# Run with coverage
python run_tests.py --coverage

# Run only unit tests
python run_tests.py --unit-only

# Run only integration tests
python run_tests.py --integration-only

# Run fast tests (skip slow/external)
python run_tests.py --fast
```

**Pre-commit Hook**: Tests run automatically before each commit to ensure code quality.

**Test Coverage**: The test suite covers all core components, task types, and features.

See `tests/README.md` for detailed testing documentation.

### Adding New Task Types

1. Create a new task class inheriting from `Task`:
```python
from runner.tasks.base import Task

class MyCustomTask(Task):
    task_type = "my_custom"
    description = "My custom task"
    
    def execute(self):
        # Implementation here
        return {"result": "success"}
```

2. The task will be automatically discovered by the registry.

3. **Add tests** for your new task type in `tests/unit/test_tasks.py`

### Adding New Credential Providers

1. Create a new provider inheriting from `CredentialProvider`:
```python
from runner.creds.base import CredentialProvider

class MyCredentialProvider(CredentialProvider):
    def get_credential(self, credential_name):
        # Implementation here
        return {"username": "user", "password": "pass"}
```

### Testing

Run the test suite:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=runner tests/
```

## Deployment

### Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
ENTRYPOINT ["python", "-m", "runner.cli"]
```

### Jenkins Integration
The tool is designed to work seamlessly with Jenkins:
- Reads credentials from Jenkins environment
- Generates reports in workspace
- Integrates with Jenkins pipeline stages

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation in the `docs/` directory
- Review example configurations in `configs/`
