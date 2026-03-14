import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Add Django project folder to Python path
sys.path.append(str(BASE_DIR / "khaubot"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()