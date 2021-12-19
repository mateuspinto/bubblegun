all:
	python backend/main.py

run:
	python -m http.server 8000 --directory frontend
