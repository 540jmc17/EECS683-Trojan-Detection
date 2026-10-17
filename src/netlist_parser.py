
"""
EECS 683 - Hardware Trojan Detection
Netlist Parser

Purpose:
    Read a gate-level Verilog circuit file and identify:
    - primary inputs (signals entering the circuit)
    - primary outputs (signals leaving the circuit)
    - logic gates (AND, OR, NAND, NOR, etc.) and their connections
    - D flip-flops (components that store values between clock cycles)

Why this matters:
    Other team members can use the extracted circuit information
    to calculate structural/security features for Trojan detection.

Scope:
    This is an initial parser for the simple ISCAS89 benchmark format.
    It is NOT a complete parser for every possible Verilog design.
"""

# Path lets Python locate files without manually typing the full Mac path.
from pathlib import Path

# sys gives us access to filenames typed after the Python command.
import sys


# ----------------------------------------------------
# STEP 1: Locate the project and circuit file
# ----------------------------------------------------

# __file__ is the location of THIS Python file (inside the src folder).
# resolve() obtains its full path, and parent.parent moves up two levels:
#     EECS683-Trojan-Detection/src/netlist_parser.py
#                         -> EECS683-Trojan-Detection/
project_root = Path(__file__).resolve().parent.parent

# sys.argv contains the command used to start the program.
# For example: python3 src/netlist_parser.py s382.v
#   sys.argv[0] is the Python script name.
#   sys.argv[1] is "s382.v", if a filename was supplied.
# If nothing was supplied, we analyze s27.v by default.
filename = sys.argv[1] if len(sys.argv) > 1 else "s27.v"

# Construct the path to the chosen circuit in the baseline folder.
# Example: netlists/baseline/s382.v
netlist_file = project_root / "netlists" / "baseline" / filename


# ----------------------------------------------------
# STEP 2: Read the circuit file
# ----------------------------------------------------

# Read the entire Verilog file as one string.
# UTF-8 specifies how text characters are decoded.
circuit = netlist_file.read_text(encoding="utf-8")

# Print the file name so we know which circuit is being analyzed.
print("Reading circuit:", netlist_file.name)


# ----------------------------------------------------
# STEP 3: Identify primary inputs and outputs
# ----------------------------------------------------

# We use separate lists because inputs and outputs serve different purposes.
# Example inputs: CK, G0, G1; example output: G17.
primary_inputs = []
primary_outputs = []

# A benchmark's top-level module normally has the same name as its file.
# For example, s382.v contains a main module called s382.
# This helps us ignore the helper module called "dff".
module_name = netlist_file.stem

# Remember which Verilog module we are currently examining.
# None means we are not inside a module.
current_module = None

# Some declarations span several lines:
#     input CK, G0,
#           G1, G2;
# We hold the partial text until we reach its final semicolon.
pending_declaration = ""

# Split the whole circuit into lines and inspect them one at a time.
for line in circuit.splitlines():

    # Discard // comments, then remove extra whitespace.
    # The "1" means split only at the first occurrence of //.
    line = line.split("//", 1)[0].strip()

    # Ignore blank lines and lines that contained only comments.
    if not line:
        continue

    # When a new module begins, save its name.
    # Example: module s27(CK,G0,...);
    if line.startswith("module "):
        current_module = line.split()[1].split("(")[0]
        pending_declaration = ""
        continue

    # When the current module ends, stop treating lines as part of it.
    if line.startswith("endmodule"):
        current_module = None
        pending_declaration = ""
        continue

    # Skip everything outside the main benchmark circuit.
    # In particular, do not count ports from the helper dff module.
    if current_module != module_name:
        continue

    # If a line starts with input/output, begin a new declaration.
    if line.startswith(("input ", "output ")):
        pending_declaration = line

    # Otherwise, if we were in the middle of a declaration,
    # append this line to the unfinished declaration.
    elif pending_declaration:
        pending_declaration += " " + line

    # Lines such as "wire ..." or gate instances are not port declarations.
    else:
        continue

    # A semicolon marks the end of a Verilog declaration.
    # If it is missing, keep reading subsequent lines.
    if ";" not in pending_declaration:
        continue

    # Keep the declaration text before its semicolon.
    # strip() removes whitespace around that complete statement.
    declaration = pending_declaration.split(";", 1)[0].strip()

    # Split once at whitespace:
    #     "input CK,G0,G1" -> declaration_type="input"
    #                         signals="CK,G0,G1"
    declaration_type, signals = declaration.split(None, 1)

    # Break comma-separated signal names into an actual Python list.
    # strip() removes spaces; the if condition excludes empty names.
    signal_names = [
        signal.strip()
        for signal in signals.split(",")
        if signal.strip()
    ]

    # Place the signals in the appropriate list.
    # extend() adds each name separately, rather than adding a nested list.
    if declaration_type == "input":
        primary_inputs.extend(signal_names)

    elif declaration_type == "output":
        primary_outputs.extend(signal_names)

    # We have finished this declaration, so clear the temporary text.
    pending_declaration = ""

# Show the primary port names that were found.
print("\nPrimary Inputs:", primary_inputs)
print("Primary Outputs:", primary_outputs)


# ----------------------------------------------------
# STEP 4: Prepare to store the logic gates
# ----------------------------------------------------

# Every logic gate will be represented by a Python dictionary.
# All gate dictionaries are collected in this list for later analysis.
gates = []

# These are the gate types we recognize in the benchmark format.
# The trailing space distinguishes a gate keyword from a longer word.
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
# STEP 5: Extract gates, including multi-line connections
# ----------------------------------------------------

# Start outside any module, then watch for the top-level module.
current_module = None

# Accumulate a Verilog statement until its ending semicolon appears.
# This prevents losing a gate connection that is written on another line.
pending_statement = ""

for line in circuit.splitlines():

    # Remove // comments and whitespace, just as in Step 3.
    line = line.split("//", 1)[0].strip()

    if not line:
        continue

    # Identify a module's beginning and clear previously collected text.
    if line.startswith("module "):
        current_module = line.split()[1].split("(")[0]
        pending_statement = ""
        continue

    # Identify a module's end and discard any leftover partial statement.
    if line.startswith("endmodule"):
        current_module = None
        pending_statement = ""
        continue

    # Ignore the dff helper module and other non-top-level content.
    if current_module != module_name:
        continue

    # Add the latest line to whatever statement we are building.
    pending_statement += " " + line

    # A line can contain more than one semicolon-separated statement.
    # Process each complete statement; leave any unfinished part for later.
    while ";" in pending_statement:

        statement, pending_statement = pending_statement.split(";", 1)
        statement = statement.strip()

        # Skip declarations or statements that are not supported logic gates.
        if not statement.startswith(gate_types):
            continue

        # Example complete statement:
        #     and AND2_0(G8,G14,G6)
        # The text before '(' identifies the gate type and instance name.
        gate_info, connections = statement.split("(", 1)
        gate_type, gate_name = gate_info.split()

        # Take the signal text inside parentheses and split at commas.
        # Result for the example: ["G8", "G14", "G6"]
        connections = connections.split(")", 1)[0]
        wires = [wire.strip() for wire in connections.split(",")]

        # At least one output and one input are required for these gates.
        # Missing wire names are an error, rather than valid connections.
        if len(wires) < 2 or any(not wire for wire in wires):
            raise ValueError(
                f"Incomplete wire connections for gate {gate_name}"
            )

        # In these gate-level primitive instances, the FIRST connected
        # signal is the output, and all remaining signals are inputs.
        # A dictionary makes the information easier to access later.
        gate = {
            "name": gate_name,
            "type": gate_type,
            "output": wires[0],
            "inputs": wires[1:]
        }

        # Save this gate before moving to the next statement.
        gates.append(gate)


# ----------------------------------------------------
# STEP 6: Display extracted gate information
# ----------------------------------------------------

# Show which circuit was parsed and how many gates we extracted.
print("\nCircuit:", netlist_file.name)
print("Total Logic Gates:", len(gates))
print("\nGate Information:")

# Read each stored dictionary and print its fields.
for gate in gates:
    print("\n-------------------------")
    print("Gate Name:", gate["name"])
    print("Gate Type:", gate["type"])
    print("Output Wire:", gate["output"])
    print("Input Wires:", gate["inputs"])


# ----------------------------------------------------
# STEP 7: Identify flip-flops in the main circuit
# ----------------------------------------------------

# These benchmarks use flip-flop instances such as:
#     dff DFF_0(CK,G5,G10);
# The dff helper module declares ports in this exact order:
#     (CK, Q, D) = (clock, stored output, data input).
# NOTE: This code assumes that specific dff format.
flip_flops = []
current_module = None

for line in circuit.splitlines():

    # Discard line comments and whitespace.
    line = line.split("//", 1)[0].strip()

    # Track which module is active, just as in earlier steps.
    if line.startswith("module "):
        current_module = line.split()[1].split("(")[0]
        continue

    if line.startswith("endmodule"):
        current_module = None
        continue

    # Only look for instances in the main circuit.
    if current_module != module_name:
        continue

    # This benchmark represents flip-flops as lines starting with "dff ".
    if line.startswith("dff "):

        # Separate the instance identification from the port connections.
        # "dff DFF_0(CK,G5,G10);" -> flip_name="DFF_0".
        flip_info, connections = line.split("(", 1)
        flip_type, flip_name = flip_info.split()

        # Remove text after ')' and split the three connected signals.
        connections = connections.split(")", 1)[0]
        wires = [wire.strip() for wire in connections.split(",")]

        # Save the CK, Q, and D connections using readable field names.
        flip_flop = {
            "name": flip_name,
            "type": flip_type,
            "clock": wires[0],
            "output": wires[1],  # Q: value stored by the flip-flop
            "input": wires[2]    # D: value captured on the clock edge
        }

        # Add the flip-flop dictionary to the list.
        flip_flops.append(flip_flop)

# Print the number of flip-flops and details of each one.
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

# len() counts the number of entries in each list.
# These totals provide a quick check against known benchmark statistics.
print("\n-------------------------")
print("Circuit Analysis Summary")
print("-------------------------")
print("Total Primary Inputs:", len(primary_inputs))
print("Total Primary Outputs:", len(primary_outputs))
print("Total Logic Gates:", len(gates))
print("Total Flip-Flops:", len(flip_flops))
print("\nFinished analyzing circuit!")
