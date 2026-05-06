import os
import sys
from radicale import Application, config

# Add the project directory to sys.path
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)

# Load configuration
# We manually load the config file
configuration = config.load([os.path.join(path, "radicale.conf")])

# Create the WSGI application
application = Application(configuration)
