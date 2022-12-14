#!/bin/bash
docker build -t dummy-oauth ./cmds/dummy-oauth -f ./cmds/dummy-oauth/Dockerfile.core
docker build -t interuss-test .
