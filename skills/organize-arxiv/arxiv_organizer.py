#!/usr/bin/env python3
"""Arxiv Paper Organizer — renames, tags, and files arxiv PDFs.

Usage:
    python arxiv_organizer.py --scan   FOLDER [--recurse] [--library LIB]
    python arxiv_organizer.py --execute FOLDER [--recurse] [--library LIB]
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time

# ── Constants ────────────────────────────────────────────────────────────────

CAT_SLUGS = {
    "cs.AI": "#ai", "cs.CE": "#comp-eng", "cs.CL": "#nlp", "cs.CR": "#security",
    "cs.CV": "#vision", "cs.CY": "#tech-society", "cs.DB": "#databases",
    "cs.DC": "#distributed", "cs.ET": "#emerging-tech", "cs.HC": "#hci",
    "cs.LG": "#ml", "cs.MA": "#multi-agent", "cs.MM": "#multimedia",
    "cs.NE": "#neuro-evo", "cs.NI": "#networking", "cs.OH": "#cs-other",
    "cs.PL": "#prog-lang", "cs.SC": "#symbolic", "cs.SD": "#audio",
    "cs.SE": "#software-eng", "eess.AS": "#speech", "math.CO": "#combinatorics",
    "math.NT": "#number-theory", "q-fin.TR": "#quant-trading",
}
AI_ADJACENT = {
    "cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.MA", "cs.NE", "cs.MM",
    "cs.SE", "cs.HC", "cs.CE", "cs.CY", "eess.AS", "cs.SD",
}

FOLDER_MAP = {
    "cs.CR": "_CS, Tech", "cs.DB": "_CS, Tech", "cs.DC": "_CS, Tech",
    "cs.ET": "_CS, Tech", "cs.NI": "_CS, Tech", "cs.OH": "_CS, Tech",
    "cs.PL": "_CS, Tech", "cs.SC": "_CS, Tech",
    "math.CO": "_Math, Physics, Philosophy", "math.NT": "_Math, Physics, Philosophy",
    "q-fin.TR": "_Business, Econ, FInance",
}

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".arxiv_cache.json")

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def sanitize_filename(s):
    import html
    s = html.unescape(s)  # &#39; → '
    s = re.sub(r'\$[^$]*\$', '', s)  # remove LaTeX $...$
    s = re.sub(r'[<>:"/\\|?*\[\]{}]', '', s)
    s = re.sub(r"[']", '', s)  # remove apostrophes for safety
    s = re.sub(r'\s+', ' ', s)
    return s.strip()
def get_folder_for_cats(cats):
    for c in cats:
        if c in AI_ADJACENT:
            return "__AI__"
    if cats:
        return FOLDER_MAP.get(cats[0], "__AI__")
    return "__AI__"

def cats_to_slugs(cats):
    return ' '.join(CAT_SLUGS.get(c, '#' + c.replace('.', '-')) for c in cats)

def extract_from_pdf(filepath):
    """Extract arxiv ID, version, title, categories, date from a PDF."""
    import fitz
    doc = fitz.open(filepath)
    meta = doc.metadata
    page0 = doc[0].get_text() if doc.page_count > 0 else ''
    doc.close()

    # arxiv ID + version from filename
    fname = os.path.basename(filepath)
    arxiv_id, version = '', ''
    m = re.search(r'(\d{4}\.\d{4,5})(v\d+)?', fname)
    if m:
        yymm = m.group(1)[:4]
        if int(yymm[2:]) <= 12:  # valid month
            arxiv_id = m.group(1)
            version = m.group(2) or ''

    # fallback: from PDF text
    if not arxiv_id:
        m2 = re.search(r'arXiv:(\d{4}\.\d{4,5})(v\d+)?', page0)
        if m2:
            arxiv_id = m2.group(1)
            version = version or (m2.group(2) or '')
    if not arxiv_id:
        return None  # not an arxiv paper

    # version from text if not in filename
    if not version:
        m3 = re.search(r'arXiv:\d{4}\.\d{4,5}(v\d+)', page0)
        if m3:
            version = m3.group(1)

    # categories from PDF stamp
    cats = []
    stamp = re.search(r'arXiv:\S+\s*\[([^\]]+)\]', page0)
    if stamp:
        cats = [stamp.group(1)]

    # date from PDF stamp
    date_str = ''
    dm = re.search(r'arXiv:\S+\s*\[[^\]]+\]\s*(\d{1,2}\s+\w+\s+\d{4})', page0)
    if dm:
        date_str = dm.group(1)

    # title from metadata or first lines
    title = meta.get('title', '').strip()
    bad_titles = ('1', 'Preprint', 'Preprint. Under review.', 'Microsoft Word - Raja.doc')
    bad_prefixes = ('JOURNAL OF', 'Published', 'arXiv:', 'Proceedings', '2026', '2025', '22')
    if not title or title in bad_titles or any(title.startswith(p) for p in bad_prefixes):
        lines = [l.strip() for l in page0.split('\n') if l.strip() and len(l.strip()) > 10]
        for line in lines:
            if not re.match(r'^(arXiv:|Published|JOURNAL|Proceedings|Preprint|20\d\d-)', line):
                title = line[:200]
                break
    return {
        'arxiv_id': arxiv_id,
        'version': version,
        'title': title,
        'cats_from_pdf': cats,
        'date_from_pdf': date_str,
        'meta_title': meta.get('title', ''),
        'meta_keywords': meta.get('keywords', ''),
        'meta_author': meta.get('author', ''),
    }

def fetch_arxiv_page(arxiv_id, cache):
    """Fetch categories, title, date from arxiv abstract page. Uses cache."""
    if arxiv_id in cache:
        return cache[arxiv_id]

    url = f"https://arxiv.org/abs/{arxiv_id}"
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={'User-Agent': 'ArxivOrganizer/1.0'})
        resp = urllib.request.urlopen(req, timeout=30)
        html = resp.read().decode('utf-8')

        # categories
        subj = re.search(r'Subjects:.*?</span>\s*(.*?)\s*</div>', html, re.DOTALL)
        cats = []
        if subj:
            codes = re.findall(r'([a-z-]+\.[A-Z]{2})', subj.group(1))
            seen = set()
            for c in codes:
                if c not in seen:
                    cats.append(c)
                    seen.add(c)
        # title
        title_match = re.search(r'<h1 class="title mathjax">\s*<span class="descriptor">Title:</span>\s*(.*?)\s*</h1>', html, re.DOTALL)
        title = title_match.group(1).strip() if title_match else ''

        # submitted date
        date_match = re.search(r'Submitted.*?(\d{1,2}\s+\w+\s+\d{4})', html)
        submitted = date_match.group(1) if date_match else ''
        if not submitted:
            date_match2 = re.search(r'\[Submitted on (\d+ \w+ \d{4})', html)
            submitted = date_match2.group(1) if date_match2 else ''

        result = {'cats': cats, 'title': title, 'submitted': submitted}
        cache[arxiv_id] = result
        return result
    except Exception as e:
        print(f"  WARNING: Could not fetch {url}: {e}", file=sys.stderr)
        return {'cats': [], 'title': '', 'submitted': ''}

def parse_date(date_str):
    """Parse various date formats to datetime."""
    for fmt in ('%d %b %Y', '%d %B %Y', '%Y-%m-%d'):
        try:
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

def set_file_dates(filepath, dt):
    """Set file modification and access time."""
    ts = dt.timestamp()
    os.utime(filepath, (ts, ts))
    if sys.platform == 'win32':
        ps = f'(Get-Item "{filepath}").CreationTime = [datetime]::Parse("{dt.isoformat()}")'
        subprocess.run(['powershell', '-Command', ps], capture_output=True)
def update_pdf_metadata(filepath, title, keywords, subject, date_str):
    """Write metadata fields into PDF."""
    import fitz
    doc = fitz.open(filepath)

    meta = doc.metadata
    meta['title'] = title
    meta['keywords'] = keywords
    meta['subject'] = subject
    if date_str:
        dt = parse_date(date_str)
        if dt:
            pdf_date = dt.strftime("D:%Y%m%d000000Z")
            meta['creationDate'] = pdf_date
            meta['modDate'] = pdf_date

    doc.set_metadata(meta)
    tmp = filepath + '.tmp'
    doc.save(tmp, garbage=4, deflate=True)
    doc.close()
    os.replace(tmp, filepath)

def append_log(folder, line):
    logpath = os.path.join(folder, 'move.log')
    with open(logpath, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
# ── Main Logic ───────────────────────────────────────────────────────────────

def scan_folder(folder, recurse=False):
    """Find all arxiv PDFs and build a rename/move plan."""
    pdfs = []
    if recurse:
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.lower().endswith('.pdf'):
                    pdfs.append(os.path.join(root, f))
    else:
        for f in os.listdir(folder):
            if f.lower().endswith('.pdf'):
                pdfs.append(os.path.join(folder, f))

    cache = load_cache()
    plan = []
    fetch_count = 0

    for filepath in sorted(pdfs):
        info = extract_from_pdf(filepath)
        if info is None:
            continue  # not arxiv, skip

        aid = info['arxiv_id']
        ver = info['version']

        date = info['date_from_pdf']
        title = info['title']
        web = fetch_arxiv_page(aid, cache)
        fetch_count += 1
        if fetch_count % 5 == 0:
            save_cache(cache)
            time.sleep(1)

        cats = web['cats'] if web['cats'] else info['cats_from_pdf']
        if web['title'] and (not title or len(web['title']) > len(title)):
            title = web['title']
        if web['submitted'] and not date:
            date = web['submitted']

        # build new filename
        slug_str = cats_to_slugs(cats) if cats else ''
        safe_title = sanitize_filename(title)
        ver_str = ' ' + ver if ver else ''
        new_name = f"{aid} {slug_str} {safe_title}{ver_str}.pdf".replace('  ', ' ')

        # destination folder
        dest_subfolder = get_folder_for_cats(cats) if cats else '__AI__'

        plan.append({
            'src_path': filepath,
            'src_folder': os.path.dirname(filepath),
            'orig_name': os.path.basename(filepath),
            'new_name': new_name,
            'dest_subfolder': dest_subfolder,
            'arxiv_id': aid,
            'version': ver,
            'title': title,
            'cats': cats,
            'slugs': slug_str,
            'submitted': date,
            'action': 'RENAME' if dest_subfolder == os.path.basename(os.path.dirname(filepath)) or not cats else 'MOVE',
        })

    save_cache(cache)
    return plan
def print_plan(plan, library=None):
    """Print the plan in human-readable format."""
    for p in plan:
        src = p['src_path']
        if library and p['action'] == 'MOVE':
            dest_dir = os.path.join(library, p['dest_subfolder'])
        else:
            dest_dir = p['src_folder']
        dest = os.path.join(dest_dir, p['new_name'])

        changed = src != dest
        action = 'MOVE+RENAME' if p['action'] == 'MOVE' and changed else ('RENAME' if changed else 'META ONLY')

        print(f"\n{action} → {p['dest_subfolder']}")
        print(f"  FROM: {p['orig_name']}")
        if changed:
            print(f"    TO: {p['new_name']}")
        print(f"  META: title={p['title'][:80]}")
        print(f"        keywords={p['slugs']}")
        print(f"        subject={'; '.join(p['cats'])}")
        print(f"        date={p['submitted']}")

def execute_plan(plan, library=None):
    """Execute renames, metadata updates, and logging."""
    import fitz  # verify available
    now = datetime.datetime.now().isoformat(timespec='seconds')
    for p in plan:
        src = p['src_path']
        src_folder = p['src_folder']

        if library and p['action'] == 'MOVE':
            dest_dir = os.path.join(library, p['dest_subfolder'])
        else:
            dest_dir = src_folder

        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, p['new_name'])

        # 1. Update metadata
        kw = p['slugs'].replace(' ', ', ')
        subj = '; '.join(p['cats'])
        try:
            update_pdf_metadata(src, p['title'], kw, subj, p['submitted'])
        except Exception as e:
            print(f"  ERROR metadata {p['orig_name']}: {e}", file=sys.stderr)

        # 2. Rename/move
        if src != dest:
            if os.path.exists(dest):
                print(f"  SKIP (dest exists): {p['new_name']}", file=sys.stderr)
                continue
            os.rename(src, dest)
            action_str = 'MOVE' if src_folder != dest_dir else 'RENAME'
            log_line = f"{now} {action_str:6s} {p['orig_name']} → {p['dest_subfolder']}/{p['new_name']}"
            append_log(src_folder, log_line)
            if src_folder != dest_dir:
                append_log(dest_dir, log_line)
            print(f"  {action_str}: {p['new_name']}")
        else:
            log_line = f"{now} META   {p['orig_name']}"
            append_log(src_folder, log_line)
            print(f"  META:   {p['orig_name']}")

        # 3. Set file dates
        if p['submitted']:
            dt = parse_date(p['submitted'])
            if dt:
                set_file_dates(dest if src != dest else src, dt)

# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Arxiv Paper Organizer')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--scan', metavar='FOLDER', help='Dry run: print plan')
    group.add_argument('--execute', metavar='FOLDER', help='Execute plan')
    parser.add_argument('--recurse', action='store_true', help='Recurse into subfolders')
    parser.add_argument('--library', metavar='PATH', help='Library root for cross-folder moves')
    args = parser.parse_args()

    folder = args.scan or args.execute
    if not os.path.isdir(folder):
        print(f"Error: {folder} is not a directory", file=sys.stderr)
        sys.exit(1)

    plan = scan_folder(folder, recurse=args.recurse)
    print(f"Found {len(plan)} arxiv papers")
    if args.scan:
        print_plan(plan, library=args.library)
    else:
        execute_plan(plan, library=args.library)
        print(f"\nDone. Processed {len(plan)} files.")