import codecs
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from file_view import ChangedOnDisk, Files, save, version


class EditorTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.file = self.root / 'source'

    def test_competing_edits_preserve_one_complete_revision(self):
        self.file.write_text('original')
        tag = version(self.file.read_bytes())

        def write(text):
            try:
                save(self.file, tag, text)
                return text
            except ChangedOnDisk:
                return None

        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(write, ['first', 'second']))
        self.assertCountEqual(results, [None, self.file.read_text()])

    def test_preserves_encoding_and_executable_bits(self):
        original = codecs.BOM_UTF16_BE + 'café\r\n'.encode('utf-16-be')
        self.file.write_bytes(original)
        self.file.chmod(0o751)
        save(self.file, version(original), 'thé\r\n')
        self.assertEqual(self.file.read_bytes(), codecs.BOM_UTF16_BE + 'thé\r\n'.encode('utf-16-be'))
        self.assertEqual(self.file.stat().st_mode & 0o777, 0o751)

    def test_only_explicit_staging_links_can_leave_root(self):
        self.file.write_text('text')
        stage = self.root / 'stage'
        stage.mkdir()
        (stage / 'selected').symlink_to(self.file)
        self.assertFalse(Files(stage, staged=False).editable('selected'))
        files = Files(stage, staged=True)
        self.assertTrue(files.editable('selected'))
        (stage / 'late').symlink_to(self.file)
        self.assertFalse(files.editable('late'))
        self.assertFalse(files.editable('../source'))
        self.file.write_bytes(b'data\x00')
        self.assertFalse(files.editable('selected'))
