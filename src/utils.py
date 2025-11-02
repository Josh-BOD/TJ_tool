"""Utility functions for TrafficJunky Automation Tool."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from colorama import Fore, Style, init

# Initialize colorama for colored console output
init(autoreset=True)


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: str = 'INFO',
    log_to_console: bool = True,
    log_to_file: bool = True
) -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (optional)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_to_file and log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def print_banner():
    """Print tool banner."""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          TrafficJunky Automation Tool v1.0.0                ║
║          Automated Creative Upload System                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)


def print_success(message: str):
    """Print success message in green."""
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")


def print_error(message: str):
    """Print error message in red."""
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")


def print_warning(message: str):
    """Print warning message in yellow."""
    print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")


def print_info(message: str):
    """Print info message in blue."""
    print(f"{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")


def get_timestamp() -> str:
    """Get current timestamp as string."""
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def validate_csv_file(csv_path: Path) -> bool:
    """
    Validate that CSV file exists and is readable.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        True if valid, False otherwise
    """
    if not csv_path.exists():
        print_error(f"CSV file not found: {csv_path}")
        return False
    
    if not csv_path.is_file():
        print_error(f"Path is not a file: {csv_path}")
        return False
    
    if csv_path.suffix.lower() != '.csv':
        print_error(f"File is not a CSV: {csv_path}")
        return False
    
    return True


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}m {seconds:.0f}s"
    
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m"

