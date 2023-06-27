docker_build:
	docker build -t spyctl_api:latest .

docker_test_build:
	rm -rf ./build
	mkdir ./build
	mkdir ./build/spyctl
	cp -r ../spyctl ../pyproject.toml ./build/spyctl
	docker build -f TestDockerfile -t spyctl_test_api:latest .

docker-run:
	docker-compose up -d

docker-test-run:
	docker-compose -f test-docker-compose.yaml up -d

docker-down:
	docker-compose down --remove-orphans

virtual_env:
	/usr/bin/python3.11 -m venv ./spyctl_api_venv --clear

local_spyctl_build:
	(cd ..; pip3.11 uninstall spyctl -y; pip3.11 install .)
	