#!/bin/bash
# Sweep six_port_flex.py from 60 GHz to 300 GHz in 20 GHz steps
# Use --no-fill for faster preview runs

for ghz in $(seq 60 20 300); do
    freq=$((ghz * 1000000000))
    echo "=== Running at ${ghz} GHz ==="
    python six_port_flex.py --frequency "${freq}" "$@"
done
