#!/usr/bin/python3

import requests
import subprocess
from collections import OrderedDict
import json
import pymysql
import logging
import os

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

# --- Configuration ---
# Replace with the actual Spring Boot URL where error logs are sent.
spring_boot_url = os.getenv("SPRING_BOOT_URL", "http://your-spring-boot-url/endpoint")
namespace = os.getenv("K8S_NAMESPACE", "default")  # Kubernetes namespace

# --- Send Payload to Spring Boot URL ---
def send_payload(customer, service_name, pod_status, error, message, env="PROD"):
    payload = OrderedDict([
        ("customer", f"{customer}-{env}"),
        ("error", error),
        ("message", message),
        ("appName", pod_status),
    ])
    try:
        response = requests.post(spring_boot_url, json=payload)
        logging.info(f"Service: {service_name}")
        logging.info(f"Pod Name: {pod_status}")
        logging.info(f"Status Code: {response.status_code}")
        logging.info(f"Response Text: {response.text}")
        logging.info(f"Payload Sent:\n{json.dumps(payload, indent=4)}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending request for {service_name}: {e}")

# --- MySQL Health Check ---
def check_mysql_health(user, password, database):
    try:
        # Fetching MySQL host dynamically
        cmd = "kubectl get svc | grep -i mysql | awk '{print $3}'"
        mysql_host = subprocess.check_output(cmd, shell=True, universal_newlines=True).strip()

        # Connecting to MySQL Database
        connection = pymysql.connect(
            host=mysql_host,
            user=user,
            password=password,
            database=database
        )

        with connection.cursor() as cursor:
            cursor.execute("SELECT value FROM project_settings WHERE settings_key = 'customer'")
            result = cursor.fetchone()
            customer = result[0] if result else "UnknownCustomer"
            logging.info(f"MySQL project_settings customer: {customer}")
        
        connection.close()
        return customer

    except Exception as e:
        logging.error(f"MySQL health check failed: {e}")
        send_payload("mysql", "MySQL_Service", "DB_ERROR", "MYSQL_ERROR", "connection failed")
        return None

# --- Kubernetes Pod Status Check ---
def check_kubernetes_pod_status(base_name):
    try:
        result = subprocess.check_output(
            ['kubectl', 'get', 'pods', '--namespace', namespace, '--no-headers'],
            universal_newlines=True
        )

        if not result.strip():
            logging.warning(f"No pods found for service: {base_name}")
            return None, None

        # Iterating over the pods and checking status
        for line in result.strip().split('\n'):
            parts = line.split()
            if len(parts) < 3:
                logging.warning(f"Skipping invalid line: {line}")
                continue

            pod_name, status = parts[0], parts[2]
            if base_name.replace('-service', '') in pod_name:
                logging.info(f"Found pod: {pod_name} with status: {status}")
                return pod_name, status

        logging.warning(f"No pod found for service: {base_name}")
        return None, None

    except subprocess.CalledProcessError as e:
        logging.error(f"Error checking pod status: {e}")
        return None, None

# --- Service Health Inside Pod ---
def check_service_inside_pod(customer, pod_name, pod_status, service_name):
    if pod_status != "Running":
        logging.warning(f"Pod {pod_name} status is {pod_status} (not Running). Skipping health check curl.")
        send_payload(customer, service_name, pod_name, "POD_NOT_RUNNING", f"Pod status is {pod_status}, service is unavailable")
        return False

    try:
        # Dynamically determine the health endpoint based on service name
        if "dims" in service_name:
            url = f'{service_name}.default.svc.cluster.local/health'
        elif "scheduler" in service_name:
            url = f'{service_name}.default.svc.cluster.local/get'
        else:
            logging.warning(f"Unknown service: {service_name}")
            send_payload(customer, service_name, pod_name, "UNKNOWN_SERVICE", f"Unknown service: {service_name}")
            return False

        cmd = [
            'kubectl', 'exec', '-n', namespace, pod_name, '--',
            'curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', url
        ]
        response_code = subprocess.check_output(cmd, universal_newlines=True).strip()

        if response_code == "200":
            logging.info(f"Service {service_name} inside pod {pod_name} is healthy.")
            return True
        else:
            logging.error(f"Service {service_name} inside pod {pod_name} returned HTTP {response_code}")
            send_payload(customer, service_name, pod_name, "SERVICE_UNHEALTHY", f"Received HTTP {response_code}")
            return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing curl inside pod {pod_name}: {e}")
        send_payload(customer, service_name, pod_name, "CURL_NOT_FOUND", "curl failed from within the pod")
        return False

# --- Get Service Names Dynamically ---
def get_service_names():
    try:
        result = subprocess.check_output(
            ['kubectl', 'get', 'svc', '-n', namespace, '--no-headers'],
            universal_newlines=True
        )

        # Collecting services with dims and scheduler
        services = [
            line.split()[0] for line in result.strip().split('\n')
            if 'dims' in line.split()[0] or 'scheduler' in line.split()[0]
        ]
        return services
    except subprocess.CalledProcessError as e:
        logging.error(f"Error retrieving services: {e}")
        return []

# --- Main Execution ---
def check_services():
    # Check MySQL health and retrieve customer data
    customer = check_mysql_health(user=os.getenv("MYSQL_USER", "default_user"), 
                                  password=os.getenv("MYSQL_PASSWORD", "default_password"), 
                                  database=os.getenv("MYSQL_DB", "dimsdb"))
    if not customer:
        logging.error("Skipping further checks as MySQL is not reachable.")
        return

    # Get service names and check their health
    services = get_service_names()

    if not services:
        logging.warning("No relevant services found in Kubernetes.")
    
    for service in services:
        pod, pod_status = check_kubernetes_pod_status(service)
        if pod:
            check_service_inside_pod(customer, pod, pod_status, service)
        else:
            logging.warning(f"Service {service} pod not found or not running.")
            send_payload(customer, service, "N/A", "SERVICE_NOT_RUNNING", f"No running pods found for service {service}")

if __name__ == "__main__":
    check_services()
