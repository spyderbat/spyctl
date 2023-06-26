docker_build:
	docker build -t spyctl_api:latest .

docker-run:
	docker-compose up -d

docker-down:
	docker-compose down --remove-orphans

virtual_env:
	python3.11 -m venv ./spyctl_api_venv --clear

local_spyctl_build:
	(cd ..; pip3.11 uninstall spyctl -y; pip3.11 install .)
	