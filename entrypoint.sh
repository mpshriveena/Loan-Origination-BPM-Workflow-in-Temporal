#!/bin/bash

# Start Kafka server
/etc/confluent/docker/run &

# Wait for Kafka to be ready
sleep 10

# Create topic
kafka-topics --create --topic loan_disbursement --bootstrap-server localhost:9092 --replication-factor 3 --partitions 1 || true

# Keep the container running
wait
