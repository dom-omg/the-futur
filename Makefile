.PHONY: install run sleep identity stats

install:
	python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -q

run:
	cd src && ../.venv/bin/python agent.py

sleep:
	cd src && ../.venv/bin/python sleep_engine.py

identity:
	cd src && ../.venv/bin/python -c \
		"from dotenv import load_dotenv; load_dotenv('../.env'); from identity_manager import get_identity_summary; print(get_identity_summary())"

stats:
	cd src && ../.venv/bin/python -c \
		"from dotenv import load_dotenv; load_dotenv('../.env'); from episode_store import episode_count, pattern_count; from identity_manager import load; i=load(); print(f'Episodes: {episode_count()} | Patterns: {pattern_count()} | Sleep cycles: {i[\"sleep_count\"]} | Age: {i[\"age_days\"]}d')"
