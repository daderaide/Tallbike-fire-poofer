.PHONY: setup test clean upload

setup:
	python3 -m venv venv && venv/bin/pip install -r requirements.txt

test:
	pytest tests/ -v

clean:
	rm -rf venv __pycache__ .pytest_cache

upload:
	find lib/ -name '.DS_Store' -delete
	mpremote connect /dev/tty.usbserial-110 cp -r lib/ :
	mpremote connect /dev/tty.usbserial-110 cp main.py :main.py
	mpremote connect /dev/tty.usbserial-10 cp -r lib/ :
	mpremote connect /dev/tty.usbserial-10 cp main.py :main.py