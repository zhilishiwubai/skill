"""Read actual generated PDFs with fonts moved into nested Form resources."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pdf_resource_core', ROOT/'scripts/figure.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class PdfResourceTests(unittest.TestCase):
    def nested_delivery(self, root, strip_font=False):
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        output = root/'output'
        core.render(ROOT/'assets/brief-template.json', output)
        reader = PdfReader(output/'figure.pdf')
        writer = PdfWriter()
        page = writer.add_page(reader.pages[0])
        resources = page['/Resources']
        if strip_font:
            for font in resources['/Font'].values():
                font = font.get_object()
                for descendant in font.get('/DescendantFonts', [font]):
                    descriptor = descendant.get_object()['/FontDescriptor'].get_object()
                    for key in ['/FontFile', '/FontFile2', '/FontFile3']:
                        if key in descriptor: del descriptor[key]
        form = DecodedStreamObject()
        form.set_data(page.get_contents().get_data())
        form.update({NameObject('/Type'):NameObject('/XObject'), NameObject('/Subtype'):NameObject('/Form'),
                     NameObject('/BBox'):page.mediabox, NameObject('/Resources'):resources})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/XObject'):DictionaryObject({NameObject('/Fm'):writer._add_object(form)})})
        content = DecodedStreamObject(); content.set_data(b'q /Fm Do Q')
        page[NameObject('/Contents')] = writer._add_object(content)
        with (output/'nested.pdf').open('wb') as stream: writer.write(stream)
        (output/'nested.pdf').replace(output/'figure.pdf')
        audit = core.read_json(output/'audit.json')
        audit['hashes']['figure.pdf'] = core.sha(output/'figure.pdf')
        core.write_json(output/'audit.json', audit)
        return output

    def test_real_nested_embedded_fonts_pass_full_readback(self):
        with tempfile.TemporaryDirectory() as folder:
            output = self.nested_delivery(Path(folder))
            self.assertEqual(core.verify(output)['status'], 'PASS')

    def test_nested_unembedded_font_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            output = self.nested_delivery(Path(folder), strip_font=True)
            with self.assertRaisesRegex(core.Invalid, 'not embedded'):
                core.verify(output)

    def test_empty_and_cyclic_resources_terminate_without_font_claim(self):
        from pypdf.generic import DictionaryObject, NameObject
        resources = DictionaryObject()
        self.assertEqual(core.embedded_pdf_fonts(resources), 0)
        resources[NameObject('/XObject')] = DictionaryObject({NameObject('/Loop'):DictionaryObject({NameObject('/Resources'):resources})})
        self.assertEqual(core.embedded_pdf_fonts(resources), 0)


if __name__ == '__main__': unittest.main()
