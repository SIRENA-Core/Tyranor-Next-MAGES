// Print every defined data item (address, size, type) in the given ranges.
// args: <outFile> <start1Hex> <end1Hex> [<start2Hex> <end2Hex> ...]
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;

import java.io.PrintWriter;

public class DumpData extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] a = getScriptArgs();
        try (PrintWriter out = new PrintWriter(a[0], "UTF-8")) {
            for (int i = 1; i + 1 < a.length; i += 2) {
                Address s = toAddr(Long.parseLong(a[i], 16));
                Address e = toAddr(Long.parseLong(a[i + 1], 16));
                DataIterator it = currentProgram.getListing().getDefinedData(s, true);
                while (it.hasNext()) {
                    Data d = it.next();
                    if (d.getAddress().compareTo(e) >= 0) break;
                    out.println(d.getAddress() + " " + d.getLength() + " " + d.getDataType().getName());
                }
            }
        }
    }
}
