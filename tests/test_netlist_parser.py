
"""
EECS 683 - Hardware Trojan Detection
Netlist Parser Testing

Purpose:
    Test our netlist parser to make sure it correctly reads
    gate-level Verilog circuits and extracts the expected
    circuit information.

Why this matters:
    Before other team members calculate security features or
    perform Trojan detection, we need to verify that our parser
    correctly identifies gates, flip-flops, inputs, outputs,
    wires, and their connections.

Circuits tested:
    - s27.v: Small baseline circuit used to test the parser.
    - design8.v: Smaller instructor-provided Trojan circuit.
    - design48.v: Larger instructor-provided Trojan circuit.

Scope:
    These tests verify the netlist parser's functionality.
    They do NOT calculate security features, detect Trojans,
    or simulate circuit behavior.
"""

# ---------------------------------------------------------
# STEP 1 - IMPORT LIBRARIES AND LOCATE PROJECT FILES
# ---------------------------------------------------------

# unittest is Python's built-in testing framework.
# It lets us create tests and check whether the parser
# produces the expected circuit information.
import unittest

# Path helps us locate circuit files in our project folders.
from pathlib import Path

# sys allows us to add our src folder to Python's import path.
import sys


# Find the main EECS683-Trojan-Detection project folder.
#
# __file__ refers to this test file:
#     tests/test_netlist_parser.py
#
# parents[1] moves up to the main project directory.
ROOT = Path(__file__).resolve().parents[1]

# Add our src folder to Python's import search path.
# This allows us to import netlist_parser.py even though
# it is stored in a different folder from this test file.
sys.path.insert(0, str(ROOT / "src"))

# Import the parse_netlist function from our parser.
# This is the function that reads Verilog files and
# returns information about the circuit.
#
# noqa: E402 tells certain code-checking tools to ignore
# the fact that this import appears after other statements.
from netlist_parser import parse_netlist  # noqa: E402


# ---------------------------------------------------------
# STEP 2 - CREATE OUR NETLIST PARSER TEST CLASS
# ---------------------------------------------------------

# This class groups all tests for our netlist parser.
#
# unittest.TestCase provides methods such as:
#     assertEqual() - checks whether two values match.
#     assertIn() - checks whether a value is present.
#     assertNotIn() - checks whether a value is absent.
#     assertTrue() - checks whether a condition is true.
#
# Each method beginning with "test_" is automatically
# recognized and executed by Python's unittest framework.
class TestNetlistParser(unittest.TestCase):

    # -----------------------------------------------------
    # TEST 1 - CHECK THE BASELINE S27 CIRCUIT
    # -----------------------------------------------------

    def test_s27(self):

        # Run our parser on the baseline s27.v circuit.
        # The returned dictionary contains circuit information
        # such as the module name, gates, and flip-flops.
        data = parse_netlist(ROOT / "netlists/baseline/s27.v")

        # Verify that the parser selected the correct module.
        self.assertEqual(data["module"], "s27")

        # Verify that the parser found 10 logic gates.
        # This includes the circuit's basic logic gates
        # and its NOT (inverter) gates.
        self.assertEqual(data["summary"]["logic_gates"], 10)

        # Verify that the parser identified 3 flip-flops.
        self.assertEqual(data["summary"]["flip_flops"], 3)

        # Verify the expected primary input count.
        # The five inputs include the clock signal.
        self.assertEqual(data["summary"]["primary_input_bits"], 5)

        # Verify that the circuit has one primary output.
        self.assertEqual(data["summary"]["primary_output_bits"], 1)

        # Find the flip-flop named DFF_0 in the parsed results.
        #
        # The next() function returns the first matching
        # flip-flop from the list of extracted flip-flops.
        ff = next(
            cell for cell in data["flip_flops"]
            if cell["name"] == "DFF_0"
        )

        # Check that the parser identified the correct
        # connections for this flip-flop:
        #
        # Clock: CK
        # Output (Q): G5
        # Input (D): G10
        #
        # This confirms that positional flip-flop connections
        # are interpreted in the correct order.
        self.assertEqual(
            (ff["clock"], ff["output"], ff["input"]),
            ("CK", "G5", "G10")
        )

    # -----------------------------------------------------
    # TEST 2 - CHECK THE INSTRUCTOR'S DESIGN8 CIRCUIT
    # -----------------------------------------------------

    def test_design8(self):

        # Run our parser on design8.v, one of the
        # Trojan-inserted circuits provided by the instructor.
        data = parse_netlist(ROOT / "netlists/trojan/design8.v")

        # The main module in design8.v is named "top".
        # This verifies that the parser does not incorrectly
        # assume the module name must match the filename.
        self.assertEqual(data["module"], "top")

        # Verify the expected number of logic gates.
        self.assertEqual(data["summary"]["logic_gates"], 80)

        # Verify the expected number of flip-flops.
        self.assertEqual(data["summary"]["flip_flops"], 3)

        # Verify the total number of primary input bits.
        self.assertEqual(data["summary"]["primary_input_bits"], 8)

        # Verify the total number of primary output bits.
        self.assertEqual(data["summary"]["primary_output_bits"], 28)

        # Check that our parser correctly recognizes
        # individual wires inside a multi-bit signal.
        #
        # For example, n4 is declared as a two-bit signal.
        # The parser should recognize n4[0] and n4[1]
        # as separate bit-level nets.
        self.assertIn("n4[0]", data["nets"])
        self.assertIn("n4[1]", data["nets"])

        # Verify that a Verilog constant is not incorrectly
        # recorded as a wire.
        #
        # 1'b0 represents a constant binary zero.
        # It is not a net with its own signal name.
        self.assertNotIn("1'b0", data["nets"])

        # Find the flip-flop instance named g9.
        ff = next(
            cell for cell in data["flip_flops"]
            if cell["name"] == "g9"
        )

        # Verify that named flip-flop ports were parsed correctly.
        #
        # RN = Reset connection
        # SN = Set connection
        # CK = Clock connection
        # D  = Data input
        # Q  = Stored output
        #
        # This checks the named-port format used by
        # the instructor's design8 circuit.
        self.assertEqual(
            ff["ports"],
            {
                "RN": "1'b1",
                "SN": "1'b1",
                "CK": "n0",
                "D": "n27",
                "Q": "n13[0]"
            }
        )

    # -----------------------------------------------------
    # TEST 3 - CHECK THE INSTRUCTOR'S DESIGN48 CIRCUIT
    # -----------------------------------------------------

    def test_design48(self):

        # Run our parser on design48.v.
        # This is a larger instructor-provided Trojan circuit,
        # so it helps verify that the parser also handles
        # circuits with more components and connections.
        data = parse_netlist(ROOT / "netlists/trojan/design48.v")

        # Verify that the correct top-level module was found.
        self.assertEqual(data["module"], "top")

        # Verify the expected number of logic gates.
        self.assertEqual(data["summary"]["logic_gates"], 208)

        # Verify the expected number of flip-flops.
        self.assertEqual(data["summary"]["flip_flops"], 33)

        # Verify that the parser identifies all 70 input bits.
        self.assertEqual(data["summary"]["primary_input_bits"], 70)

        # Verify that the parser identifies all 13 output bits.
        self.assertEqual(data["summary"]["primary_output_bits"], 13)

        # Check that the bus bit n10[12] is recognized
        # as a primary output.
        #
        # This helps verify that the parser correctly
        # expands vector declarations in larger circuits.
        self.assertIn("n10[12]", data["primary_outputs"])

    # -----------------------------------------------------
    # TEST 4 - VERIFY INSTRUCTOR-LISTED TROJAN GATE IDS
    # -----------------------------------------------------

    def test_instructor_trojan_gate_ids_exist(self):

        # The instructor provided separate text files
        # identifying Trojan-related gate instance names.
        #
        # This test checks that our parser recognizes
        # those instance names in the corresponding circuits.
        #
        # IMPORTANT:
        # We are NOT implementing Trojan detection here.
        # We are only verifying that the parser did not
        # miss the gate instances listed by the instructor.

        # Run the same verification for both instructor designs.
        for stem in ("design8", "design48"):

            # subTest lets Python report which design failed
            # if one of the two checks does not pass.
            with self.subTest(stem=stem):

                # Parse the corresponding Verilog circuit.
                data = parse_netlist(
                    ROOT / "netlists/trojan" / f"{stem}.v"
                )

                # Collect all extracted gate and flip-flop names.
                #
                # A set helps us quickly check whether
                # an expected instance name was recognized.
                ids = {
                    x["name"]
                    for x in data["gates"] + data["flip_flops"]
                }

                # Open the instructor's Trojan information file.
                # Example: Trojan_info_design8.txt
                raw = (
                    ROOT / "netlists/trojan" /
                    f"Trojan_info_{stem}.txt"
                ).read_text()

                # Extract the gate names between the markers:
                #
                # TROJAN_GATES
                #     listed gate names
                # END_TROJAN_GATES
                #
                # split() separates the names into a list.
                labels = (
                    raw.split("TROJAN_GATES", 1)[1]
                    .split("END_TROJAN_GATES", 1)[0]
                    .split()
                )

                # Make sure the instructor's gate list
                # was not empty.
                self.assertTrue(labels)

                # Verify that every instructor-listed
                # Trojan gate instance exists in our
                # parser's extracted instance names.
                #
                # This does not classify any nets or
                # determine whether a Trojan is present.
                self.assertTrue(set(labels).issubset(ids))


# ---------------------------------------------------------
# STEP 3 - RUN THE TESTS
# ---------------------------------------------------------

# If this file is executed directly, run the tests.
#
# We can also run all tests from the main project folder:
#
# python3 -m unittest discover -s tests -v
#
# Successful tests will report "ok" for each test
# and finish with "OK".
#
# These checks validate selected parsing behavior.
# Passing them does not prove support for every
# possible Verilog circuit.
if __name__ == "__main__":
    unittest.main()
