import logging

COLORS = {
    logging.DEBUG: '\033[36m',    # Cyan
    logging.INFO: '\033[32m',     # Green
    logging.WARNING: '\033[33m',  # Yellow
    logging.ERROR: '\033[31m',    # Red
    logging.CRITICAL: '\033[41m', # Red background
}

RESET = '\033[0m'


def print_colored(level: int, inside_brace: str, message: str, ) -> None:
    """
    Print a message in a color corresponding to a logging level constant.

    Args:
        level (int): One of logging.DEBUG, logging.INFO, etc.
        message (str): The message to print.
    """
    color = COLORS.get(level, '')
    print(f"[{color}{inside_brace}{RESET}] {message}")

if __name__ == "__main__":
    print_colored(logging.DEBUG, "Debug Message")
    print_colored(logging.INFO, "This is info", "Success")
    print_colored(logging.WARNING, "This is a warning", "Invalid Qos")
    print_colored(logging.ERROR, "This is an error")
    print_colored(logging.CRITICAL, "This is critical", "Test Failed")