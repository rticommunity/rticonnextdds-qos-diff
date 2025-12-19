##############################################################################################
# (c) 2024-2025 Copyright, Real-Time Innovations, Inc. (RTI) All rights reserved.
#
# RTI grants Licensee a license to use, modify, compile, and create derivative works of the
# software solely for use with RTI Connext DDS. Licensee may redistribute copies of the
# software, provided that all such copies are subject to this license. The software is
# provided "as is", with no warranty of any type, including any warranty for fitness for any
# purpose. RTI is under no obligation to maintain or support the software. RTI shall not be
# liable for any incidental or consequential damages arising out of the use or inability to
# use the software.
#
##############################################################################################

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