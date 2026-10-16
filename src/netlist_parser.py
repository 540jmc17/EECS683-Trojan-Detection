
"""
EECS 683 - Hardware Trojan Detection
Netlist Parser

Purpose:
Read a Verilog circuit file and identify primary inputs,
primary outputs, logic gates, their connections, and flip-flops.

This is an initial parser for the simple gate-level Verilog
format used by the s27 benchmark. It will be generalized later.
"""

from pathlib import Path


# ----------------------------------------------------
# STEP 1: Locate the project and circuit file
# ----------------------------------------------------

# Find the main project directory (one level above src)
project_root = Path(__file__).resolve().parent.parent

# Locate the example circuit we want to analyze
netlist_file = project_root / "netlists" / "baseline" / "s27.v"


# ----------------------------------------------------
# STEP 2: Read the circuit file
# ----------------------------------------------------

# Read the entire Verilog file into a string
circuit = netlist_file.read_text(encoding="utf-8")

print("Reading circuit:", netlist_file.name)


# ----------------------------------------------------
# STEP 3: Identify primary inputs and outputs
# ----------------------------------------------------

primary_inputs = []
primary_outputs = []

# The main module for s27.v is named s27.
# We skip the separate helper module named dff.
module_name = netlist_file.stem
current_module = None

for line in circuit.splitlines():

    # Remove line comments and whitespace
    line = line.split("//", 1)[0].strip()

    # Determine which module the current line belongs to
    if line.startswith("module "):
        current_module = line.split()[1].split("(")[0]
        continue

    if line.startswith("endmodule"):
        current_module = None
        continue

    # Only gather the top-level circuit's ports
    if current_module != module_name:
        continue

    if line.startswith("input "):
        signals = line.removeprefix("input ").rstrip(";")
        primary_inputs.extend(
            signal.strip() for signal in signals.split(",")
        )

    elif line.startswith("output "):
        signals = line.removeprefix("output ").rstrip(";")
        primary_outputs.extend(
            signal.strip() for signal in signals.split(",")
        )

print("\nPrimary Inputs:", primary_inputs)
print("Primary Outputs:", primary_outputs)


# ----------------------------------------------------
# STEP 4: Prepare to store the logic gates
# ----------------------------------------------------

# Each gate will be stored as a dictionary in this list
# so feature-extraction code can use it later.
gates = []

gate_types = (
    "and ",
    "or ",
    "nand ",
    "nor ",
    "not ",
    "xor ",
    "xnor ",
    "buf "
)


# ----------------------------------------------------
# STEP 5: Extract the logic gates and connections
# ----------------------------------------------------

for line in circuit.splitlines():

    line = line.split("//", 1)[0].strip()

    if line.startswith(gate_types):

        # Example: and AND2_0(G8,G14,G6);
        gate_info, connections = line.split("(", 1)
        gate_type, gate_name = gate_info.split()

        # Separate output and input wires
        connections = connections.split(")", 1)[0]
        wires = [wire.strip() for wire in connections.split(",")]

        # For these Verilog primitive gates, output comes first
        output_wire = wires[0]
        input_wires = wires[1:]

        gate = {
            "name": gate_name,
            "type": gate_type,
            "output": output_wire,
            "inputs": input_wires
        }

        gates.append(gate)


# ----------------------------------------------------
# STEP 6: Display extracted gate information
# ----------------------------------------------------

print("\nCircuit:", netlist_file.name)
print("Total Logic Gates:", len(gates))
print("\nGate Information:")

for gate in gates:
    print("\n-------------------------")
    print("Gate Name:", gate["name"])
    print("Gate Type:", gate["type"])
    print("Output Wire:", gate["output"])
    print("Input Wires:", gate["inputs"])


# ----------------------------------------------------
# STEP 7: Identify flip-flops in the main circuit
# ----------------------------------------------------

# In s27.v, each instance has the format:
# dff DFF_0(CK,G5,G10);
# The helper module declares its ports as (CK, Q, D).
flip_flops = []
current_module = None

for line in circuit.splitlines():

    line = line.split("//", 1)[0].strip()

    if line.startswith("module "):
        current_module = line.split()[1].split("(")[0]
        continue

    if line.startswith("endmodule"):
        current_module = None
        continue

    if current_module != module_name:
        continue

    if line.startswith("dff "):

        # Separate the instance name from its connections
        flip_info, connections = line.split("(", 1)
        flip_type, flip_name = flip_info.split()

        # Extract CK, Q, and D in the order used by this module
        connections = connections.split(")", 1)[0]
        wires = [wire.strip() for wire in connections.split(",")]

        flip_flop = {
            "name": flip_name,
            "type": flip_type,
            "clock": wires[0],
            "output": wires[1],   # Q
            "input": wires[2]     # D
        }

        flip_flops.append(flip_flop)

print("\nTotal Flip-Flops:", len(flip_flops))

for flip_flop in flip_flops:
    print("\n-------------------------")
    print("Flip-Flop Name:", flip_flop["name"])
    print("Clock:", flip_flop["clock"])
    print("Output (Q):", flip_flop["output"])
    print("Input (D):", flip_flop["input"])


# ----------------------------------------------------
# STEP 8: Display the final circuit summary
# ----------------------------------------------------

print("\n-------------------------")
print("Circuit Analysis Summary")
print("-------------------------")
print("Total Primary Inputs:", len(primary_inputs))
print("Total Primary Outputs:", len(primary_outputs))
print("Total Logic Gates:", len(gates))
print("Total Flip-Flops:", len(flip_flops))
print("\nFinished analyzing circuit!")
