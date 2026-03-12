import sys
import logging
import os

logging.basicConfig(stream=sys.stderr)
os.environ['LANG'] = "en_US.UTF-8"
os.environ['LC_ALL'] = 'en_us.UTF-8'

sys.path.insert(0, "/var/www/bytequest")

from app import application
