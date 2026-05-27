#!/usr/bin/env python3

"""
AI Shell | Strands AgentShell
Execute AI agent scripts with shebang syntax

This script parses and executes agent scripts with special directive syntax.
Agent scripts can define their configuration using #@ directives and contain
a system prompt that guides the agent's behavior.

Dependencies:
    bedrock-agentcore
    strands-agents
    strands-agents-tools[use_browser]

Example usage:
    echo "test" | python aish.py script.ai
    cat input.txt | python aish.py script.ai
    python aish.py script.ai < input.txt
    python aish.py script.ai  # Can work without stdin if agent doesn't need it

Tool support:
    'browser', 'editor', 'file_read', 'file_write', 'generate_image',
    'generate_image_stability', 'http_request', 'nova_reels', 'retrieve'
    https://github.com/strands-agents/tools

Example `summarize.ai` file:
```
#!/usr/bin/env aish.py
# summarize.ai - Simple text summarization script
# Usage: cat document.txt | summarize.ai

#@ model: us.amazon.nova-lite-v1:0
#@ temperature: 0.1
#@ max_tokens: 2048
#@ tools: file_read

You are a text summarization experts. Your task is to:
1. Read the input text carefully
2. Extract the key points and main ideas
3. Create a concise summary that captures the essence
4. Keep the summary clear and well-organized

Provide a summary that is approximately 20% of the original length
```

Example `meeting_notes.ai` file:
```
#!/usr/bin/env aish.py
# meeting_notes.ai - Meeting notes formatter
# Usage: cat raw_notes.txt | meeting_notes.ai

#@ model: us.amazon.nova-pro-v1:0
#@ temperature: 0.2
#@ max_tokens: 4096
#@ tools: file_read

You are an executive assistant. Transform rough meeting notes into:
1. **Meeting Overview**: Date, attendees, purpose
2. **Key Discussion Points**: Main topics covered
3. **Decisions Made**: Clear list of decisions
4. **Action Items**: Tasks with owners and deadlines
5. **Next Steps**: Follow-up activities

Format as a professional meeting summary document.
```
"""

import argparse
import logging
import os
import re
import sys

from botocore.config import Config
from dotenv import load_dotenv
from pathlib import Path
from strands import Agent
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel
from typing import Any, Dict, List, Optional

# Load environment variables from .env file if it exists
load_dotenv()

LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger("strands").setLevel(LOG_LEVEL)

# Default configuration
BEDROCK_REGION = os.getenv("BEDROCK_REGION", 'us-west-2')
DEFAULT_MODEL_ID = os.getenv('AISH_MODEL_ID', 'us.amazon.nova-lite-v1:0')
DEFAULT_TEMPERATURE = float(os.getenv('AISH_TEMPERATURE', '0.1'))
DEFAULT_MAX_TOKENS = int(os.getenv('AISH_MAX_TOKENS', '2048'))
logger.debug(f'BEDROCK_REGION={BEDROCK_REGION}')
logger.debug(f'DEFAULT_MODEL_ID={DEFAULT_MODEL_ID}')
logger.debug(f'DEFAULT_TEMPERATURE={DEFAULT_TEMPERATURE}')
logger.debug(f'DEFAULT_MAX_TOKENS={DEFAULT_MAX_TOKENS}')

def get_tool(tool: str) -> Any:
    """
    Get a tool instance by name from the strands-tools library.

    Returns tools listed here:
    https://github.com/strands-agents/tools

    Args:
        tool (str): Name of the tool to retrieve. Valid options include:
            'browser', 'editor', 'file_read', 'file_write', 'generate_image',
            'generate_image_stability', 'http_request', 'nova_reels', 'retrieve'

    Returns:
        Any: The tool instance or function, ready to be used by the agent

    Raises:
        ValueError: If the tool name is not recognized or supported
        ImportError: If required tool dependencies are not installed
    """
    from strands_tools import (
        editor,
        file_read,
        file_write,
        generate_image,
        generate_image_stability,
        http_request,
        nova_reels,
        retrieve,
    )

    tools = {
        'editor': editor,
        'file_read': file_read,
        'file_write': file_write,
        'generate_image': generate_image,
        'generate_image_stability': generate_image_stability,
        'http_request': http_request,
        'nova_reels': nova_reels,
        'retrieve': retrieve
    }

    if tool == 'browser':
        error_msg = 'Browser tool is managed separately in execute_agent'
        logger.error(error_msg)
        raise ValueError(error_msg)

    if tool not in tools:
        error_msg = f'Invalid or unsupported tool: {tool}'
        logger.error(error_msg)
        raise ValueError(error_msg)

    return tools[tool]


def _substitute_env_vars(value: str) -> str:
    """
    Substitute environment variables in directive values.

    Syntax: {VAR_NAME} expands to os.environ['VAR_NAME'].
    Only uppercase identifiers with letters/numbers/underscores are expanded.

    Args:
        value: String potentially containing {VAR_NAME} placeholders

    Returns:
        String with environment variables substituted

    Raises:
        ValueError: If referenced variable doesn't exist
    """
    def replace_var(match):
        var_name = match.group(1)
        if var_name not in os.environ:
            raise ValueError(f"Environment variable not found: {var_name}")
        return os.environ[var_name]

    try:
        return re.sub(r'\{([A-Z_][A-Z0-9_]*)\}', replace_var, value)
    except ValueError:
        raise


def parse_agent_script(script_path: str) -> Dict[str, Any]:
    """
    Parse agent script to extract configuration and system prompt.

    The script format supports:
    - Shebang line (ignored if present)
    - #@ directives for configuration (e.g., #@ model: model-id)
    - Environment variable substitution in directives: {VAR_NAME}
    - System prompt as non-comment lines

    Args:
        script_path (str): Path to the agent script file

    Returns:
        dict: Configuration dictionary containing:
            - model (str): Model ID to use
            - temperature (float): Sampling temperature
            - max_tokens (int): Maximum tokens to generate
            - tools (list): List of tool names to enable
            - skills (list): List of skills to load (optional)
            - system_prompt (str): The system prompt for the agent

    Raises:
        FileNotFoundError: If the script file does not exist
        ValueError: If the script contains invalid configuration directives
        PermissionError: If the script file cannot be read

    Example:
        Script file content:
            #!/usr/bin/env aish.py
            #@ model: {BEDROCK_MODEL}
            #@ temperature: 0.7
            #@ tools: file_read, file_write
            #@ skills: summarize, format

            You are a helpful assistant that processes text files.

        With .env:
            BEDROCK_MODEL=us.amazon.nova-lite-v1:0
    """
    script_file = Path(script_path)

    if not script_file.exists():
        raise FileNotFoundError(f"Agent script not found: {script_path}")

    if not script_file.is_file():
        raise ValueError(f"Path is not a file: {script_path}")

    try:
        with open(script_path) as f:
            lines = f.readlines()
    except PermissionError as e:
        raise PermissionError(f"Cannot read script file: {script_path}") from e

    # Skip shebang
    if lines and lines[0].startswith('#!'):
        lines = lines[1:]

    # Default config
    config = {
        'model': DEFAULT_MODEL_ID,
        'temperature': DEFAULT_TEMPERATURE,
        'max_tokens': DEFAULT_MAX_TOKENS,
        'tools': [],
        'skills': []
    }

    system_prompt_lines = []

    for line_num, line in enumerate(lines, start=1):
        # Parse #@ directives
        if line.startswith('#@ '):
            directive = line[3:].strip()
            if ':' in directive:
                key, value = directive.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Substitute environment variables in directive values
                try:
                    value = _substitute_env_vars(value)
                except ValueError as e:
                    raise ValueError(f"Variable substitution error at line {line_num}: {e}") from e

                if key == 'model':
                    config['model'] = value
                elif key == 'tools':
                    config['tools'] = [t.strip() for t in value.split(',')]
                elif key == 'skills':
                    config['skills'] = [s.strip() for s in value.split(',')]
                elif key == 'temperature':
                    try:
                        config[key] = float(value)
                        if not 0 <= config[key] <= 1:
                            logger.warning(f"Temperature {value} outside [0,1] range at line {line_num}")
                    except ValueError as e:
                        raise ValueError(f"Invalid temperature value '{value}' at line {line_num}") from e
                elif key == 'max_tokens':
                    try:
                        config[key] = int(value)
                        if config[key] <= 0:
                            raise ValueError(f"max_tokens must be positive at line {line_num}")
                    except ValueError as e:
                        raise ValueError(f"Invalid max_tokens value '{value}' at line {line_num}") from e
                else:
                    config[key] = value
            else:
                logger.warning(f"Malformed directive at line {line_num}: {line.strip()}")
        elif not line.startswith('#'):
            # System prompt content
            system_prompt_lines.append(line)

    config['system_prompt'] = ''.join(system_prompt_lines).strip()

    if not config['system_prompt']:
        logger.warning(f"No system prompt found in {script_path}")

    return config


def execute_agent(script_path: str, stdin_input: str, **kwargs) -> str:
    """
    Execute agent script with given input.

    Args:
        script_path (str): Path to the agent script
        stdin_input (str): Input string to process (can be empty)
        **kwargs: Additional arguments from command line (currently unused)

    Returns:
        str: Output generated by the agent

    Raises:
        FileNotFoundError: If script file doesn't exist
        ValueError: If script configuration is invalid or tools are unavailable
        RuntimeError: If agent execution fails

    Example:
        >>> result = execute_agent("process.ai", "Hello world")
        >>> print(result)
    """
    # Parse the agent script
    try:
        config = parse_agent_script(script_path)
    except (FileNotFoundError, ValueError, PermissionError) as e:
        logger.error(f"Failed to parse agent script: {e}")
        raise

    # Build the model
    try:
        model = BedrockModel(
            model_id=config['model'],
            temperature=config['temperature'],
            max_tokens=config['max_tokens'],
            boto_client_config=Config(
                read_timeout=120,
                connect_timeout=120,
                retries=dict(max_attempts=3, mode="adaptive"),
            )
        )
    except Exception as e:
        logger.error(f"Failed to initialize model: {e}")
        raise RuntimeError(f"Model initialization failed: {e}") from e

    # Load tools
    browser = None
    try:
        tools = []
        for t in config['tools']:
            if t == 'browser':
                from strands_tools.browser import LocalChromiumBrowser
                browser = LocalChromiumBrowser()
                tools.append(browser.browser)
            else:
                tools.append(get_tool(t))
    except (ValueError, ImportError) as e:
        if browser:
            try:
                browser.close()
            except Exception as close_err:
                logger.warning(f"Failed to close browser: {close_err}")
        logger.error(f"Failed to load tools: {e}")
        raise ValueError(f"Tool loading failed: {e}") from e

    # Build the agent
    try:
        agent = Agent(
            system_prompt=config['system_prompt'],
            model=model,
            tools=tools,
            callback_handler=PrintingCallbackHandler()
        )
    except Exception as e:
        if browser:
            try:
                browser.close()
            except Exception as close_err:
                logger.warning(f"Failed to close browser: {close_err}")
        logger.error(f"Failed to create agent: {e}")
        raise RuntimeError(f"Agent creation failed: {e}") from e

    # Execute
    try:
        result = agent(stdin_input)
        return result
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise RuntimeError(f"Agent execution failed: {e}") from e
    finally:
        if browser:
            try:
                logger.debug("Closing browser resource")
                browser.close()
            except Exception as close_err:
                logger.warning(f"Failed to close browser: {close_err}")


def main(stdin_input: str, args: argparse.Namespace) -> None:
    """
    Main processing function.

    Args:
        stdin_input (str): Input from stdin (can be empty string)
        args (argparse.Namespace): Parsed command line arguments containing:
            - script: Path to the agent script
            - args: Additional positional arguments (currently unused)

    Raises:
        SystemExit: If agent execution fails with non-zero exit code
    """
    # Convert args namespace to dict, excluding 'script' and 'args' fields
    kwargs = {k: v for k, v in vars(args).items() if k not in ['script', 'args']}
    try:
        result = execute_agent(args.script, stdin_input, **kwargs)
        print()
        # print(result)  # Add this only if the agent's callback_handler=None
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        logger.error(f"Execution failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)


def get_stdin() -> str:
    """
    Get input from stdin if available.

    Checks whether stdin is connected to a terminal (interactive mode) or
    has piped/redirected input available.

    Returns:
        str: Input from stdin, or empty string if no input is available

    Note:
        This function will block if stdin is being piped but no data is available yet.
        In interactive terminal mode, it returns immediately with an empty string.
    """
    # Check if stdin is connected to a terminal (interactive) or a pipe/file
    if sys.stdin.isatty():
        return ''  # Interactive terminal - no piped input
    else:
        return sys.stdin.read().strip()  # Input is being piped or redirected


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Execute Strands agent scripts with AI-powered processing',
        epilog='Examples:\n'
               '  echo "test" | python aish.py script.ai\n'
               '  cat input.txt | python aish.py script.ai\n'
               '  python aish.py script.ai < input.txt',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('script', help='Agent script file to execute')
    parser.add_argument('args', nargs='*', help='Arguments to pass to agent (not yet implemented)')
    args = parser.parse_args()

    stdin_input = get_stdin()

    # Always execute the agent, even without stdin input
    # The agent script may not require stdin input
    main(stdin_input, args)
