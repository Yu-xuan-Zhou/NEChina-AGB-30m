# -*- coding: utf-8 -*-
r"""Make the file table of the data release from the per-file JSON reports.

Usage: python -X utf8 -I make_file_table.py C:\AGB_NE_release [README_release.md]
Prints a Markdown table (file, size, valid pixels, pixel arithmetic mean / min / max, check) and, when a
README path is given, replaces the block between <!-- FILE TABLE --> and <!-- /FILE TABLE -->.
These are encoding-QC statistics, not the paper's area-weighted regional means.
"""
import glob, json, os, sys

def main():
    out_dir = sys.argv[1]
    rows = []
    for p in sorted(glob.glob(os.path.join(out_dir, "*.json"))):
        r = json.load(open(p, encoding="utf-8"))
        st, ck = r["source_stats"], r["output_check"]
        rows.append((os.path.basename(r["output"]), r["output_bytes"] / 1e9, st["n_valid"], st["mean"], st["min"], st["max"],
                     ck["ok"], r["sha256"][:12], r["job"], st["n_zero"], st["n_nan"]))
    lines = ["| File | Size (GB) | Valid pixels | Pixel arithmetic mean (Mg ha-1) | Min | Max | Check | sha256 (first 12) |",
             "|---|---|---|---|---|---|---|---|"]
    for f, gb, n, mean, mn, mx, ok, sha, job, nz, nnan in rows:
        lines.append(f"| `{f}` | {gb:.2f} | {n:,} | {mean:.2f} | {mn:.1f} | {mx:.1f} | {'passed' if ok else 'FAILED'} | {sha} |")
    table = "\n".join(lines)
    print(table)
    if len(sys.argv) > 2:
        path = sys.argv[2]
        t = open(path, encoding="utf-8").read()
        a, b = "<!-- FILE TABLE -->", "<!-- /FILE TABLE -->"
        i, j = t.index(a) + len(a), t.index(b)
        t = t[:i] + "\n" + table + "\n" + t[j:]
        open(path, "w", encoding="utf-8", newline="\n").write(t)
        print("table written into", path)

if __name__ == "__main__":
    main()
