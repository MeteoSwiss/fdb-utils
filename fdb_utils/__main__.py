import logging
import sys

from fdb_utils import main


logging.basicConfig(stream=sys.stdout, level=logging.INFO)


main.app()
