
"""EECS 683 gate-level Verilog netlist parser.

Handles the two instructor benchmark styles:
- s27.v: helper dff module first, positional flip-flop connections.
- design8.v / design48.v: top module, vector bits, named-port dff cells.

Output is circuit connectivity (JSON), NOT the ten security features required
later in Step 1 and NOT a Trojan detector.

This is intentionally a restricted gate-level parser, not all of Verilog.
Unsupported gate-level statements fail with an error rather than disappear.
"""

# All imports below come from Python's standard library.
# No additional Python packages are required for this parser.
from __future__ import annotations

# argparse reads the filename and optional commands entered in the terminal.
import argparse

# json saves the circuit connections for our teammates to use.
import json

# re helps recognize patterns in Verilog statements.
import re

# Path helps locate and open files in our project folders.
from pathlib import Path


# ---------------------------------------------------------
# SECTION 1 - VERILOG SYNTAX PATTERNS
# ---------------------------------------------------------

# These are the basic logic gate types our parser recognizes.
# We identify these gates and their connections, while the
# feature-extraction teammates calculate fan-in/fan-out later.
PRIMITIVE_GATES = {"and", "or", "nand", "nor", "not", "xor", "xnor", "buf"}

# This pattern identifies complete Verilog module blocks.
# It lets us find the module's name, header, and body.
MODULE_RE = re.compile(
    r"\bmodule\s+(?P<name>[A-Za-z_]\w*)\s*(?P<header>.*?)\s*;"
    r"(?P<body>.*?)\bendmodule\b",
    flags=re.DOTALL,
)

# This pattern recognizes individual gate instances.
# Example: nand g0(n45, n4[0], n38)
#
# kind = nand
# name = g0
# args = n45, n4[0], n38
INSTANCE_RE = re.compile(
    r"^(?P<kind>[A-Za-z_]\w*)\s+(?P<name>[A-Za-z_$][\w$]*)\s*"
    r"\((?P<args>.*)\)$",
    flags=re.DOTALL,
)

# Recognizes valid wire names, including individual bus bits.
# Examples: n38, n4[0], n13[1]
NAME_RE = re.compile(r"^[A-Za-z_$][\w$]*(?:\[\d+\])?$")

# Recognizes Verilog constants such as 1'b0 and 1'b1.
# Constants are fixed logic values, not wires.
CONSTANT_RE = re.compile(
    r"^(?:\d+\s*'\s*[sS]?[bBoOdDhH][0-9a-fA-F_xXzZ?]+|\d+|'[01xXzZ])$"
)

# Recognizes declarations for inputs, outputs, and internal signals.
DECL_RE = re.compile(
    r"^(input|output|inout|wire|reg|logic)\s+(.+)$",
    re.DOTALL,
)

# Recognizes named flip-flop connections.
# Examples: .CK(n0), .D(n27), .Q(n13[0])
PORT_RE = re.compile(r"\.([A-Za-z_]\w*)\s*\(\s*([^()]*)\s*\)")


# ---------------------------------------------------------
# SECTION 2 - CLEANING AND INTERPRETING VERILOG SOURCE
# ---------------------------------------------------------

def remove_comments(text: str) -> str:
    """Remove Verilog comments before interpreting circuit statements."""

    # Remove multi-line /* ... */ comments first.
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    # Remove single-line // comments.
    # This prevents commented-out gates from being counted.
    return re.sub(r"//[^\n]*", "", text)


def parse_declaration(statement: str) -> tuple[str, list[str]] | None:
    """Return declaration type and individual net names."""

    # Check whether the statement declares a supported signal type.
    match = DECL_RE.match(statement)

    if not match:
        return None

    # Example: input [1:0] n4, n5
    # kind = input
    # contents = [1:0] n4, n5
    kind, contents = match.groups()

    # Remove modifiers that are not part of the signal names.
    contents = re.sub(
        r"\b(?:signed|unsigned|wire|reg|logic)\b", "", contents
    )

    # Check whether the declaration contains a bus range.
    # Example: [1:0] identifies two bits for each declared signal.
    width = re.search(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", contents)

    bit_indices = None

    if width:
        # Read both ends of the bus range.
        msb, lsb = map(int, width.groups())

        # Create the indexes for all bits in that range.
        bit_indices = range(min(msb, lsb), max(msb, lsb) + 1)

        # Remove the bus range before extracting signal names.
        contents = contents[:width.start()] + contents[width.end():]

    names = []

    # Multiple signals may appear in one declaration.
    for part in contents.split(","):
        name = part.strip()

        # Make sure each signal has a supported name.
        if not re.fullmatch(r"[A-Za-z_$][\w$]*", name):
            raise ValueError(f"Unsupported declaration item: {name!r}")

        if bit_indices is None:
            # Store scalar signals directly.
            names.append(name)

        else:
            # Expand vectors into individual bit-level nets.
            # Example: n4[1:0] becomes n4[0] and n4[1].
            names.extend(f"{name}[{bit}]" for bit in bit_indices)

    return kind, names


def get_module(
    text: str, expected_name: str
) -> tuple[str, str, dict[str, str]]:
    """Select the main circuit module instead of the helper dff module."""

    # Collect the module definitions found in the Verilog file.
    modules = {m.group("name"): m for m in MODULE_RE.finditer(text)}

    if not modules:
        raise ValueError("No Verilog modules found")

    # The s27 benchmark uses a module named s27.
    # The professor's design8/design48 files use module top.
    # Check those names first.
    for name in (expected_name, "top"):
        if name in modules:
            selected = modules[name]
            break

    else:
        # If neither expected name exists, look for one non-dff module.
        # We should not mistake the helper flip-flop definition
        # for the circuit that needs to be analyzed.
        others = [
            m for name, m in modules.items()
            if name.lower() != "dff"
        ]

        if len(others) != 1:
            raise ValueError(
                f"Cannot uniquely select top module: {list(modules)}"
            )

        selected = others[0]

    # Save module headers to help identify positional connections.
    module_headers = {
        name: m.group("header") for name, m in modules.items()
    }

    return selected.group("name"), selected.group("body"), module_headers


def module_port_order(header: str) -> list[str]:
    """Read the declared port order from a helper module."""

    # Example: module dff(CK,Q,D)
    # This tells us the clock, output, and input positions.
    match = re.search(r"\((.*?)\)", header, flags=re.DOTALL)

    if not match:
        return []

    return [part.strip() for part in match.group(1).split(",")]


# ---------------------------------------------------------
# SECTION 3 - IDENTIFYING FLIP-FLOPS
# ---------------------------------------------------------

def parse_flip_flop(
    kind: str, name: str, args: str, module_headers: dict
) -> dict:

    # Flip-flops store values between clock events.
    # We only record their connections here.
    # We are not simulating their behavior.

    # Check for named connections used by instructor circuits.
    # Example: .CK(n0), .D(n27), .Q(n13[0])
    if re.search(r"\.\w+\s*\(", args):
        matched = PORT_RE.findall(args)

        # Ensure there are no leftover malformed connection strings.
        remaining = PORT_RE.sub("", args).replace(",", "").strip()

        if not matched or remaining:
            raise ValueError(
                f"Invalid named ports on flip-flop {name}: {args}"
            )

        # Create a dictionary mapping port names to connected signals.
        connections = {
            key.upper(): value.strip() for key, value in matched
        }

    else:
        # The s27 benchmark uses positional connections instead.
        # Example: dff DFF_0(CK,G5,G10)
        # The helper module identifies these as CK, Q, and D.
        names = module_port_order(module_headers.get(kind, ""))

        values = [arg.strip() for arg in args.split(",")]

        if not names or len(names) != len(values):
            raise ValueError(
                f"Cannot resolve positional ports on flip-flop {name}"
            )

        connections = dict(
            zip((port.upper() for port in names), values)
        )

    # Every supported flip-flop must have:
    # CK = clock
    # Q  = output
    # D  = data input
    for required in ("CK", "Q", "D"):
        if not connections.get(required):
            raise ValueError(
                f"Flip-flop {name} is missing {required}"
            )

    # Store the flip-flop information for later feature extraction.
    return {
        "name": name,
        "type": kind,
        "clock": connections["CK"],
        "input": connections["D"],
        "output": connections["Q"],

        # Keep extra connections such as RN and SN.
        # These are reset/set pins used by the instructor's circuits.
        "ports": connections,
    }


# ---------------------------------------------------------
# SECTION 4 - MAIN NETLIST PARSER
# ---------------------------------------------------------

def parse_netlist(path: str | Path) -> dict:
    """Read a circuit and return its components and connections."""

    # Convert the supplied filename into a full path.
    source_path = Path(path).expanduser().resolve()

    # Read the Verilog source and remove comments.
    text = remove_comments(
        source_path.read_text(encoding="utf-8")
    )

    # Identify which module contains the actual circuit.
    module, body, module_headers = get_module(
        text, source_path.stem
    )

    # Lists for the different types of circuit information.
    inputs: list[str] = []
    outputs: list[str] = []
    wires: list[str] = []
    gates: list[dict] = []
    flip_flops: list[dict] = []

    # Verilog statements end with semicolons.
    # Examine each statement separately.
    for raw in body.split(";"):
        statement = raw.strip()

        if not statement:
            continue

        # Check for input, output, and internal wire declarations.
        declaration = parse_declaration(statement)

        if declaration is not None:
            kind, names = declaration

            if kind == "input":
                inputs.extend(names)

            elif kind == "output":
                outputs.extend(names)

            elif kind == "inout":
                # An inout port can send and receive signals.
                inputs.extend(names)
                outputs.extend(names)

            else:
                wires.extend(names)

            continue

        # Check whether the statement represents a gate or flip-flop.
        instance = INSTANCE_RE.fullmatch(statement)

        # Unsupported syntax produces an error.
        # This prevents the program from silently ignoring logic.
        if instance is None:
            raise ValueError(
                f"Unsupported statement in module {module}: "
                f"{statement[:120]!r}"
            )

        kind, name, args = instance.group(
            "kind", "name", "args"
        )

        kind_lower = kind.lower()

        # Check whether the instance is a supported logic gate.
        if kind_lower in PRIMITIVE_GATES:

            # Primitive gates in our supported files use positional
            # connections rather than named ports.
            if "." in args and re.search(r"\.\w+\s*\(", args):
                raise ValueError(
                    f"Named ports not supported for primitive gate {name}"
                )

            # Split the connections into individual signals.
            signals = [
                value.strip() for value in args.split(",")
            ]

            # Each primitive gate requires an output and input.
            if len(signals) < 2 or not all(signals):
                raise ValueError(
                    f"Invalid connections on {name}: {args}"
                )

            # Make sure the connections are valid signal names
            # or supported Verilog constants.
            for signal in signals:
                if not (
                    NAME_RE.fullmatch(signal)
                    or CONSTANT_RE.fullmatch(signal)
                ):
                    raise ValueError(
                        f"Unsupported signal {signal!r} on gate {name}"
                    )

            # A gate output must be a signal, not a constant.
            if CONSTANT_RE.fullmatch(signals[0]):
                raise ValueError(
                    f"Primitive gate {name} output cannot be a constant"
                )

            # For these primitive gates:
            # First connection = output
            # Remaining connections = inputs
            #
            # Example:
            # nand g0(n45, n4[0], n38)
            # Output: n45
            # Inputs: n4[0], n38
            gates.append({
                "name": name,
                "type": kind_lower,
                "output": signals[0],
                "inputs": signals[1:],
            })

        elif kind_lower == "dff":
            # Flip-flops require different connection parsing.
            # Send the instance to our flip-flop helper function.
            flip_flops.append(
                parse_flip_flop(kind, name, args, module_headers)
            )

        else:
            # Reject cells or constructs our parser does not support.
            raise ValueError(
                f"Unsupported instance type {kind!r} for {name}"
            )

    # ---------------------------------------------------------
    # SECTION 5 - COLLECT UNIQUE NET NAMES
    # ---------------------------------------------------------

    # Begin with declared inputs, outputs, and wires.
    connected = inputs + outputs + wires

    # Add every gate's output and input connections.
    for gate in gates:
        connected.extend([
            gate["output"],
            *gate["inputs"],
        ])

    # Add the flip-flop connections.
    for flip_flop in flip_flops:
        connected.extend(flip_flop["ports"].values())

    # A signal may connect to multiple gates.
    # A set removes duplicates so each net appears once.
    # Constants such as 1'b0 are not included as nets.
    # Sorting keeps the JSON output consistent.
    net_names = sorted({
        s for s in connected if NAME_RE.fullmatch(s)
    })

    # Return all extracted information in one dictionary.
    # Our teammates can use the gate and net connections
    # to calculate features in their own Python code.
    #
    # The summary values are basic component counts,
    # not security features or Trojan classifications.
    return {
        "source_file": source_path.name,
        "module": module,

        # Remove duplicate names while preserving their order.
        "primary_inputs": list(dict.fromkeys(inputs)),
        "primary_outputs": list(dict.fromkeys(outputs)),
        "wires": list(dict.fromkeys(wires)),

        "gates": gates,
        "flip_flops": flip_flops,
        "nets": net_names,

        "summary": {
            "primary_input_bits": len(set(inputs)),
            "primary_output_bits": len(set(outputs)),
            "logic_gates": len(gates),
            "flip_flops": len(flip_flops),
            "nets": len(net_names),
        },
    }


# ---------------------------------------------------------
# SECTION 6 - LOCATE THE CIRCUIT FILE
# ---------------------------------------------------------

def resolve_input(name: str) -> Path:
    """Find the Verilog file selected by the user."""

    candidate = Path(name).expanduser()

    # First check whether the user provided a valid file path.
    if candidate.is_file():
        return candidate

    # Find the main project directory from this script's location.
    root = Path(__file__).resolve().parent.parent

    # Search our baseline and Trojan circuit folders.
    for folder in ("netlists/baseline", "netlists/trojan"):
        attempt = root / folder / name

        if attempt.is_file():
            return attempt

    # Explain the problem if the file cannot be found.
    raise FileNotFoundError(
        f"Cannot find {name!r}; use a full/relative path"
    )


# ---------------------------------------------------------
# SECTION 7 - RUN THE PARSER AND EXPORT JSON
# ---------------------------------------------------------

def main() -> None:
    """Process terminal arguments and run the netlist parser."""

    # Set up the arguments that can be entered in the terminal.
    parser = argparse.ArgumentParser(
        description="Parse a gate-level Verilog netlist"
    )

    # Required argument: which circuit file to analyze.
    parser.add_argument(
        "verilog_file",
        help="Path to .v (or filename inside netlists/)"
    )

    # Optional argument: where to save the JSON connectivity data.
    parser.add_argument(
        "--json",
        metavar="PATH",
        help="Save parsed connectivity to JSON"
    )

    # Read the arguments supplied by the user.
    args = parser.parse_args()

    # Locate the circuit and extract its information.
    result = parse_netlist(
        resolve_input(args.verilog_file)
    )

    # Print a summary to help verify the parser's results.
    print(
        f"Circuit: {result['source_file']} "
        f"(module {result['module']})"
    )
    print(
        f"Primary input bits: "
        f"{result['summary']['primary_input_bits']}"
    )
    print(
        f"Primary output bits: "
        f"{result['summary']['primary_output_bits']}"
    )
    print(f"Logic gates: {result['summary']['logic_gates']}")
    print(f"Flip-flops: {result['summary']['flip_flops']}")
    print(f"Unique nets: {result['summary']['nets']}")

    # Only save JSON if the user requested it with --json.
    if args.json:
        out = Path(args.json)

        # Create the output folder if it does not exist.
        out.parent.mkdir(parents=True, exist_ok=True)

        # Write the dictionary into a readable JSON file.
        out.write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )

        print(f"Saved parsed connectivity: {out}")


# Run main() when this Python file is executed directly.
# Tests and teammates can import parse_netlist() without
# automatically executing the command-line program.
if __name__ == "__main__":
    main()
