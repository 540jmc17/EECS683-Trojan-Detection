"""calculate fan-in, fan-out, and logic depth for each net in a parsed circuit."""

# keep type annotations separate from runtime evaluation
from __future__ import annotations

import argparse # read verilog filename from command line
import csv # format feature rows for detector input
import sys # send csv to standard output
from graphlib import CycleError, TopologicalSorter # process inputs before outputs and detect loops

# reuse Jake's parser to locate and read a netlist
from netlist_parser import parse_netlist, resolve_input


def extract_structural_features(circuit: dict) -> dict[str, dict[str, int | None]]:
    """return a feature dictionary keyed by net name.

    fan-in counts distinct named inputs to a driving combinational gate.
    fan-out counts distinct cells that use a net, including flip-flops.
    logic depth counts gates along a longest combinational path to a net.
    """
    # keep one feature row for every net returned by parser, including unused nets
    nets = circuit["nets"]
    # store input names for each gate output so repeated pins count once
    fan_in = {net: set() for net in nets}
    # start at zero until a gate or flip-flop uses a net
    fan_out = dict.fromkeys(nets, 0)
    # primary inputs start a new combinational path at depth zero
    sources = set(circuit["primary_inputs"])

    for flip_flop in circuit["flip_flops"]:
        # start depth over at each flip-flop output so feedback through storage is allowed
        sources.add(flip_flop["output"])
        # collect signals on input pins, including clock and any reset or set pins
        consumed_nets = {
            signal for pin, signal in flip_flop["ports"].items() if pin != "Q"
        }
        # count each flip-flop once per net and skip literal constants
        for net in consumed_nets.intersection(fan_out):
            fan_out[net] += 1

    # track which nets have a combinational driver
    driven = set()
    for gate in circuit["gates"]:
        output = gate["output"]
        # reject a second driver because this calculation assumes one driver per net
        if output in driven or output in sources:
            raise ValueError(f"Multiple drivers for net {output!r}")
        driven.add(output)

        # keep only named nets and count a repeated input once for this gate
        inputs = set(gate["inputs"]).intersection(fan_out)
        # save inputs for both fan-in count and depth calculation
        fan_in[output] = inputs
        # each input net has one more cell using it
        for net in inputs:
            fan_out[net] += 1

    # save calculated depths so downstream gates can reuse them
    depths = {}
    try:
        # visit every input before any gate that uses it, regardless of file order
        for net in TopologicalSorter(fan_in).static_order():
            if net in sources:
                # primary inputs and flip-flop outputs have no preceding gate on this path
                depths[net] = 0
            elif net in driven:
                # read depth for each named input to this net's driving gate
                input_depths = [depths[parent] for parent in fan_in[net]]
                # add one gate to a deepest input path, or keep depth unknown if any input is undriven
                # constant-only gates use zero as input depth, giving their output depth one
                depths[net] = (
                    None if None in input_depths else 1 + max(input_depths, default=0)
                )
            else:
                # a net without a source or driving gate has unknown depth
                depths[net] = None
    except CycleError as error:
        # show which nets form a loop so teammates can trace it in verilog
        cycle = " -> ".join(error.args[1])
        raise ValueError(f"Combinational cycle prevents depth calculation: {cycle}") from error

    # combine all three features under each net name
    return {
        net: {
            "fan_in": len(fan_in[net]),
            "fan_out": fan_out[net],
            "logic_depth": depths[net],
        }
        for net in nets
    }


def main() -> None:
    # set up command-line help and require one input file
    parser = argparse.ArgumentParser(description="Write per-net structural features as CSV")
    parser.add_argument("verilog_file", help="Path to a gate-level Verilog file")
    args = parser.parse_args()

    try:
        # locate verilog file, parse its connections, then calculate feature values
        features = extract_structural_features(parse_netlist(resolve_input(args.verilog_file)))
    except (OSError, ValueError) as error:
        # print a readable error and return a nonzero exit status
        parser.exit(1, f"{error}\n")

    # write csv to standard output so it can be viewed or redirected into a file
    writer = csv.DictWriter(sys.stdout, ["net_name", "fan_in", "fan_out", "logic_depth"])
    writer.writeheader()
    for net, values in features.items():
        # include net name as row identifier, with unknown depths written as blank
        writer.writerow({"net_name": net, **values})

if __name__ == "__main__":
    main()
