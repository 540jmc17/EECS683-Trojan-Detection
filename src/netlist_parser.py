
"""
EECS 683 - Hardware Trojan Detection
Netlist Parser

Purpose:
Read a Verilog circuit file and identify its logic gates,
gate names, input wires, and output wires.

The extracted information will later be used for
security feature calculations and Trojan detection.
"""

from pathlib import Path


# ----------------------------------------------------
# STEP 1: Locate the project and circuit file
# ----------------------------------------------------

# Find the main project directory
project_root = Path(__file__).resolve().parent.parent

# Locate the circuit file we want to analyze
netlist_file = project_root / "netlists" / "baseline" / "s27.v"


# ----------------------------------------------------
# STEP 2: Read the circuit file
# ----------------------------------------------------

# Read the entire Verilog circuit file
circuit = netlist_file.read_text()

# Display the name of the circuit being analyzed
print("Reading circuit:", netlist_file.name)


# ----------------------------------------------------
# STEP 3: Prepare to store the logic gates
# ----------------------------------------------------

# Create an empty list to store information about
# each logic gate found in the circuit
gates = []

# Define the different gate types we want to identify
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
# STEP 4: Examine each line of the circuit
# ----------------------------------------------------

# Go through the circuit file one line at a time
for line in circuit.splitlines():

    # Remove extra spaces from the beginning and end
    line = line.strip()

    # Check if this line contains a supported logic gate
    if line.startswith(gate_types):

        # Separate gate information from wire connections
        # Example: and AND2_0(G8,G14,G6);
        gate_info, connections = line.split("(", 1)

        # Extract the gate type and gate name
        # Example: gate_type = and
        #          gate_name = AND2_0
        gate_type, gate_name = gate_info.split()

        # Remove the closing parenthesis and anything after it
        connections = connections.split(")", 1)[0]

        # Separate the wires using commas
        # Example: G8,G14,G6 becomes [G8, G14, G6]
        wires = [
            wire.strip()
            for wire in connections.split(",")
        ]

        # For these Verilog logic primitives,
        # the first wire represents the gate output
        output_wire = wires[0]

        # The remaining wires represent gate inputs
        input_wires = wires[1:]

        # Store all information about the gate
        # using a Python dictionary
        gate = {
            "name": gate_name,
            "type": gate_type,
            "output": output_wire,
            "inputs": input_wires
        }

        # Add the gate dictionary to our list
        gates.append(gate)


# ----------------------------------------------------
# STEP 5: Display the extracted gate information
# ----------------------------------------------------

print("\nCircuit:", netlist_file.name)

# Display how many logic gates were identified
print("Total Logic Gates:", len(gates))

print("\nGate Information:")

# Go through all of the gates we collected
for gate in gates:

    # Display the individual gate information
    print("\n-------------------------")
    print("Gate Name:", gate["name"])
    print("Gate Type:", gate["type"])
    print("Output Wire:", gate["output"])
    print("Input Wires:", gate["inputs"])

print("\n-------------------------")
print("Finished analyzing circuit!")
