
all : clean


#remove all extraneous pycaches and pyc's
clean :
	find . -name "*.pyc" | xargs rm
	find . -name "__pycache__" | xargs rm -r
