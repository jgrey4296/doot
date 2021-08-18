
all : clean

# Building ####################################################################
build:
	python -m build
	pip install -U -e .

# Linting #####################################################################
pylint:
	@echo "Linting"
	pylint --rcfile=./.pylintrc ${TOP} --ignore=${ig} --ignore-patterns=${igpat}

# Cleaning ####################################################################
clean :
	find . -name "*.pyc" | xargs rm
	find . -name "__pycache__" | xargs rm -r
	-rm -rf dist
