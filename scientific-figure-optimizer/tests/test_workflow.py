"""Check observable invariants, rejected scientific changes and exported readback."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('figure', ROOT/'scripts/figure.py')
figure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(figure)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.brief = json.loads((ROOT/'examples/spring.json').read_text())
        self.brief['input'] = 'input.csv'
        self.data = 'displacement,force_a,force_b\n0,0,0\n1,2,3\n2,4,6\n'

    def save(self):
        (self.root/'input.csv').write_text(self.data, encoding='utf-8')
        p = self.root/'brief.json'
        p.write_text(json.dumps(self.brief), encoding='utf-8')
        return p

    def test_reject_bad_input(self):
        for value in ['', 'NA', 'NaN', 'inf']:
            with self.subTest(value=value):
                self.data = f'displacement,force_a,force_b\n0,0,0\n1,{value},3\n'
                with self.assertRaises(figure.Invalid):
                    figure.load(self.save())

    def test_missing_unit(self):
        del self.brief['x']['unit']
        with self.assertRaises(figure.Invalid):
            figure.load(self.save())

    def test_scientific_change_rejected(self):
        for change in [{'processing': {'method': 'smooth'}}, {'style': {'xlim': [0, 1]}},
                       {'style': {'unit_conversion': 1000}}, {'style': {'colors': ['#ffffff', '#eeeeee']}}]:
            with self.subTest(change=change):
                original = copy.deepcopy(self.brief)
                self.brief.update(change)
                with self.assertRaises(figure.Invalid):
                    figure.render(self.save(), self.root/'invalid')
                self.assertFalse((self.root/'invalid').exists())
                self.brief = original

    def test_unknown_field_and_unauthorized_style(self):
        self.brief['smoothing'] = True
        with self.assertRaises(figure.Invalid):
            figure.load(self.save())
        del self.brief['smoothing']
        self.brief['allowed_style_changes'] = []
        self.brief['style'] = {'width_mm': 130}
        with self.assertRaises(figure.Invalid):
            figure.load(self.save())

    def test_preserve_unsorted_duplicates_and_tamper(self):
        self.data = 'displacement,force_a,force_b\n0,0,0\n2,4,6\n1,2,3\n1,2,3\n'
        p = self.save()
        original = (self.root/'input.csv').read_bytes()
        figure.render(p, self.root/'result')
        self.assertEqual((self.root/'result/source.csv').read_bytes(), original)
        self.assertEqual(figure.verify(self.root/'result')['status'], 'PASS')
        with self.assertRaises(figure.Invalid):
            figure.render(p, self.root/'result')
        path = self.root/'result/figure.svg'
        path.write_bytes(path.read_bytes()+b'\n<!-- edit -->')
        with self.assertRaises(figure.Invalid):
            figure.verify(self.root/'result')

    def test_long_note_fails_cleanly(self):
        self.brief['note'] = 'oversized annotation '*50
        with self.assertRaises(figure.Invalid):
            figure.render(self.save(), self.root/'bad-layout')
        self.assertFalse((self.root/'bad-layout').exists())

    def test_reference_status_required(self):
        self.brief['reference_lines'] = [{'x': 1, 'label': 'B1', 'source': 'teaching'}]
        with self.assertRaises(figure.Invalid):
            figure.load(self.save())

    def test_missing_column_and_ragged_csv(self):
        for data in ['wrong,force_a,force_b\n0,0,0\n1,2,3\n',
                     'displacement,force_a,force_b\n0,0,0\n1,2\n']:
            self.data = data
            with self.assertRaises(figure.Invalid):
                figure.load(self.save())

    def test_multiline_note_and_reference_readback(self):
        self.brief['note'] = 'Teaching curve\nReference is unvalidated\nNo physical transition claim'
        self.brief['reference_lines'] = [{'x': 1, 'label': 'R1', 'source': 'teaching', 'status': 'unvalidated'}]
        out = self.root/'reference-result'
        figure.render(self.save(), out)
        self.assertEqual(figure.verify(out)['status'], 'PASS')
        # Bypass the simple file hash to exercise geometric readback itself.
        svg = out/'figure.svg'
        import xml.etree.ElementTree as ET
        tree = ET.parse(svg)
        ns = {'s': 'http://www.w3.org/2000/svg'}
        path = tree.getroot().find('.//s:g[@id="reference-0"]/s:path', ns)
        path.set('d', 'M 0 0 L 0 100')
        tree.write(svg, encoding='utf-8')
        audit = json.loads((out/'audit.json').read_text())
        audit['hashes']['figure.svg'] = figure.sha(svg)
        (out/'audit.json').write_text(json.dumps(audit))
        with self.assertRaises(figure.Invalid):
            figure.verify(out)


if __name__ == '__main__':
    unittest.main()
