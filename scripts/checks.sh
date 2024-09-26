#!/bin/bash


ruff check --fix ./..
bandit -r *.py
