#!/usr/bin/env python
from app.main import update_averages, app

with app.app_context():
   update_averages()
