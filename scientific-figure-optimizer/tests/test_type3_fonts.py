"""Embedded Type3 regressions; no Origin import or application startup."""
import importlib.util
import os
from pathlib import Path
import unittest

from pypdf import PdfReader
from pypdf.generic import (ArrayObject, BooleanObject, DecodedStreamObject,
                          DictionaryObject, FloatObject, NameObject, NumberObject)

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('type3_test_core', ROOT/'scripts/figure.py')
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)


def stream(program):
    result = DecodedStreamObject()
    result.set_data(program)
    return result


def values(items):
    return ArrayObject([NumberObject(x) if isinstance(x, int) else FloatObject(x) for x in items])


def fixture():
    font = DictionaryObject({
        NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type3'),
        NameObject('/FontBBox'): values([0, 0, 500, 700]),
        NameObject('/FontMatrix'): values([.001, 0, 0, .001, 0, 0]),
        NameObject('/FirstChar'): NumberObject(32), NameObject('/LastChar'): NumberObject(33),
        NameObject('/Widths'): values([250, 500]),
        NameObject('/Encoding'): DictionaryObject({NameObject('/Differences'): ArrayObject([
            NumberObject(32), NameObject('/space'), NameObject('/mark')])}),
        NameObject('/CharProcs'): DictionaryObject({
            NameObject('/space'): stream(b'250 0 d0'),
            NameObject('/mark'): stream(b'500 0 0 0 500 700 d1 0 0 500 700 re f')})})
    resources = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
    return resources, font


class Type3FontTests(unittest.TestCase):
    def check(self, resources):
        return core.embedded_pdf_fonts(resources)

    def assert_rejected(self, resources):
        with self.assertRaises(core.Invalid):
            self.check(resources)

    def test_charprocs_embeds_font_without_fontdescriptor_and_allows_spacing_glyph(self):
        resources, font = fixture()
        self.assertNotIn('/FontDescriptor', font)
        self.assertEqual(self.check(resources), 1)

    def test_missing_empty_or_nonstream_charprocs_rejected(self):
        for mode in ['missing', 'empty', 'nonstream', 'missing_encoded_glyph']:
            with self.subTest(mode=mode):
                resources, font = fixture()
                if mode == 'missing': del font['/CharProcs']
                elif mode == 'empty': font[NameObject('/CharProcs')] = DictionaryObject()
                elif mode == 'nonstream': font['/CharProcs'][NameObject('/mark')] = DictionaryObject()
                else: del font['/CharProcs']['/mark']
                self.assert_rejected(resources)

    def test_empty_or_malformed_glyph_metrics_rejected(self):
        for program in [b'', b'500 d0', b'500 0 0 0 d1', b'0 0 m 500 0 d0', b'500 0 d2']:
            with self.subTest(program=program):
                resources, font = fixture()
                font['/CharProcs'][NameObject('/mark')] = stream(program)
                self.assert_rejected(resources)

    def test_missing_and_unsupported_encoding_rejected(self):
        for encoding in [None, NameObject('/WinAnsiEncoding'), DictionaryObject(),
                         DictionaryObject({NameObject('/Differences'): ArrayObject()})]:
            with self.subTest(encoding=str(encoding)):
                resources, font = fixture()
                if encoding is None: del font['/Encoding']
                else: font[NameObject('/Encoding')] = encoding
                self.assert_rejected(resources)

    def test_encoding_duplicates_bad_names_or_out_of_range_rejected(self):
        for sequence in [[NameObject('/space')], [NumberObject(32), NumberObject(500)],
                         [NumberObject(32), NameObject('/space'), NumberObject(32), NameObject('/mark')],
                         [NumberObject(255), NameObject('/space')], [NumberObject(32), BooleanObject(True)]]:
            with self.subTest(sequence=str(sequence)):
                resources, font = fixture()
                font['/Encoding'][NameObject('/Differences')] = ArrayObject(sequence)
                self.assert_rejected(resources)

    def test_required_metrics_and_width_array_structure_rejected(self):
        invalid = [('/Widths', values([250])),
                   ('/FirstChar', NumberObject(-1)), ('/LastChar', NumberObject(256)),
                   ('/FirstChar', BooleanObject(True)), ('/FontBBox', values([0, 0])),
                   ('/FontMatrix', values([0, 0, 0, 0, 0, 0])),
                   ('/FontMatrix', values([float('inf'), 0, 0, .001, 0, 0]))]
        for index, (name, value) in enumerate(invalid):
            with self.subTest(name=name, case=index):
                resources, font = fixture()
                font[NameObject(name)] = value
                self.assert_rejected(resources)

    def test_glyph_named_resources_must_exist(self):
        for program in [b'500 0 d0 /Missing Do', b'500 0 d0 /Missing gs',
                        b'500 0 d0 /Missing 12 Tf', b'500 0 d0 /Missing sh',
                        b'500 0 d0 /Missing cs']:
            with self.subTest(program=program):
                resources, font = fixture()
                font['/CharProcs'][NameObject('/mark')] = stream(program)
                self.assert_rejected(resources)

    def test_glyph_resources_can_be_font_local_or_inherited(self):
        for local in [False, True]:
            with self.subTest(local=local):
                resources, font = fixture()
                ext = DictionaryObject({NameObject('/GS'): DictionaryObject()})
                target = DictionaryObject() if local else resources
                target[NameObject('/ExtGState')] = ext
                if local: font[NameObject('/Resources')] = target
                font['/CharProcs'][NameObject('/mark')] = stream(b'500 0 d0 /GS gs /DeviceRGB cs')
                self.assertEqual(self.check(resources), 1)

    def test_nested_form_and_shared_cyclic_resources_terminate(self):
        resources, _ = fixture()
        top = DictionaryObject({NameObject('/XObject'): DictionaryObject({NameObject('/Form'):
            DictionaryObject({NameObject('/Resources'): resources})})})
        resources[NameObject('/XObject')] = DictionaryObject({NameObject('/Cycle'):
            DictionaryObject({NameObject('/Resources'): top})})
        self.assertEqual(self.check(top), 1)
        self.assertEqual(self.check(DictionaryObject()), 0)

    def test_typetwo_glyph_missing_font_program_still_rejected(self):
        resources, _ = fixture()
        resources['/Font'][NameObject('/TT')] = DictionaryObject({NameObject('/Subtype'): NameObject('/TrueType')})
        self.assert_rejected(resources)

    def test_real_origin_pdf_type3_and_truetype_resources(self):
        supplied = os.environ.get('SFO_NATIVE_TYPE3_PDF')
        if not supplied: self.skipTest('Optional actual-export check: set SFO_NATIVE_TYPE3_PDF')
        fixture_path = Path(supplied)
        self.assertTrue(fixture_path.is_file(), 'Supplied native PDF fixture does not exist')
        pdf = PdfReader(fixture_path)
        self.assertEqual(len(pdf.pages), 1)
        self.assertEqual(self.check(pdf.pages[0]['/Resources']), 6)


if __name__ == '__main__': unittest.main()
