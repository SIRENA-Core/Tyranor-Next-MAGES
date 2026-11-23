// Decompile every function whose entry lies in [start, end) and write the C to an output file.
// args: <startHex> <endHex> <outFile>
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

import java.io.PrintWriter;

public class DumpRange extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] a = getScriptArgs();
        Address start = toAddr(Long.parseLong(a[0], 16));
        Address end = toAddr(Long.parseLong(a[1], 16));
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        try (PrintWriter out = new PrintWriter(a[2], "UTF-8")) {
            FunctionIterator it = currentProgram.getFunctionManager().getFunctions(start, true);
            while (it.hasNext()) {
                Function f = it.next();
                if (f.getEntryPoint().compareTo(end) >= 0) break;
                DecompileResults r = ifc.decompileFunction(f, 120, monitor);
                out.println("// ===== " + f.getName() + " @ " + f.getEntryPoint());
                if (r != null && r.decompileCompleted()) out.println(r.getDecompiledFunction().getC());
                else out.println("// decompile failed");
            }
        }
    }
}
