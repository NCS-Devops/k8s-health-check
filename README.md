# Kubernetes Health Check and Monitoring Script

This repository contains a Python script that performs health checks on services running within a Kubernetes cluster, integrates with a MySQL database for customer information, and sends error data to a Spring Boot application for monitoring and logging.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Setup](#setup)
- [Usage](#usage)
- [Environment Variables](#environment-variables)

## Overview
This script provides automated health checks for services deployed in a Kubernetes cluster. It performs the following tasks:
- Checks the status of Kubernetes pods
- Verifies the health of services within pods
- Checks MySQL health and retrieves customer data
- Sends monitoring payloads to a Spring Boot service

## Features
- Automated service health checks
- MySQL health check integration
- Dynamic service and pod discovery
- Integration with Spring Boot URL for error logging
- Configurable via environment variables

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/k8s-health-check.git
   cd k8s-health-check
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables (see below for details):
   - `SPRING_BOOT_URL` - URL for your Spring Boot error logging endpoint.
   - `MYSQL_USER` - MySQL database username.
   - `MYSQL_PASSWORD` - MySQL database password.
   - `MYSQL_DB` - The name of the MySQL database.
   - `K8S_NAMESPACE` - Kubernetes namespace to check for services.

4. You can create a `.env` file for local development with the following content:
   ```env
   SPRING_BOOT_URL="http://your-spring-boot-url/endpoint"
   MYSQL_USER="your_mysql_user"
   MYSQL_PASSWORD="your_mysql_password"
   MYSQL_DB="dimsdb"
   K8S_NAMESPACE="default"
   ```

## Usage

To run the script:
```bash
python health_check.py
