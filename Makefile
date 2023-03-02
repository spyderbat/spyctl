build:
	python3 -m build

test_build: clean
	pip uninstall spyctl -y
	pip install .

release:
	python3 -m twine upload dist/*

release_to_test_pypi:
	python3 -m twine upload --repository testpypi dist/*

install_from_test:
	pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple spyctl

venv:
	python3 -m venv ~/spyctl_demo --clear

clean:
	rm -rf ./dist
	rm -rf ./spyctl.egg-info
	rm -rf ./build

.PHONY: rebuild
rebuild:
	$(MAKE) clean
	$(MAKE) build

test_coverage:
	coverage run --omit="test_*.py" -m pytest

view_coverage_wsl:
	coverage html
	explorer.exe "htmlcov\index.html" ||:
