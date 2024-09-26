#!/bin/bash


black ./..
ruff check --fix
bandit -r *.py
