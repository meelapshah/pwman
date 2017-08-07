from setuptools import setup

setup(
  name="Password Manager",
  version="1.0",
  py_modules=[ "pwman" ],
  install_requires=[
    "sqlalchemy",
    "terminaltables"
  ],
  author="Meelap Shah",
  author_email="meelapshah@gmail.com",
  description="Store and retrieve passwords into sqlite.",
  entry_points={
    "console_scripts": [
      "pwman = pwman:main",
    ]
  }
)
