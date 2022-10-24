#!/bin/sh

# This runs the app through a wsgi server (Gunicorn) which is preferred for production environments.

gunicorn --bind 0.0.0.0:8000 "app:create_app()"
