"""Import configuration variables from enviroment."""
import os


CONNECT_TIMEOUT = int(os.getenv("KONG__CONNECT_TIMEOUT", 5000))
"""Enviroment variable for connect timeout for the service."""

WRITE_TIMEOUT = int(os.getenv("KONG__WRITE_TIMEOUT", 300000))
"""Enviroment variable for write timeout for the service."""

READ_TIMEOUT = int(os.getenv("KONG__READ_TIMEOUT", 300000))
"""Enviroment variable for read timeout for the service."""

RETRIES = int(os.getenv("KONG__RETRIES", 5))
"""Enviroment variable for retries for the service."""
