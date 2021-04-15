# Development
See more at https://packaging.python.org/tutorials/packaging-projects/

## Setup
`pip3 install -r requirements.dev.txt`

## Build
Specify version in `setup.py`, then

```
python3 setup.py sdist bdist_wheel
twine check dist/*
```

## Upload to PyPi
```
twine upload dist/*
```

