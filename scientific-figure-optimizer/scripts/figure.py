"""Controlled CSV line plots. No numerical transformations are implemented."""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import warnings
import xml.etree.ElementTree as ET

VERSION = '0.1.3'
STYLE = {'width_mm': 120, 'height_mm': 85, 'dpi': 300,
         'font': 'DejaVu Sans', 'font_pt': 9, 'line_pt': 1.2,
         'colors': ['#243f53', '#666666', '#8b4513'],
         'xlim': None, 'ylim': None}


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def keys(obj, allowed, where):
    require(isinstance(obj, dict), f'{where} must be an object')
    require(not set(obj) - set(allowed), f'Unknown fields in {where}: {set(obj)-set(allowed)}')


def nonempty(obj, names):
    for name in names:
        require(isinstance(obj.get(name), str) and bool(obj[name].strip()), f'Missing text: {name}')


def text_list(value, where, required=True):
    require(isinstance(value, list) and (bool(value) or not required) and
            all(isinstance(v, str) and v.strip() for v in value), f'{where} must be a list of nonempty strings')


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f'Duplicate JSON field: {key}')
            result[key] = value
        return result
    def constant(value):
        raise Invalid(f'Non-standard JSON constant: {value}')
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'),
                          object_pairs_hook=pairs, parse_constant=constant)
    except (OSError, UnicodeError, ValueError) as e:
        raise Invalid(f'{path}: {e}') from e


def load(brief_path):
    brief_path = Path(brief_path).resolve()
    b = read_json(brief_path)
    keys(b, ['version', 'input', 'provenance', 'reader_question', 'claim', 'must_keep',
             'allowed_style_changes', 'processing', 'x', 'series', 'style',
             'reference_lines', 'note', 'acceptance', 'y_label', 'font_sha256'], 'brief')
    require(type(b.get('version')) is int and b['version'] == 1, 'version must be integer 1')
    nonempty(b, ['input', 'reader_question', 'claim'])
    text_list(b.get('must_keep'), 'must_keep')
    require(b.get('processing') == {'method': 'none'}, 'Only processing.method=none is supported; request a separately reviewed processing extension')
    for field in ['note', 'y_label']:
        require(field not in b or isinstance(b[field], str), f'{field} must be text')
    require('font_sha256' not in b or (isinstance(b['font_sha256'], str) and
            re.fullmatch('[0-9a-f]{64}', b['font_sha256'])), 'Invalid font_sha256')
    keys(b.get('provenance'), ['source', 'evidence_level', 'rights', 'public_redistribution'], 'provenance')
    nonempty(b['provenance'], ['source', 'evidence_level', 'rights'])
    require(type(b['provenance'].get('public_redistribution')) is bool, 'public_redistribution must be boolean')
    keys(b.get('acceptance'), ['formats', 'human_review'], 'acceptance')
    require(b['acceptance'].get('formats') == ['svg', 'pdf', 'png'], 'formats must be svg,pdf,png')
    text_list(b['acceptance'].get('human_review'), 'acceptance.human_review')
    series = b.get('series')
    require(isinstance(series, list) and 1 <= len(series) <= 3, 'Support 1 to 3 series on a shared linear axis')
    for i, spec in enumerate([b.get('x')] + series):
        keys(spec, ['column', 'label', 'unit'], f'x/series[{i}]')
        nonempty(spec, ['column', 'label', 'unit'])
        require(all(spec[k] == spec[k].strip() for k in ['column', 'label', 'unit']), f'x/series[{i}] contains surrounding whitespace')
    require(len({s['label'].casefold() for s in series}) == len(series), 'Series labels must be unique (case insensitive)')
    require(len({s['unit'] for s in series}) == 1, 'Series must have the same explicit unit')
    if len(series) > 1:
        nonempty(b, ['y_label'])
    require(len({s['column'] for s in series}) == len(series), 'Duplicate series column')
    custom = b.get('style', {})
    keys(custom, STYLE, 'style')
    allowed = b.get('allowed_style_changes')
    text_list(allowed, 'allowed_style_changes', required=False)
    require(set(allowed) <= set(STYLE), 'allowed_style_changes must name supported style fields')
    require(set(custom) <= set(allowed), 'Style changes exceed authorization in allowed_style_changes')
    style = STYLE | custom
    for name, low, high in [('width_mm', 65, 250), ('height_mm', 55, 250),
                            ('dpi', 96, 1200), ('font_pt', 7, 18), ('line_pt', .4, 3)]:
        v = style[name]
        require(type(v) in (int, float) and math.isfinite(v) and low <= v <= high, f'Invalid {name}')
    require(type(style['dpi']) is int, 'dpi must be integer')
    require(style['width_mm']/25.4*style['height_mm']/25.4*style['dpi']**2 <= 40_000_000,
            'Requested raster exceeds 40 megapixels; reduce authorized dimensions or DPI')
    require(isinstance(style['font'], str) and style['font'].strip(), 'font required')
    require(isinstance(style['colors'], list) and len(style['colors']) >= len(series) and
            all(isinstance(c, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', c) for c in style['colors']), 'Use #RRGGBB colors')
    for lim in ['xlim', 'ylim']:
        v = style[lim]
        require(v is None or (isinstance(v, list) and len(v) == 2 and all(type(n) in (int, float) and math.isfinite(n) for n in v) and v[0] < v[1]), f'Invalid {lim}')
    refs = b.get('reference_lines', [])
    require(isinstance(refs, list) and len(refs) <= 2, 'At most 2 reference lines')
    for r in refs:
        keys(r, ['x', 'label', 'source', 'status'], 'reference line')
        nonempty(r, ['label', 'source', 'status'])
        require(type(r.get('x')) in (int, float) and math.isfinite(r['x']), 'Invalid reference x')
    require(len({r['label'].strip().casefold() for r in refs}) == len(refs), 'Reference labels must be unique')
    require(not refs or (isinstance(b.get('note'), str) and b['note'].strip()), 'Reference lines require a visible note explaining status')
    source = (brief_path.parent / b['input']).resolve()
    try:
        raw = source.read_bytes()
        reader = csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True)
        cols = next(reader, [])
    except (OSError, UnicodeError, csv.Error) as e:
        raise Invalid(f'{source}: {e}') from e
    require(cols and all(c.strip() and c == c.strip() for c in cols) and len(cols) == len(set(cols)), 'CSV needs nonempty, unique headers without surrounding whitespace')
    selected = [b['x']['column']] + [s['column'] for s in series]
    require(set(selected) <= set(cols), f'Required column missing: {sorted(set(selected)-set(cols))}')
    arrays = [[] for _ in selected]
    seen = [{} for _ in selected]
    try:
        for row in reader:
            i = reader.line_num
            require(len(row) == len(cols), f'Ragged CSV row {i}: expected {len(cols)} fields, got {len(row)}')
            for a, col in zip(arrays, selected):
                v = row[cols.index(col)].strip()
                require(v != '', f'Missing value at row {i}, column {col}')
                try:
                    number = float(v)
                except ValueError as e:
                    raise Invalid(f'Non-numeric value at row {i}, column {col}') from e
                require(math.isfinite(number), f'Non-finite value at row {i}, column {col}')
                try:
                    exact = Decimal(v)
                except InvalidOperation as e:
                    raise Invalid(f'Invalid decimal at row {i}, column {col}') from e
                require(exact == 0 or (number != 0 and 1e-100 <= abs(number) <= 1e100),
                        f'Unsupported numerical magnitude at row {i}, column {col}; supported nonzero magnitude is 1e-100 to 1e100, no rescaling performed')
                prior = seen[selected.index(col)]
                require(number not in prior or prior[number] == exact,
                        f'Floating-point precision would merge distinct values at row {i}, column {col}')
                prior[number] = exact
                a.append(number)
    except csv.Error as e:
        raise Invalid(f'{source}: malformed CSV near row {reader.line_num}: {e}') from e
    require(len(arrays[0]) >= 2, 'Need at least 2 points')
    notices = []
    x = arrays[0]
    if any(v <= u for u, v in zip(x, x[1:])):
        notices.append('X order is non-increasing somewhere; source order and duplicate points retained.')
    for lim, data in [('xlim', x), ('ylim', [v for a in arrays[1:] for v in a])]:
        if style[lim] is not None:
            require(style[lim][0] <= min(data) and max(data) <= style[lim][1], f'{lim} would hide data')
    for r in refs:
        lim = style['xlim'] or [min(x), max(x)]
        require(lim[0] <= r['x'] <= lim[1], 'Reference line outside display range')
    return b, style, source, arrays, notices


def contrast(color):
    rgb = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
    linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    return 1.05/(sum(v*w for v, w in zip(linear, [.2126, .7152, .0722]))+.05)


REQUIRED_FILES = {'source.csv', 'brief.json', 'figure.py', 'requirements.txt',
                  'REPRODUCE.md', 'figure.svg', 'figure.pdf', 'figure.png',
                  'final-size.png', 'grayscale.png'}


def _pdf_finite_numbers(values, count, where):
    values = values.get_object() if hasattr(values, 'get_object') else values
    require(isinstance(values, (list, tuple)) and len(values) == count,
            f'Invalid Type3 {where}')
    require(all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                for v in values), f'Invalid Type3 {where}')


def _embedded_type3_font(font, inherited_resources, seen):
    """Check embedded Type3 glyph structure, not full PDF rendering semantics.

    Adobe PDF Reference 1.3, Table 5.9: Type3 embeds glyph content in CharProcs
    rather than requiring a FontDescriptor/FontFile. Explicit Differences only;
    named encodings require a separately implemented mapping before acceptance.
    Font embedding does not certify glyph advance/Widths consistency or complete
    PDF graphics semantics; rendered layout remains a separate check.
    """
    from pypdf.generic import ContentStream, DictionaryObject, NameObject, StreamObject
    _pdf_finite_numbers(font.get('/FontBBox'), 4, 'FontBBox')
    _pdf_finite_numbers(font.get('/FontMatrix'), 6, 'FontMatrix')
    matrix = font['/FontMatrix']
    require(matrix[0]*matrix[3]-matrix[1]*matrix[2] != 0, 'Singular Type3 FontMatrix')
    first, last = font.get('/FirstChar'), font.get('/LastChar')
    require(isinstance(first, int) and not isinstance(first, bool) and
            isinstance(last, int) and not isinstance(last, bool) and
            0 <= first <= last <= 255, 'Invalid Type3 character range')
    _pdf_finite_numbers(font.get('/Widths'), last-first+1, 'Widths')
    encoding = font.get('/Encoding')
    encoding = encoding.get_object() if encoding is not None else None
    require(isinstance(encoding, DictionaryObject) and '/Differences' in encoding,
            'Type3 requires a supported explicit Differences encoding')
    differences = encoding['/Differences']
    require(isinstance(differences, (list, tuple)) and differences,
            'Invalid Type3 Differences encoding')
    mapping, code = {}, None
    for item in differences:
        if isinstance(item, int) and not isinstance(item, bool):
            require(0 <= item <= 255, 'Invalid Type3 encoding code')
            code = item
        else:
            require(isinstance(item, NameObject) and code is not None and code <= 255,
                    'Invalid Type3 encoding glyph name')
            require(code not in mapping, 'Duplicate Type3 encoding code')
            mapping[code] = item
            code += 1
    require(mapping and all(first <= c <= last for c in mapping),
            'Type3 encoding outside character range')
    charprocs = font.get('/CharProcs')
    charprocs = charprocs.get_object() if charprocs is not None else None
    require(isinstance(charprocs, DictionaryObject) and charprocs, 'Type3 CharProcs missing or empty')
    require(all(name in charprocs for name in mapping.values()), 'Type3 encoded glyph missing from CharProcs')
    glyph_resources = font.get('/Resources', inherited_resources).get_object()
    require(isinstance(glyph_resources, DictionaryObject), 'Invalid Type3 Resources')
    for name, ref in charprocs.items():
        require(isinstance(name, NameObject), 'Invalid Type3 CharProcs glyph name')
        stream = ref.get_object()
        require(isinstance(stream, StreamObject), 'Type3 glyph is not an embedded stream')
        try:
            operations = ContentStream(stream, getattr(ref, 'pdf', None)).operations
        except Exception as error:
            raise Invalid(f'Cannot parse embedded Type3 glyph: {name}') from error
        require(bool(operations), 'Empty Type3 glyph program')
        operands, operator = operations[0]
        require(operator in [b'd0', b'd1'], 'Type3 glyph must begin with d0 or d1')
        _pdf_finite_numbers(operands, 2 if operator == b'd0' else 6, 'glyph metrics')
        # A spacing glyph may legitimately contain only d0/d1 and paint nothing.
        for operands, operator in operations[1:]:
            if operator in [b'Do', b'gs', b'sh', b'Tf', b'CS', b'cs']:
                category = {b'Do':'/XObject', b'gs':'/ExtGState', b'sh':'/Shading',
                            b'Tf':'/Font', b'CS':'/ColorSpace', b'cs':'/ColorSpace'}[operator]
                require(bool(operands) and isinstance(operands[0], NameObject),
                        'Invalid Type3 glyph resource operand')
                resource_name = operands[0]
                if category == '/ColorSpace' and resource_name in ['/DeviceGray', '/DeviceRGB', '/DeviceCMYK', '/Pattern']:
                    continue
                entries = glyph_resources.get(category)
                require(entries is not None and resource_name in entries.get_object(),
                        f'Type3 glyph resource missing: {resource_name}')
    return embedded_pdf_fonts(glyph_resources, seen)


def embedded_pdf_fonts(resources, seen=None):
    """Check page and nested Form font resources; avoid cycles/shared resources."""
    seen = set() if seen is None else seen
    resources = resources.get_object()
    if id(resources) in seen:
        return 0
    seen.add(id(resources))
    count = 0
    fonts = resources.get('/Font')
    for font in fonts.get_object().values() if fonts else []:
        f = font.get_object()
        if f.get('/Subtype') == '/Type3':
            count += _embedded_type3_font(f, resources, seen)
        else:
            for child in f.get('/DescendantFonts', [font]):
                desc = child.get_object().get('/FontDescriptor')
                require(desc is not None and any(k in desc.get_object() for k in ['/FontFile', '/FontFile2', '/FontFile3']), 'PDF font is not embedded')
        count += 1
    objects = resources.get('/XObject')
    for obj in objects.get_object().values() if objects else []:
        nested = obj.get_object().get('/Resources')
        if nested:
            count += embedded_pdf_fonts(nested, seen)
    return count


def verify(folder, _pending=False):
    try:
        return _verify(folder, _pending)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError,
            ET.ParseError, ArithmeticError) as e:
        raise Invalid(f'Verification failed in {folder}: {e}') from e


def _verify(folder, pending):
    """Independently read back SVG geometry, CSV, PDF and raster properties."""
    from PIL import Image
    from pypdf import PdfReader
    folder = Path(folder)
    a = read_json(folder/'audit.json')
    require(isinstance(a, dict) and isinstance(a.get('hashes'), dict), 'Invalid audit manifest')
    require(set(a['hashes']) == REQUIRED_FILES, 'Manifest must include every required delivery file')
    for name, expected in a['hashes'].items():
        require(Path(name).name == name, 'Unsafe manifest filename')
        require(sha(folder/name) == expected, f'File changed: {name}')
    result = read_json(folder/'verification.json')
    require(result.get('status') == 'PASS' or (pending and result.get('status') == 'PENDING'), 'Stored verification is not PASS; regenerate the delivery')
    require(read_json(folder/'brief.json').get('input') == 'source.csv', 'Snapshot brief must use local source.csv')
    b, style, source, arrays, _ = load(folder/'brief.json')
    require(sha(source) == a['source_sha256'], 'Source hash differs from audit')
    require(a['point_count_per_series'] == len(arrays[0]) and a['series_count'] == len(arrays)-1,
            'Audit point/series counts differ from source')
    root = ET.parse(folder/'figure.svg').getroot()
    ns = {'s': 'http://www.w3.org/2000/svg'}
    require(bool(root.findall('.//s:text', ns)), 'SVG lacks editable text')
    require(not root.findall('.//s:image', ns), 'Unexpected raster in SVG')
    width, height = style['width_mm']/25.4*72, style['height_mm']/25.4*72
    require(abs(float(root.attrib['width'].rstrip('pt'))-width) < .001, 'SVG width mismatch')
    require(abs(float(root.attrib['height'].rstrip('pt'))-height) < .001, 'SVG height mismatch')
    box, xlim, ylim = a['axes_box_pt'], a['xlim'], a['ylim']
    require(all(math.isfinite(v) for v in box+xlim+ylim) and box[2] > 0 and box[3] > 0 and
            xlim[0] < xlim[1] and ylim[0] < ylim[1], 'Invalid axes geometry')
    require(xlim[0] <= min(arrays[0]) <= max(arrays[0]) <= xlim[1] and
            all(ylim[0] <= v <= ylim[1] for y in arrays[1:] for v in y), 'Exported limits hide source data')
    for name, actual in [('xlim', xlim), ('ylim', ylim)]:
        require(style[name] is None or style[name] == actual, f'Exported {name} differs from brief')
    for i, y in enumerate(arrays[1:]):
        group = root.find(f'.//s:g[@id="series-{i}"]', ns)
        require(group is not None, 'Missing SVG series')
        path = group.find('s:path', ns)
        require(path is not None, 'Missing SVG path')
        require('transform' not in group.attrib and 'transform' not in path.attrib, 'Unexpected series transform')
        clip_id = re.fullmatch(r'url\(#([^)]*)\)', path.attrib.get('clip-path', ''))
        require(clip_id is not None, 'SVG curve clip rectangle missing')
        rect = root.find(f'.//s:clipPath[@id="{clip_id[1]}"]/s:rect', ns)
        require(rect is not None and all(abs(float(rect.attrib[k])-v) <= 2e-5
                for k, v in zip(['x', 'y', 'width', 'height'],
                                [box[0], height-box[1]-box[3], box[2], box[3]])),
                'SVG curve clip rectangle differs from axes')
        d = path.attrib['d']
        require(not re.search(r'[A-DF-KN-Za-df-kn-z]', d), 'Unsupported SVG path command')
        nums = [float(n) for n in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', d)]
        commands = re.findall('[MLml]', d)
        require(commands == ['M']+['L']*(len(y)-1) and len(nums) == 2*len(y), 'Exported SVG point count/order changed')
        for j, (xv, yv) in enumerate(zip(arrays[0], y)):
            px = box[0]+(xv-xlim[0])/(xlim[1]-xlim[0])*box[2]
            py = height-(box[1]+(yv-ylim[0])/(ylim[1]-ylim[0])*box[3])
            require(abs(nums[2*j]-px) <= 2e-5 and abs(nums[2*j+1]-py) <= 2e-5, 'SVG numeric readback differs from source')
            require(-2e-5 <= nums[2*j] <= width+2e-5 and -2e-5 <= nums[2*j+1] <= height+2e-5, 'SVG point outside canvas')
    for i, ref in enumerate(b.get('reference_lines', [])):
        group = root.find(f'.//s:g[@id="reference-{i}"]', ns)
        require(group is not None, 'Missing reference line')
        path = group.find('s:path', ns)
        require(path is not None, 'Missing reference path')
        values = [float(n) for n in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', path.attrib['d'])]
        expected_x = box[0]+(ref['x']-xlim[0])/(xlim[1]-xlim[0])*box[2]
        require(len(values) == 4 and abs(values[0]-expected_x) <= 2e-5 and abs(values[2]-expected_x) <= 2e-5 and
                abs(values[1]-(height-box[1])) <= 2e-5 and abs(values[3]-(height-box[1]-box[3])) <= 2e-5,
                'Reference position changed')
    pdf = PdfReader(folder/'figure.pdf')
    require(len(pdf.pages) == 1, 'PDF must have one page')
    page = pdf.pages[0]
    require(abs(float(page.mediabox.width)-width) < .001 and abs(float(page.mediabox.height)-height) < .001, 'PDF page dimensions mismatch')
    require(embedded_pdf_fonts(page['/Resources']) > 0, 'PDF fonts missing')
    for name, dpi in [('figure.png', style['dpi']), ('final-size.png', 96), ('grayscale.png', style['dpi'])]:
        with Image.open(folder/name) as im:
            im.load()
            expected = [int(style['width_mm']/25.4*dpi), int(style['height_mm']/25.4*dpi)]
            require(all(abs(v-e) <= 1 for v, e in zip(im.size, expected)), f'{name} dimensions mismatch')
            recorded_dpi = im.info.get('dpi')
            require(recorded_dpi is not None and len(recorded_dpi) == 2 and
                    all(abs(v-dpi) <= .03 for v in recorded_dpi), f'{name} DPI metadata mismatch')
            require(all(abs(pixels/resolution*25.4-target) <= 25.4/dpi+.01
                        for pixels, resolution, target in zip(im.size, recorded_dpi,
                                                             [style['width_mm'], style['height_mm']])),
                    f'{name} physical size mismatch')
            if name == 'grayscale.png':
                require(im.mode == 'L', 'Grayscale mode mismatch')
    return {'status': 'PASS', 'svg_numeric_readback': True, 'pdf_size_and_embedded_fonts': True,
            'raster_dimensions': True, 'raster_dpi_and_physical_size': True,
            'grayscale_file': True, 'hashes': True, 'all_points_visible': True,
            'human_scientific_and_visual_review': 'PENDING'}


def dependency_versions():
    """Lock the installed dependency closure, excluding unrelated host packages."""
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    versions = {}
    todo = ['matplotlib', 'numpy', 'Pillow', 'pypdf']
    while todo:
        name = canonicalize_name(todo.pop())
        if name in versions:
            continue
        dist = importlib.metadata.distribution(name)
        versions[name] = dist.version
        for text in dist.requires or []:
            requirement = Requirement(text)
            if requirement.marker is None or requirement.marker.evaluate({'extra': ''}):
                todo.append(requirement.name)
    return dict(sorted(versions.items()))


def render(brief, output):
    b, style, source, arrays, notices = load(brief)
    output = Path(output).resolve()
    require(not output.exists(), 'Output already exists; choose a new version directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.sfo-', dir=output.parent))
    fig = None
    rc_original = None
    try:
        os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'sfo-mpl-cache'))
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.font_manager import findfont
        from matplotlib.text import Text
        from PIL import Image, ImageOps
        font = findfont(style['font'], fallback_to_default=False)
        require('font_sha256' not in b or sha(font) == b['font_sha256'],
                'Font fingerprint differs from portable brief; install the exact licensed font before rerunning')
        rc_original = matplotlib.rcParams.copy()
        plt.rcdefaults()
        plt.rcParams.update({'font.family': style['font'], 'font.size': style['font_pt'],
                             'svg.fonttype': 'none', 'pdf.fonttype': 42, 'path.simplify': False,
                             'agg.path.chunksize': 0, 'axes.unicode_minus': False,
                             'text.usetex': False, 'text.parse_math': False,
                             'svg.hashsalt': 'scientific-figure-optimizer'})
        for c in style['colors'][:len(b['series'])]:
            require(contrast(c) >= 3, 'Curve contrast on white is below 3:1')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            fig = plt.figure(figsize=(style['width_mm']/25.4, style['height_mm']/25.4), dpi=style['dpi'])
            note_lines = len(b.get('note', '').splitlines())
            bottom = .23 + .04*max(0, note_lines-1)
            require(bottom < .55, 'Too many note lines for this layout')
            ax = fig.add_axes([.20, bottom, .75, .83-bottom])
            for i, (s, y) in enumerate(zip(b['series'], arrays[1:])):
                line, = ax.plot(arrays[0], y, lw=style['line_pt'], color=style['colors'][i],
                                ls=['-', '--', ':'][i], label=s['label'])
                line.set_gid(f'series-{i}')
                require(list(line.get_xdata()) == arrays[0] and list(line.get_ydata()) == y, 'Plot data changed')
            reference_texts = []
            for i, r in enumerate(b.get('reference_lines', [])):
                line = ax.axvline(r['x'], color='#777777', ls=['--', ':'][i], lw=.7, zorder=0)
                line.set_gid(f'reference-{i}')
                reference_texts.append(ax.text(r['x'], 1.025, r['label'], transform=ax.get_xaxis_transform(), ha='center', fontsize=style['font_pt']-1))
            ax.set_xlabel(f"{b['x']['label']} ({b['x']['unit']})")
            ax.set_ylabel(f"{b.get('y_label', b['series'][0]['label'])} ({b['series'][0]['unit']})")
            if style['xlim'] is not None:
                ax.set_xlim(style['xlim'])
            if style['ylim'] is not None:
                ax.set_ylim(style['ylim'])
            ax.spines[['top', 'right']].set_visible(False)
            ax.tick_params(direction='out', width=.7, length=3)
            legend = ax.legend(loc='lower left', bbox_to_anchor=(0, 1.13), borderaxespad=0,
                               frameon=False, ncol=len(b['series']), fontsize=style['font_pt']-1)
            if b.get('note'):
                fig.text(.20, .035, b['note'], fontsize=style['font_pt']-2, va='bottom')
            boxes = []
            for dpi in [style['dpi'], 96]:
                fig.set_dpi(dpi)
                fig.canvas.draw()
                renderer = fig.canvas.get_renderer()
                w, h = fig.canvas.get_width_height()
                # Locators may retain ticks beyond view limits; these are not drawn.
                hidden_ticks = set()
                for axis, limits in [(ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())]:
                    for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                        if not limits[0] <= tick.get_loc() <= limits[1]:
                            hidden_ticks.update([tick.label1, tick.label2])
                for t in fig.findobj(Text):
                    if t not in hidden_ticks and t.get_visible() and t.get_text():
                        bb = t.get_window_extent(renderer)
                        require(bb.x0 >= -.5 and bb.y0 >= -.5 and bb.x1 <= w+.5 and bb.y1 <= h+.5, f'Text clipped: {t.get_text()}')
                require(not legend.get_window_extent(renderer).overlaps(ax.get_window_extent(renderer)), 'Legend covers data axes')
                for i, t in enumerate(reference_texts):
                    bb = t.get_window_extent(renderer)
                    require(not bb.overlaps(legend.get_window_extent(renderer)), 'Reference annotation overlaps legend')
                    require(all(not bb.overlaps(other.get_window_extent(renderer)) for other in reference_texts[i+1:]),
                            'Reference annotations overlap')
                for note in fig.texts:
                    require(not note.get_window_extent(renderer).overlaps(ax.xaxis.label.get_window_extent(renderer)), 'Note overlaps axis label')
                boxes.append({'dpi': dpi, 'text_inside_canvas': True, 'legend_outside_data_axes': True})
            fig.set_dpi(style['dpi'])
            fig.canvas.draw()
            # Matplotlib's SVG backend uses points, independently of raster DPI.
            box = [v*72 for v in ax.get_position().bounds]
            box = [box[0]*fig.get_figwidth(), box[1]*fig.get_figheight(),
                   box[2]*fig.get_figwidth(), box[3]*fig.get_figheight()]
            for ext in ['svg', 'pdf', 'png']:
                fig.savefig(stage/f'figure.{ext}', dpi=style['dpi'], facecolor='white')
            fig.savefig(stage/'final-size.png', dpi=96, facecolor='white')
            plt.close(fig)
            require(not caught, 'Rendering warnings: '+ '; '.join(str(w.message) for w in caught))
        with Image.open(stage/'figure.png') as image:
            ImageOps.grayscale(image).save(stage/'grayscale.png', dpi=(style['dpi'], style['dpi']))
        shutil.copyfile(source, stage/'source.csv')
        require(sha(source) == sha(stage/'source.csv'), 'Source snapshot changed')
        snapshot = b | {'input': 'source.csv', 'font_sha256': sha(font)}
        write_json(stage/'brief.json', snapshot)
        shutil.copyfile(__file__, stage/'figure.py')
        versions = dependency_versions()
        (stage/'requirements.txt').write_text('\n'.join(f'{n}=={v}' for n, v in versions.items())+'\n', encoding='utf-8')
        (stage/'REPRODUCE.md').write_text(
            f'Tested Python {sys.version.split()[0]}; use the same Python minor version for this lock.\n\n'
            'From this folder, create an isolated environment and install dependencies:\n\n'
            '```powershell\npython -m venv .venv\n.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n'
            '.venv\\Scripts\\python.exe figure.py verify .\n'
            '.venv\\Scripts\\python.exe figure.py render brief.json --out ../rerun-new-version\n'
            '.venv\\Scripts\\python.exe figure.py verify ../rerun-new-version\n```\n\n'
            f'Font: {style["font"]}; SHA256 {sha(font)}. The portable brief enforces this fingerprint. '
            'DejaVu Sans comes with pinned Matplotlib. Custom fonts require an independently licensed installation; '
            'no fonts are copied. This dependency closure targets the recorded Python/OS; other platforms require revalidation. '
            'SVG text needs the font on the editing machine. File bytes may differ due to export timestamps; '
            'compare numerical readback, point order, source hash and dimensions. '
            'Human scientific and final-size visual review remains required.\n', encoding='utf-8')
        audit = {'tool_version': VERSION, 'python': sys.version.split()[0], 'versions': versions,
                 'source_sha256': sha(source), 'font_file_sha256': sha(font), 'font_family': style['font'],
                 'platform': sys.platform,
                 'point_count_per_series': len(arrays[0]), 'series_count': len(arrays)-1,
                 'source_order_preserved': True, 'processing': {'method': 'none'},
                 'xlim': list(ax.get_xlim()), 'ylim': list(ax.get_ylim()), 'axes_box_pt': box,
                 'layout_checks': boxes, 'warnings': notices,
                 'human_review': {'status': 'PENDING', 'checks': b['acceptance']['human_review']},
                 'editability': {'script_and_csv': 'VERIFIED', 'svg_text_and_paths': 'VERIFIED',
                                 'native_project': 'NOT_TESTED', 'word_ole': 'NOT_TESTED'},
                 'limits': ['Human scientific review pending', 'No journal compliance certification',
                            'No automatic aesthetic or color-vision pass', 'No statistical inference'],
                 'hashes': {p.name: sha(p) for p in stage.iterdir() if p.is_file()}}
        write_json(stage/'audit.json', audit)
        write_json(stage/'verification.json', {'status': 'PENDING'})
        result = verify(stage, _pending=True)
        write_json(stage/'verification.json', result)
        require(not output.exists(), 'Output appeared during rendering; refusing overwrite')
        stage.rename(output)
        return {'status': 'PASS_AUTOMATED_CHECKS', 'output': str(output), 'points': len(arrays[0]), 'human_review': 'PENDING'}
    except BaseException:
        shutil.rmtree(stage)
        raise
    finally:
        if fig is not None:
            plt.close(fig)
        if rc_original is not None:
            matplotlib.rcParams.update(rc_original)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for command in ['check', 'render']:
        s = sub.add_parser(command)
        s.add_argument('brief')
        if command == 'render':
            s.add_argument('--out', required=True)
    sub.add_parser('verify').add_argument('folder')
    args = p.parse_args()
    try:
        if args.command == 'check':
            _, _, _, arrays, notices = load(args.brief)
            result = {'status': 'VALID', 'points': len(arrays[0]), 'notices': notices}
        elif args.command == 'render':
            result = render(args.brief, args.out)
        else:
            result = verify(args.folder)
        print(json.dumps(result, ensure_ascii=True))
    except (Invalid, ValueError, KeyError, TypeError, OSError, ImportError, RuntimeError, ArithmeticError, csv.Error, ET.ParseError) as e:
        if args.command == 'verify' and (Path(args.folder)/'audit.json').is_file():
            try:
                write_json(Path(args.folder)/'verification.json', {'status': 'FAIL', 'error': str(e)})
            except OSError:
                pass
        print(json.dumps({'status': 'FAIL', 'error': str(e)}, ensure_ascii=True), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
