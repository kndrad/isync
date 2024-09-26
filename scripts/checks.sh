#!/bin/bash


ruff format ./..
ruff check --fix ./..

bandit -r *.py
