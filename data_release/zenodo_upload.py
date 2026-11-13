# -*- coding: utf-8 -*-
r"""Upload the AGB_NE data release to Zenodo as a DRAFT deposition (publishing is a separate, explicit step).

Token: create a personal access token at https://zenodo.org/account/settings/applications/ (scopes
deposit:write and deposit:actions; the sandbox needs its own token from sandbox.zenodo.org) and put it in
the environment variable ZENODO_TOKEN before running. The script reads it from the environment only and
never prints or stores it.

  set ZENODO_TOKEN=...                       (cmd)        $env:ZENODO_TOKEN = "..."     (PowerShell)
  python -X utf8 zenodo_upload.py --dir C:\AGB_NE_release --dry-run              # no network: list files, md5, metadata
  python -X utf8 zenodo_upload.py --dir C:\AGB_NE_release --sandbox              # rehearsal on sandbox.zenodo.org
  python -X utf8 zenodo_upload.py --dir C:\AGB_NE_release                        # real draft on zenodo.org
  python -X utf8 zenodo_upload.py --dir C:\AGB_NE_release --deposition 1234567   # resume / update an existing draft
  python -X utf8 zenodo_upload.py --dir C:\AGB_NE_release --deposition 1234567 --parallel 5   # 5 files at a time
  python -X utf8 zenodo_upload.py --dir C:\AGB_NE_release --deposition 1234567 --publish --yes-publish

What it does: creates (or reuses) a deposition, writes the metadata of zenodo_metadata.json with the
description from zenodo_description.html (DOI pre-reserved), uploads every *.tif, *.json, README.md,
sha256sums.txt and md5sums.txt of --dir to the deposition bucket (files already there with the same md5
are skipped, so an interrupted run can be repeated), compares Zenodo's md5 with the local one, and prints
the draft URL and the reserved DOI. Nothing is published unless --publish --yes-publish are both given.

Network errors: each file is tried up to --attempts times (default 8). The bucket API cannot resume
a file, so a failed file starts over after a pause (30 s, doubling up to 10 min) and after Zenodo has answered a
test request again (checked every 60 s for up to --max-wait-hours, default 6). Files that still fail are listed at
the end (exit code 2) and are picked up by the next run with --deposition ID; completed files are skipped by md5.

Parallel upload: --parallel N sends up to N files at the same time, each over its own connection and
with the same retry logic. Zenodo (CERN) gives a single connection only about 0.3-0.7 MB/s from here, and the
connections add up, so N=5 is roughly five times faster. The files are listed with numbers [1]..[N] first; one
status line then shows the GB sent per file and in total (a file that starts over after an error drops back to 0).
"""
import argparse, glob, hashlib, json, os, queue, shutil, sys, threading, time
import requests

CHUNK = 1 << 22  # 4 MB

# ---- console output: one progress line that is overwritten in place; messages go on lines of their own -------------
_out_lock = threading.Lock()
_line_len = 0  # length of the progress line currently on screen (0 = none)

def status(line):
    """Show `line` as the progress line, replacing the previous one (no newline)."""
    global _line_len
    with _out_lock:
        width = max(shutil.get_terminal_size((120, 20)).columns - 1, 40)
        line = line[:width]
        print("\r" + line.ljust(min(_line_len, width)), end="", flush=True)
        _line_len = len(line)

def say(msg=""):
    """Print a message on its own line; a progress line on screen is kept and closed with a newline first."""
    global _line_len
    with _out_lock:
        if _line_len:
            print()
            _line_len = 0
        print(msg, flush=True)

def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()

class Progress:
    """File wrapper for requests: known length, md5 on the fly; with own_line it shows its own progress line."""
    def __init__(self, path, own_line=True):
        self.f = open(path, "rb"); self.size = os.path.getsize(path); self.done = 0
        self.h = hashlib.md5(); self.t0 = time.time(); self.last = 0.0; self.name = os.path.basename(path)
        self.own_line = own_line
    def __len__(self):
        return self.size
    def read(self, n=-1):
        b = self.f.read(CHUNK if n is None or n < 0 else n)
        if b:
            self.h.update(b); self.done += len(b)
            now = time.time()
            if self.own_line and (now - self.last > 5 or self.done == self.size):
                rate = self.done / max(now - self.t0, 1e-6) / 1e6
                eta = (self.size - self.done) / max(rate * 1e6, 1.0) / 60
                status(f"  {self.name}: {self.done/1e9:6.2f} / {self.size/1e9:.2f} GB  {rate:5.1f} MB/s  "
                       f"{(now - self.t0)/60:4.0f} min, about {eta:4.0f} min left")
                self.last = now
        return b
    def close(self):
        self.f.close()

class Slot:
    """One file of this run: its number in the status line, its state and the current Progress object."""
    def __init__(self, idx, name, size, shared):
        self.idx = idx; self.name = name; self.size = size
        self.shared = shared                       # parallel mode: no own progress line, messages tagged [idx]
        self.tag = f"[{idx}] " if shared else ""
        self.p = None; self.state = "queued"; self.info = ""   # state: queued, up, wait, done, FAIL
    def sent(self):
        """Bytes sent in the current attempt, or the whole file once Zenodo has confirmed it."""
        if self.state == "done":
            return self.size
        return self.p.done if self.state == "up" and self.p else 0
    def cell(self):
        return f"[{self.idx}] " + (f"{self.p.done/1e9:.2f}" if self.state == "up" and self.p else self.state)

def board(slots, total, t0):
    """Status line of the parallel mode: total GB, average rate since the start, rough time left, then the GB per
    unfinished file (finished files are announced on their own line). Kept short for narrow terminal panes."""
    sent = sum(s.sent() for s in slots); el = time.time() - t0
    rate = sent / max(el, 1e-6) / 1e6
    left = f"~{(total - sent) / max(rate * 1e6, 1.0) / 60:.0f} min left" if sent else "starting"
    cells = " ".join(s.cell() for s in slots if s.state != "done") or "all done"
    return f"  {sent/1e9:.2f}/{total/1e9:.2f} GB {rate:.1f} MB/s {left} | {cells}"

def release_files(d):
    names = []
    for pat in ("*.tif", "*.json", "README.md", "sha256sums.txt", "md5sums.txt"):
        names += [os.path.basename(p) for p in glob.glob(os.path.join(d, pat))]
    return sorted(n for n in set(names) if not n.startswith("build_log"))

def load_metadata(script_dir):
    meta = json.load(open(os.path.join(script_dir, "zenodo_metadata.json"), encoding="utf-8"))
    meta = {k: v for k, v in meta.items() if not k.startswith("_")}
    if isinstance(meta.get("description"), str) and meta["description"].startswith("@"):
        meta["description"] = open(os.path.join(script_dir, meta["description"][1:]), encoding="utf-8").read()
    for k in ("upload_type", "title", "creators", "description", "access_right", "license"):
        if not meta.get(k):
            raise SystemExit(f"metadata key '{k}' is missing or empty in zenodo_metadata.json")
    return meta

NETWORK_ERRORS = (requests.RequestException, OSError)  # SSLError, ConnectionError, Timeout, ChunkedEncodingError, socket errors

class Retry(Exception):
    """A transient failure of one upload attempt (HTTP 5xx, 409, 423 or 429 from Zenodo or its proxy)."""

RETRY_ERRORS = NETWORK_ERRORS + (Retry,)

class Zenodo:
    def __init__(self, base, token, attempts=8, max_wait=6 * 3600):
        self.base = base; self.attempts = attempts; self.max_wait = max_wait; self.token = token
        self.s = self.session(); self.gave_up = False
    def session(self):
        """A requests session carrying the token; each upload thread uses one of its own."""
        s = requests.Session(); s.headers["Authorization"] = f"Bearer {self.token}"
        return s
    def call(self, method, url, retries=3, **kw):
        timeout = kw.pop("timeout", (30, 900))
        for attempt in range(1, retries + 1):
            try:
                r = self.s.request(method, url, timeout=timeout, **kw); break
            except NETWORK_ERRORS as e:
                if attempt == retries:
                    raise SystemExit(f"{method} {url}: {type(e).__name__}: {str(e)[:300]}")
                say(f"  {method} .../{url.split('/api/')[-1]}: {type(e).__name__}; retrying in 30 s ({attempt}/{retries})")
                time.sleep(30)
        if r.status_code >= 400:
            raise SystemExit(f"{method} {url} -> HTTP {r.status_code}: {r.text[:1500]}")
        return r.json() if r.content and r.headers.get("Content-Type", "").startswith("application/json") else {}
    def deposition(self, dep_id=None):
        if dep_id:
            return self.call("GET", f"{self.base}/api/deposit/depositions/{dep_id}")
        return self.call("POST", f"{self.base}/api/deposit/depositions", json={})
    def set_metadata(self, dep_id, meta):
        return self.call("PUT", f"{self.base}/api/deposit/depositions/{dep_id}", json={"metadata": meta})
    def files(self, dep_id):
        return self.call("GET", f"{self.base}/api/deposit/depositions/{dep_id}/files")
    def delete_file(self, file_rec):
        self.call("DELETE", file_rec["links"]["self"], timeout=60)
    def wait_online(self, dep_id, s=None, tag=""):
        """Return once the deposition can be read again; check every 60 s, give up after self.max_wait seconds."""
        s = s or self.s
        t0 = time.time(); checks = 0
        while True:
            try:
                r = s.get(f"{self.base}/api/deposit/depositions/{dep_id}", timeout=(30, 60))
                if r.status_code < 500:
                    if r.status_code >= 400:
                        self.gave_up = True
                        raise SystemExit(f"deposition {dep_id} cannot be read any more: HTTP {r.status_code}: {r.text[:500]}")
                    if checks:
                        say(f"  {tag}{time.strftime('%H:%M')}  {self.base} answers again")
                    return
                reason = f"HTTP {r.status_code}"
            except NETWORK_ERRORS as e:
                reason = type(e).__name__
            checks += 1; waited = time.time() - t0
            if waited > self.max_wait:
                self.gave_up = True
                raise SystemExit(f"{self.base} unreachable for {waited/3600:.1f} h ({reason}); giving up - "
                                 f"re-run later with --deposition {dep_id}")
            say(f"  {tag}{time.strftime('%H:%M')}  {self.base} not reachable ({reason}); next check in 60 s "
                f"(waiting since {waited/60:.0f} min)")
            time.sleep(60)
    def upload(self, bucket, path, dep_id, slot, s=None):
        """PUT one file into the bucket. The bucket API cannot resume, so after a network error the file starts over;
        between attempts the script pauses (30 s doubling up to 10 min) and then waits until Zenodo answers again.
        `slot` keeps the state for the status line, `s` is the session of the calling thread.
        Returns (file record, local md5), or (None, reason) when every attempt failed or Zenodo rejected the file."""
        s = s or self.s; tag = slot.tag
        reason = "no attempt made"
        for attempt in range(1, self.attempts + 1):
            p = Progress(path, own_line=not slot.shared)
            slot.p = p; slot.state = "up"
            try:
                r = s.put(f"{bucket}/{os.path.basename(path)}", data=p, timeout=(30, 900))
                if r.status_code >= 500 or r.status_code in (409, 423, 429):   # server trouble, lock, rate limit
                    raise Retry(f"HTTP {r.status_code}: {r.text[:300]}")
                if r.status_code >= 400:
                    return None, f"HTTP {r.status_code}: {r.text[:800]}"
                return r.json(), p.h.hexdigest()
            except RETRY_ERRORS as e:
                reason = f"{type(e).__name__}: {str(e)[:300]}"
                say(f"  {tag}{time.strftime('%H:%M')}  attempt {attempt}/{self.attempts} failed after {p.done/1e9:.2f} GB: {reason}")
            finally:
                p.close()
            if attempt < self.attempts:
                slot.state = "wait"
                pause = min(30 * 2 ** (attempt - 1), 600)
                say(f"  {tag}waiting {pause} s, then checking the connection before the next attempt")
                time.sleep(pause)
                self.wait_online(dep_id, s, tag)
        return None, f"{self.attempts} attempts failed; last error {reason}"
    def publish(self, dep_id):
        return self.call("POST", f"{self.base}/api/deposit/depositions/{dep_id}/actions/publish", retries=1)

def run_slot(z, bucket, dep_id, d, slot, s=None):
    """Upload one file and record the outcome in its slot (sequential mode calls this directly, threads via worker)."""
    if z.gave_up:
        slot.state = "FAIL"; slot.info = "skipped, Zenodo was unreachable for too long"
        say(f"  {slot.tag}{slot.name}: NOT uploaded ({slot.info})"); return
    try:
        rec, info = z.upload(bucket, os.path.join(d, slot.name), dep_id, slot, s)
    except SystemExit as e:          # wait_online gave up, or the deposition cannot be read any more
        rec, info = None, str(e)
    except Exception as e:           # anything unforeseen: report this file, keep the other uploads going
        rec, info = None, f"{type(e).__name__}: {str(e)[:300]}"
    if rec is None:
        slot.state = "FAIL"; slot.info = info
        say(f"  {slot.tag}{slot.name}: NOT uploaded ({info})"); return
    remote = rec.get("checksum", "").replace("md5:", "")
    if remote and remote != info:
        slot.state = "FAIL"; slot.info = f"md5 mismatch (local {info}, Zenodo {remote})"
        say(f"  {slot.tag}{slot.name}: md5 MISMATCH - local {info}, Zenodo {remote}; the next run replaces it"); return
    slot.state = "done"; slot.info = info
    say(f"  {slot.tag}{slot.name}: uploaded, md5 {info} confirmed by Zenodo")

def worker(z, bucket, dep_id, d, q):
    """Thread of the parallel mode: takes files from the queue and uploads them over a session of its own."""
    s = z.session()
    while True:
        try:
            slot = q.get_nowait()
        except queue.Empty:
            return
        run_slot(z, bucket, dep_id, d, slot, s)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True); ap.add_argument("--deposition", type=int)
    ap.add_argument("--sandbox", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--publish", action="store_true"); ap.add_argument("--yes-publish", action="store_true")
    ap.add_argument("--skip-md5", action="store_true", help="dry run: do not compute local md5 sums")
    ap.add_argument("--attempts", type=int, default=8,
                    help="upload attempts per file (default 8; pauses 30 s, 60 s, ... up to 10 min between them)")
    ap.add_argument("--max-wait-hours", type=float, default=6,
                    help="how long to wait for the connection to come back after a failed attempt (default 6 h)")
    ap.add_argument("--parallel", type=int, default=1,
                    help="files uploaded at the same time, one connection each (default 1; Zenodo gives one connection "
                         "only about 0.3-0.7 MB/s from here, several connections add up)")
    args = ap.parse_args()
    if args.parallel < 1:
        raise SystemExit("--parallel must be 1 or more")
    here = os.path.dirname(os.path.abspath(__file__))
    meta = load_metadata(here)
    names = release_files(args.dir)
    total = sum(os.path.getsize(os.path.join(args.dir, n)) for n in names)
    say(f"deposition metadata: '{meta['title']}' | {meta['upload_type']} | {meta['access_right']} | {meta['license']} | "
        f"{len(meta['creators'])} creator(s) | description {len(meta['description']):,} chars")
    say(f"files in {args.dir}: {len(names)}, {total/1e9:.2f} GB (Zenodo limit 50 GB / 100 files per record)")
    if args.dry_run:
        lines = []
        for n in names:
            p = os.path.join(args.dir, n); sz = os.path.getsize(p)
            d = "" if args.skip_md5 else md5_of(p)
            say(f"  {sz/1e9:6.3f} GB  {d}  {n}"); lines.append(f"{d}  {n}")
        if not args.skip_md5:
            with open(os.path.join(args.dir, "md5sums.txt"), "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(l for l in lines if not l.endswith("md5sums.txt")) + "\n")
            say("md5sums.txt written (Zenodo shows md5 per file; compare after the upload)")
        say("dry run only - nothing sent"); return
    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        raise SystemExit("set the environment variable ZENODO_TOKEN first (personal access token, scopes deposit:write + deposit:actions)")
    base = "https://sandbox.zenodo.org" if args.sandbox else "https://zenodo.org"
    z = Zenodo(base, token, args.attempts, args.max_wait_hours * 3600)
    dep = z.deposition(args.deposition)
    dep_id = dep["id"]; bucket = dep["links"]["bucket"]
    say(f"deposition {dep_id} on {base} (state {dep.get('state')}, submitted={dep.get('submitted')})")
    if dep.get("submitted"):
        say("  this deposition is already published; files cannot be changed - create a new version on the website instead")
    dep = z.set_metadata(dep_id, meta)
    doi = (dep.get("metadata", {}).get("prereserve_doi") or {}).get("doi") or dep.get("doi")
    say(f"metadata written; reserved DOI: {doi}")
    existing = {f["filename"]: f for f in z.files(dep_id)}
    html = dep.get("links", {}).get("html") or f"{base}/deposit/{dep_id}"
    todo = []
    for n in names:
        p = os.path.join(args.dir, n)
        if n in existing:
            local = md5_of(p)
            if existing[n].get("checksum", "").replace("md5:", "") == local:
                say(f"  {n}: already on Zenodo with the same md5, skipped"); continue
            say(f"  {n}: on Zenodo with a different md5, replacing"); z.delete_file(existing[n])
        todo.append(n)
    shared = args.parallel > 1 and len(todo) > 1
    slots = [Slot(i, n, os.path.getsize(os.path.join(args.dir, n)), shared) for i, n in enumerate(todo, 1)]
    if not shared:
        for slot in slots:
            run_slot(z, bucket, dep_id, args.dir, slot)
    else:
        threads = min(args.parallel, len(slots)); todo_bytes = sum(s.size for s in slots)
        say(f"\nuploading {len(slots)} files ({todo_bytes/1e9:.2f} GB), {threads} at a time over separate connections:")
        for s in slots:
            say(f"  [{s.idx}] {s.name}  {s.size/1e9:.2f} GB")
        q = queue.Queue()
        for s in slots:
            q.put(s)
        pool = [threading.Thread(target=worker, args=(z, bucket, dep_id, args.dir, q), daemon=True, name=f"upload-{i+1}")
                for i in range(threads)]
        t0 = time.time()
        for t in pool:
            t.start()
        while True:
            status(board(slots, todo_bytes, t0))
            if not any(t.is_alive() for t in pool):
                break
            time.sleep(10)
    failed = [s.name for s in slots if s.state != "done"]
    if failed:
        say(f"\n{len(failed)} file(s) not uploaded: {', '.join(failed)}")
        say(f"re-run with --deposition {dep_id} to retry them (files already on Zenodo with the right md5 are skipped)")
        say(f"draft: {html}\nreserved DOI: {doi}\n(not published)")
        sys.exit(2)
    say(f"\nDRAFT ready: {html}\nreserved DOI: {doi}\n(not published)")
    if args.publish:
        if not args.yes_publish:
            raise SystemExit("--publish needs --yes-publish as well; publishing cannot be undone")
        pub = z.publish(dep_id)
        say(f"PUBLISHED: {pub.get('links', {}).get('record_html')}  DOI {pub.get('doi')}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\ninterrupted (Ctrl+C) - re-run with --deposition ID to go on; files already on Zenodo are skipped")
        sys.stdout.flush(); os._exit(130)
