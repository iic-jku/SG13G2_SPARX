#!/bin/bash
# SPDX-FileCopyrightText: 2025-2026 The SPARX Team
# SPDX-License-Identifier: Apache-2.0

# Sweep six_port_gen.py across a configurable frequency range.
# Usage: ./run_sweep.sh [start_ghz] [stop_ghz] [step_ghz] [six_port_gen args...]
start_ghz=${1:-60}
stop_ghz=${2:-300}
step_ghz=${3:-20}

shift $(( $# >= 3 ? 3 : $# ))

for ghz in $(seq "$start_ghz" "$step_ghz" "$stop_ghz"); do
    freq=$((ghz * 1000000000))
    echo "=== Running at ${ghz} GHz ==="
    python six_port_gen.py --frequency "${freq}" "$@"
done
