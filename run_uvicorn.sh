# for local
. .env
# python main.py
hypercorn main:app --bind 0.0.0.0:8080
