"""Vercel serverless entry point for Django WSGI application."""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from config.wsgi import application

# Vercel Python runtime expects 'app' variable for WSGI
app = application

