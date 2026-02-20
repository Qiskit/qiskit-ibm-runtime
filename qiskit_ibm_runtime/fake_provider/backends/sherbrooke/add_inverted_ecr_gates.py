#!/usr/bin/env python3
"""
Script to add inverted qubit ordering for all ECR gates in props_sherbrooke.json.

For each ECR gate entry like:
  {"qubits": [41, 40], "gate": "ecr", ..., "name": "ecr41_40"}

This script adds a duplicate with inverted qubit ordering:
  {"qubits": [40, 41], "gate": "ecr", ..., "name": "ecr40_41"}
"""

import json
import copy
from pathlib import Path


def add_inverted_ecr_gates(json_path: str) -> None:
    """Read the props JSON and add inverted ECR gate entries."""
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Collect existing ECR gates
    ecr_gates = [g for g in data['gates'] if g['gate'] == 'ecr']
    print(f"Found {len(ecr_gates)} existing ECR gates")
    
    # Build a set of existing qubit pairs to avoid duplicates
    existing_pairs = set()
    for gate in ecr_gates:
        qubits = tuple(gate['qubits'])
        existing_pairs.add(qubits)
    
    # Create inverted gates
    new_gates = []
    for gate in ecr_gates:
        q0, q1 = gate['qubits']
        inverted_qubits = (q1, q0)
        
        # Only add if inverted pair doesn't already exist
        if inverted_qubits not in existing_pairs:
            new_gate = copy.deepcopy(gate)
            new_gate['qubits'] = [q1, q0]
            new_gate['name'] = f"ecr{q1}_{q0}"
            new_gates.append(new_gate)
            existing_pairs.add(inverted_qubits)
    
    print(f"Adding {len(new_gates)} inverted ECR gates")
    
    # Add the new gates to the gates list
    data['gates'].extend(new_gates)
    
    # Write back to file
    with open(json_path, 'w') as f:
        json.dump(data, f)
    
    print(f"Total ECR gates now: {len([g for g in data['gates'] if g['gate'] == 'ecr'])}")
    print(f"Successfully updated {json_path}")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    json_path = script_dir / "props_sherbrooke.json"
    add_inverted_ecr_gates(str(json_path))
