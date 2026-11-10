"""Adversarial regression tests for the public CSV workflow.

Fixtures are independently constructed teaching values; no private data are used.
"""
import copy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('adversarial_figure', ROOT/'scripts/figure.py')
figure = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(figure)


class AdversarialTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.brief = json.loads((ROOT/'assets/brief-template.json').read_text(encoding='utf-8'))
        self.brief['input'] = 'input.csv'
        self.data = 'displacement,force_a,force_b\n0,0,0\n1,2,3\n2,4,6\n'

    def save(self):
        (self.root/'input.csv').write_text(self.data, encoding='utf-8')
        path = self.root/'brief.json'
        path.write_text(json.dumps(self.brief, ensure_ascii=False), encoding='utf-8')
        return path

    def cli(self, *arguments):
        return subprocess.run([sys.executable, '-X', 'utf8', str(ROOT/'scripts/figure.py'),
                               *map(str, arguments)], capture_output=True, text=True,
                              encoding='utf-8', timeout=90)

    def assert_cli_failure(self, result):
        self.assertEqual(result.returncode, 2, result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stderr)['status'], 'FAIL')
        self.assertNotIn('Traceback', result.stderr)

    def test_csv_shape_and_finite_values(self):
        headers = 'displacement,force_a,force_b\n'
        invalid = {
            'empty': '',
            'headers_only': headers,
            'one_point': headers+'0,0,0\n',
            'missing_column': 'wrong,force_a,force_b\n0,0,0\n1,2,3\n',
            'duplicate_header': 'displacement,force_a,force_a\n0,0,0\n1,2,3\n',
            'short_row': headers+'0,0,0\n1,2\n',
            'long_row': headers+'0,0,0\n1,2,3,4\n',
            'blank_record': headers+'0,0,0\n\n1,2,3\n',
            'empty_value': headers+'0,0,0\n1,,3\n',
            'text_value': headers+'0,0,0\n1,NA,3\n',
            'nan': headers+'0,0,0\n1,NaN,3\n',
            'infinity': headers+'0,0,0\n1,Inf,3\n',
            'overflow': headers+'0,0,0\n1,1e999,3\n',
            'underflow': headers+'0,0,0\n1,1e-999,3\n',
            'broken_quote': headers+'0,0,0\n1,"2,3\n',
        }
        for name, data in invalid.items():
            with self.subTest(case=name):
                self.data = data
                with self.assertRaises(figure.Invalid):
                    figure.load(self.save())

    def test_value_error_identifies_csv_location(self):
        for value in ['', 'NA', 'NaN', '-Inf']:
            with self.subTest(value=value):
                self.data = f'displacement,force_a,force_b\n0,0,0\n1,{value},3\n'
                with self.assertRaisesRegex(figure.Invalid, r'row 3.*column force_a'):
                    figure.load(self.save())

    def test_missing_file_and_malformed_json_cli(self):
        self.assert_cli_failure(self.cli('check', self.root/'absent.json'))
        path = self.save()
        self.brief['input'] = 'absent.csv'
        path = self.save()
        self.assert_cli_failure(self.cli('render', path, '--out', self.root/'missing-source'))
        self.assertFalse((self.root/'missing-source').exists())
        path.write_text('{"version":', encoding='utf-8')
        result = self.cli('check', path)
        self.assert_cli_failure(result)

    def test_duplicate_and_nonstandard_json_rejected(self):
        path = self.save()
        valid = path.read_text(encoding='utf-8')
        for text in [valid.replace('"version": 1', '"version": 1, "version": 1'),
                     valid.replace('"style": {}', '"style": {"width_mm": NaN}'),
                     valid.replace('"style": {}', '"style": {"width_mm": Infinity}')]:
            with self.subTest(json=text[:70]):
                path.write_text(text, encoding='utf-8')
                with self.assertRaises(figure.Invalid):
                    figure.load(path)

    def test_wrong_field_types_rejected(self):
        original = copy.deepcopy(self.brief)
        changes = [
            {'version': True}, {'note': 10}, {'y_label': 10},
            {'allowed_style_changes': [[]]},
            {'acceptance': {'formats': ['svg', 'pdf', 'png'], 'human_review': [12]}},
            {'must_keep': ['']}, {'input': ['input.csv']}, {'x': []},
            {'series': 'force_a'}, {'style': []}, {'reference_lines': {}},
            {'unknown_option': True},
        ]
        for change in changes:
            with self.subTest(change=change):
                self.brief = copy.deepcopy(original)
                self.brief.update(change)
                with self.assertRaises(figure.Invalid):
                    figure.load(self.save())

    def test_units_and_ambiguous_labels_rejected(self):
        original = copy.deepcopy(self.brief)
        for case in ['missing', 'conflict', 'duplicate', 'whitespace_ambiguity']:
            with self.subTest(case=case):
                self.brief = copy.deepcopy(original)
                if case == 'missing':
                    self.brief['x']['unit'] = ''
                elif case == 'conflict':
                    self.brief['series'][1]['unit'] = 'kN'
                elif case == 'duplicate':
                    self.brief['series'][1]['label'] = self.brief['series'][0]['label']
                else:
                    self.brief['series'][1]['label'] = ' '+self.brief['series'][0]['label']+' '
                with self.assertRaises(figure.Invalid):
                    figure.load(self.save())

    def test_bad_style_types_values_and_authorization(self):
        original = copy.deepcopy(self.brief)
        styles = [
            {'width_mm': 0}, {'height_mm': -1}, {'dpi': 0}, {'dpi': 300.5},
            {'width_mm': True}, {'font_pt': '9'}, {'font': ''},
            {'colors': ['red', '#666666']}, {'colors': '#243f53'},
            {'xlim': [2, 0]}, {'ylim': [0, 1]}, {'xlim': [True, 4]},
        ]
        for style in styles:
            with self.subTest(style=style):
                self.brief = copy.deepcopy(original)
                self.brief['style'] = style
                with self.assertRaises(figure.Invalid):
                    figure.load(self.save())
        self.brief = copy.deepcopy(original)
        self.brief['allowed_style_changes'] = []
        self.brief['style'] = {'width_mm': 140}
        with self.assertRaises(figure.Invalid):
            figure.load(self.save())

    def test_unsupported_processing_stops(self):
        for method in ['smooth', 'sort', 'resample', 'drop_missing', 'convert_units']:
            with self.subTest(method=method):
                self.brief['processing'] = {'method': method}
                with self.assertRaises(figure.Invalid):
                    figure.render(self.save(), self.root/'unsupported')
                self.assertFalse((self.root/'unsupported').exists())

    def test_missing_font_and_long_text_fail_without_output(self):
        original = copy.deepcopy(self.brief)
        for style in [{'font': 'SFO Deliberately Missing Font 20261109'},
                      {'colors': ['#ffffff', '#eeeeee']}]:
            self.brief = copy.deepcopy(original)
            self.brief['style'] = style
            out = self.root/'bad-render'
            self.assert_cli_failure(self.cli('render', self.save(), '--out', out))
            self.assertFalse(out.exists())
        self.brief = copy.deepcopy(original)
        self.brief['x']['label'] = 'Very long horizontal axis label '*40
        out = self.root/'long-text'
        with self.assertRaises(figure.Invalid):
            figure.render(self.save(), out)
        self.assertFalse(out.exists())
        self.assertFalse(list(self.root.glob('.sfo-*')))

    def test_constant_negative_scientific_and_source_bytes(self):
        self.brief['series'] = self.brief['series'][:1]
        self.data = ('displacement,force_a,force_b\n'
                     '-2e-3,-5e-2,0\n-1e-3,-5e-2,0\n0,-5e-2,0\n2e-3,-5e-2,0\n')
        brief = self.save()
        before = (self.root/'input.csv').read_bytes()
        out = self.root/'constant-negative'
        figure.render(brief, out)
        self.assertEqual((self.root/'input.csv').read_bytes(), before)
        self.assertEqual((out/'source.csv').read_bytes(), before)
        self.assertEqual(figure.verify(out)['status'], 'PASS')
        self.data = 'displacement,force_a,force_b\n1,2,0\n1,3,0\n1,4,0\n'
        self.assertEqual(len(figure.load(self.save())[3][0]), 3)

    def test_reverse_duplicate_points_survive_export(self):
        self.data = 'displacement,force_a,force_b\n0,-1,1\n2,3,-3\n1,2,-2\n1,2,-2\n3,0,0\n'
        brief = self.save()
        _, _, _, arrays, notices = figure.load(brief)
        self.assertEqual(arrays[0], [0, 2, 1, 1, 3])
        self.assertTrue(notices)
        out = self.root/'reverse'
        figure.render(brief, out)
        self.assertEqual(figure.verify(out)['status'], 'PASS')
        audit = json.loads((out/'audit.json').read_text(encoding='utf-8'))
        self.assertEqual(audit['point_count_per_series'], 5)
        self.assertEqual(audit['human_review']['status'], 'PENDING')

    def test_required_delivery_files_missing_never_pass(self):
        base = self.root/'base'
        figure.render(self.save(), base)
        required = ['figure.svg', 'figure.pdf', 'figure.png', 'source.csv', 'brief.json',
                    'figure.py', 'requirements.txt', 'REPRODUCE.md', 'final-size.png',
                    'grayscale.png', 'verification.json', 'audit.json']
        for index, name in enumerate(required):
            with self.subTest(file=name):
                out = self.root/f'missing-{index}'
                shutil.copytree(base, out)
                (out/name).unlink()
                result = self.cli('verify', out)
                self.assert_cli_failure(result)

    def test_png_dpi_readback_not_just_pixel_dimensions(self):
        from PIL import Image
        out = self.root/'dpi'
        figure.render(self.save(), out)
        for name in ['figure.png', 'final-size.png', 'grayscale.png']:
            with self.subTest(file=name):
                original = (out/name).read_bytes()
                with Image.open(out/name) as image:
                    image.load()
                    image.save(out/name, dpi=(72, 72))
                audit = json.loads((out/'audit.json').read_text(encoding='utf-8'))
                audit['hashes'][name] = figure.sha(out/name)
                (out/'audit.json').write_text(json.dumps(audit), encoding='utf-8')
                with self.assertRaises(figure.Invalid):
                    figure.verify(out)
                (out/name).write_bytes(original)
                audit['hashes'][name] = figure.sha(out/name)
                (out/'audit.json').write_text(json.dumps(audit), encoding='utf-8')

    def test_existing_output_is_preserved(self):
        out = self.root/'already-there'
        out.mkdir()
        marker = out/'keep.txt'
        marker.write_text('untouched', encoding='utf-8')
        with self.assertRaises(figure.Invalid):
            figure.render(self.save(), out)
        self.assertEqual(marker.read_text(encoding='utf-8'), 'untouched')
        self.assertEqual(list(out.iterdir()), [marker])

    def test_export_failure_cleans_stage_and_figures(self):
        import matplotlib.pyplot as plt
        from matplotlib.figure import Figure
        brief = self.save()
        before = plt.get_fignums()
        with mock.patch.object(Figure, 'savefig', side_effect=OSError('injected export failure')):
            with self.assertRaises(OSError):
                figure.render(brief, self.root/'failed-export')
        self.assertFalse((self.root/'failed-export').exists())
        self.assertFalse(list(self.root.glob('.sfo-*')))
        self.assertEqual(plt.get_fignums(), before)

    def test_float_precision_collapse_and_underflow_rejected_without_edit(self):
        for values in [('9007199254740992', '9007199254740993'), ('0', '1e-999')]:
            with self.subTest(values=values):
                self.data = ('displacement,force_a,force_b\n'
                             f'0,{values[0]},0\n1,{values[1]},1\n')
                brief = self.save()
                before = (self.root/'input.csv').read_bytes()
                with self.assertRaises(figure.Invalid):
                    figure.load(brief)
                self.assertEqual((self.root/'input.csv').read_bytes(), before)

    def test_reproduction_font_hash_mismatch_stops(self):
        self.brief['font_sha256'] = '0'*64
        out = self.root/'wrong-font'
        with self.assertRaises(figure.Invalid):
            figure.render(self.save(), out)
        self.assertFalse(out.exists())
        self.assertFalse(list(self.root.glob('.sfo-*')))

    def test_svg_geometry_and_path_commands_checked_beyond_hash(self):
        base = self.root/'geometry-base'
        figure.render(self.save(), base)
        ns = {'s': 'http://www.w3.org/2000/svg'}
        for case in ['clip', 'first_command', 'vertex']:
            with self.subTest(case=case):
                out = self.root/f'geometry-{case}'
                shutil.copytree(base, out)
                svg = out/'figure.svg'
                tree = ET.parse(svg)
                root = tree.getroot()
                path = root.find('.//s:g[@id="series-0"]/s:path', ns)
                self.assertIsNotNone(path)
                if case == 'clip':
                    rect = root.find('.//s:clipPath/s:rect', ns)
                    self.assertIsNotNone(rect)
                    rect.set('width', str(float(rect.attrib['width'])/4))
                elif case == 'first_command':
                    path.set('d', path.attrib['d'].replace('M', 'L', 1))
                else:
                    path.set('d', re.sub(r'([-+]?(?:\d*\.\d+|\d+\.?\d*))',
                                        lambda m: str(float(m.group())+5),
                                        path.attrib['d'], count=1))
                tree.write(svg, encoding='utf-8')
                audit = json.loads((out/'audit.json').read_text(encoding='utf-8'))
                audit['hashes']['figure.svg'] = figure.sha(svg)
                (out/'audit.json').write_text(json.dumps(audit), encoding='utf-8')
                with self.assertRaises(figure.Invalid):
                    figure.verify(out)

    def test_deleting_manifest_entry_cannot_hide_missing_required_file(self):
        out = self.root/'missing-manifest-entry'
        figure.render(self.save(), out)
        audit = json.loads((out/'audit.json').read_text(encoding='utf-8'))
        del audit['hashes']['figure.py']
        (out/'figure.py').unlink()
        (out/'audit.json').write_text(json.dumps(audit), encoding='utf-8')
        self.assert_cli_failure(self.cli('verify', out))

    def test_cli_verification_failure_invalidates_previous_pass(self):
        out = self.root/'stale-pass'
        figure.render(self.save(), out)
        report = out/'verification.json'
        self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['status'], 'PASS')
        (out/'figure.svg').write_bytes((out/'figure.svg').read_bytes()+b'\n<!-- changed -->')
        self.assert_cli_failure(self.cli('verify', out))
        self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
