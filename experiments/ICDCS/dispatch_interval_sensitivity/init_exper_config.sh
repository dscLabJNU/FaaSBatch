#!/bin/bash

# Compute the base directories and paths
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd ../../.. && pwd)
SCRIPT_DIR="$PROJECT_DIR/config"
RESOURCE_MONITOR_PATH=$(cd $SCRIPT_DIR; python -c "from config import RESOURCE_MONITOR; print(RESOURCE_MONITOR)")
MASTER_IP=$(cd $SCRIPT_DIR; python -c "from config import MASTER_IP; print(MASTER_IP)")

workflow_path="$PROJECT_DIR/src/workflow_manager"
latency_log_path="$workflow_path/tmp"
resource_log_path=$RESOURCE_MONITOR_PATH

dev01_ip='"192.168.1.18"'
dev03_ip=$MASTER_IP

# Write the values to experiment.config
echo "PROJECT_DIR=$PROJECT_DIR" > experiment.config
echo "SCRIPT_DIR=$SCRIPT_DIR" >> experiment.config
echo "RESOURCE_MONITOR_PATH=$RESOURCE_MONITOR_PATH" >> experiment.config
echo "workflow_path=$workflow_path" >> experiment.config
echo "latency_log_path=$latency_log_path" >> experiment.config
echo "resource_log_path=$resource_log_path" >> experiment.config
echo "dev-01_ip=$dev01_ip" >> experiment.config
echo "dev-03_ip=$dev03_ip" >> experiment.config
