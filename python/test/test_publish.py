import contextlib
import locale
import unittest

import mock

from publish import *
from publish.junit import parse_junit_xml_files
from publish.unittestresults import get_stats, UnitTestCase, ParseError
from publish.unittestresults import get_test_results
from test import d, n


@contextlib.contextmanager
def temp_locale(encoding: str) -> Any:
    old_locale = locale.getlocale()
    encodings = [
        f'{encoding}.utf8', f'{encoding}.utf-8',
        f'{encoding}.UTF8', f'{encoding}.UTF-8',
        encoding
    ]

    locale_set = False
    for encoding in encodings:
        try:
            locale.setlocale(locale.LC_ALL, encoding)
            locale_set = True
            break
        except:
            pass

    if not locale_set:
        raise ValueError(f'Could not set any of these locale: {", ".join(encodings)}')

    try:
        res = yield
    finally:
        locale.setlocale(locale.LC_ALL, old_locale)
    return res


errors = [ParseError('file', 'error', 1, 2)]


class PublishTest(unittest.TestCase):
    old_locale = None

    def test_test_changes(self):
        changes = SomeTestChanges(['removed-test', 'removed-skip', 'remain-test', 'remain-skip', 'skip', 'unskip'],
                                  ['remain-test', 'remain-skip', 'skip', 'unskip', 'add-test', 'add-skip'],
                                  ['removed-skip', 'remain-skip', 'unskip'], ['remain-skip', 'skip', 'add-skip'])
        self.assertEqual({'add-test', 'add-skip'}, changes.adds())
        self.assertEqual({'removed-test', 'removed-skip'}, changes.removes())
        self.assertEqual({'remain-test', 'remain-skip', 'skip', 'unskip'}, changes.remains())
        self.assertEqual({'skip', 'add-skip'}, changes.skips())
        self.assertEqual({'unskip', 'removed-skip'}, changes.un_skips())
        self.assertEqual({'add-skip'}, changes.added_and_skipped())
        self.assertEqual({'skip'}, changes.remaining_and_skipped())
        self.assertEqual({'unskip'}, changes.remaining_and_un_skipped())
        self.assertEqual({'removed-skip'}, changes.removed_skips())

    def test_test_changes_empty(self):
        changes = SomeTestChanges([], [], [], [])
        self.assertEqual(set(), changes.adds())
        self.assertEqual(set(), changes.removes())
        self.assertEqual(set(), changes.remains())
        self.assertEqual(set(), changes.skips())
        self.assertEqual(set(), changes.un_skips())
        self.assertEqual(set(), changes.added_and_skipped())
        self.assertEqual(set(), changes.remaining_and_skipped())
        self.assertEqual(set(), changes.remaining_and_un_skipped())
        self.assertEqual(set(), changes.removed_skips())

    def test_test_changes_with_nones(self):
        self.do_test_test_changes_with_nones(SomeTestChanges(None, None, None, None))
        self.do_test_test_changes_with_nones(SomeTestChanges(['test'], None, None, None))
        self.do_test_test_changes_with_nones(SomeTestChanges(None, ['test'], None, None))
        self.do_test_test_changes_with_nones(SomeTestChanges(None, None, ['test'], None))
        self.do_test_test_changes_with_nones(SomeTestChanges(None, None, None, ['test']))
        self.do_test_test_changes_with_nones(SomeTestChanges(['test'], None, ['test'], None))
        self.do_test_test_changes_with_nones(SomeTestChanges(None, ['test'], None, ['test']))
        self.do_test_test_changes_with_nones(SomeTestChanges(None, ['test'], ['test'], None))
        self.do_test_test_changes_with_nones(SomeTestChanges(['test'], None, None, ['test']))

    def do_test_test_changes_with_nones(self, changes: SomeTestChanges):
        self.assertIsNone(changes.adds())
        self.assertIsNone(changes.removes())
        self.assertIsNone(changes.remains())
        self.assertIsNone(changes.skips())
        self.assertIsNone(changes.un_skips())
        self.assertIsNone(changes.added_and_skipped())
        self.assertIsNone(changes.remaining_and_skipped())
        self.assertIsNone(changes.remaining_and_un_skipped())
        self.assertIsNone(changes.removed_skips())

    def test_abbreviate_characters(self):
        # None string
        self.assertIsNone(abbreviate(None, 1))

        # 1 byte utf8 characters
        self.assertEqual('', abbreviate('', 1))
        self.assertEqual('…', abbreviate('…', 1))
        self.assertEqual('ab', abbreviate('ab', 3))
        self.assertEqual('ab', abbreviate('ab', 2))
        self.assertEqual('…', abbreviate('ab', 1))
        self.assertEqual('abc', abbreviate('abc', 4))
        self.assertEqual('abc', abbreviate('abc', 3))
        self.assertEqual('a…', abbreviate('abc', 2))
        self.assertEqual('…', abbreviate('abc', 1))
        self.assertEqual('abcd', abbreviate('abcd', 4))
        self.assertEqual('a…d', abbreviate('abcd', 3))
        self.assertEqual('a…', abbreviate('abcd', 2))
        self.assertEqual('…', abbreviate('abcd', 1))
        self.assertEqual('abcde', abbreviate('abcde', 5))
        self.assertEqual('ab…e', abbreviate('abcde', 4))
        self.assertEqual('a…e', abbreviate('abcde', 3))
        self.assertEqual('a…', abbreviate('abcde', 2))
        self.assertEqual('…', abbreviate('abcde', 1))
        self.assertEqual('abcdef', abbreviate('abcdef', 6))
        self.assertEqual('ab…ef', abbreviate('abcdef', 5))
        self.assertEqual('ab…f', abbreviate('abcdef', 4))
        self.assertEqual('a…f', abbreviate('abcdef', 3))
        self.assertEqual('a…', abbreviate('abcdef', 2))
        self.assertEqual('…', abbreviate('abcdef', 1))
        self.assertEqual('abcdefg', abbreviate('abcdefg', 7))
        self.assertEqual('abc…fg', abbreviate('abcdefg', 6))
        self.assertEqual('ab…fg', abbreviate('abcdefg', 5))
        self.assertEqual('ab…g', abbreviate('abcdefg', 4))
        self.assertEqual('a…g', abbreviate('abcdefg', 3))
        self.assertEqual('a…', abbreviate('abcdefg', 2))
        self.assertEqual('…', abbreviate('abcdefg', 1))
        self.assertEqual('abcdefgh', abbreviate('abcdefgh', 8))
        self.assertEqual('abc…fgh', abbreviate('abcdefgh', 7))
        self.assertEqual('abc…gh', abbreviate('abcdefgh', 6))
        self.assertEqual('ab…gh', abbreviate('abcdefgh', 5))
        self.assertEqual('ab…h', abbreviate('abcdefgh', 4))
        self.assertEqual('a…h', abbreviate('abcdefgh', 3))
        self.assertEqual('a…', abbreviate('abcdefgh', 2))
        self.assertEqual('…', abbreviate('abcdefgh', 1))
        self.assertEqual('abcdefghijklmnopqrstuvwxyz', abbreviate('abcdefghijklmnopqrstuvwxyz', 27))
        self.assertEqual('abcdefghijklmnopqrstuvwxyz', abbreviate('abcdefghijklmnopqrstuvwxyz', 26))
        self.assertEqual('abcdefghijkl…opqrstuvwxyz', abbreviate('abcdefghijklmnopqrstuvwxyz', 25))

        # 2 bytes utf8 characters
        self.assertEqual('»»»»»', abbreviate('»»»»»', 5))
        self.assertEqual('»»…»', abbreviate('»»»»»', 4))
        self.assertEqual('»…»', abbreviate('»»»»»', 3))
        self.assertEqual('»…', abbreviate('»»»»»', 2))
        self.assertEqual('…', abbreviate('»»»»»', 1))
        self.assertEqual('»»»»»»', abbreviate('»»»»»»', 6))
        self.assertEqual('»»…»»', abbreviate('»»»»»»', 5))
        self.assertEqual('»»…»', abbreviate('»»»»»»', 4))
        self.assertEqual('»…»', abbreviate('»»»»»»', 3))
        self.assertEqual('»…', abbreviate('»»»»»»', 2))
        self.assertEqual('…', abbreviate('»»»»»»', 1))

        # 3 bytes utf8 characters
        self.assertEqual('▊▋▌▍▎', abbreviate('▊▋▌▍▎', 5))
        self.assertEqual('▊▋…▎', abbreviate('▊▋▌▍▎', 4))
        self.assertEqual('▊…▎', abbreviate('▊▋▌▍▎', 3))
        self.assertEqual('▊…', abbreviate('▊▋▌▍▎', 2))
        self.assertEqual('…', abbreviate('▊▋▌▍▎', 1))
        self.assertEqual('▊▋▌▍▎▏', abbreviate('▊▋▌▍▎▏', 6))
        self.assertEqual('▊▋…▎▏', abbreviate('▊▋▌▍▎▏', 5))
        self.assertEqual('▊▋…▏', abbreviate('▊▋▌▍▎▏', 4))
        self.assertEqual('▊…▏', abbreviate('▊▋▌▍▎▏', 3))
        self.assertEqual('▊…', abbreviate('▊▋▌▍▎▏', 2))
        self.assertEqual('…', abbreviate('▊▋▌▍▎▏', 1))

        # 4 bytes utf8 characters
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', abbreviate('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 27))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', abbreviate('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 26))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍…𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', abbreviate('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 25))

        # mixed utf bytes: lengths=[1, 2, 3, 4, 1, 2, 3, 4]
        self.assertEqual('a»▉𝒂a»▉𝒂', abbreviate('a»▉𝒂a»▉𝒂', 9))
        self.assertEqual('a»▉𝒂a»▉𝒂', abbreviate('a»▉𝒂a»▉𝒂', 8))
        self.assertEqual('a»▉…»▉𝒂', abbreviate('a»▉𝒂a»▉𝒂', 7))
        self.assertEqual('a»▉…▉𝒂', abbreviate('a»▉𝒂a»▉𝒂', 6))
        self.assertEqual('a»…▉𝒂', abbreviate('a»▉𝒂a»▉𝒂', 5))
        self.assertEqual('a»…𝒂', abbreviate('a»▉𝒂a»▉𝒂', 4))
        self.assertEqual('a…𝒂', abbreviate('a»▉𝒂a»▉𝒂', 3))
        self.assertEqual('a…', abbreviate('a»▉𝒂a»▉𝒂', 2))
        self.assertEqual('…', abbreviate('a»▉𝒂a»▉𝒂', 1))
        self.assertEqual('a»▉𝒂a»▉', abbreviate('a»▉𝒂a»▉', 8))
        self.assertEqual('a»▉𝒂a»▉', abbreviate('a»▉𝒂a»▉', 7))
        self.assertEqual('a»▉…»▉', abbreviate('a»▉𝒂a»▉', 6))
        self.assertEqual('a»…»▉', abbreviate('a»▉𝒂a»▉', 5))
        self.assertEqual('a»…▉', abbreviate('a»▉𝒂a»▉', 4))
        self.assertEqual('a…▉', abbreviate('a»▉𝒂a»▉', 3))
        self.assertEqual('a…', abbreviate('a»▉𝒂a»▉', 2))
        self.assertEqual('…', abbreviate('a»▉𝒂a»▉', 1))

        # invalid abbreviation lengths
        self.assertRaises(ValueError, lambda: abbreviate('abc', 0))
        self.assertRaises(ValueError, lambda: abbreviate('abc', -1))

    def test_abbreviate_bytes(self):
        # None string
        self.assertIsNone(abbreviate_bytes(None, 3))

        # even number of characters
        # 4 bytes utf characters
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 105))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 104))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎…𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 103))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍…𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 102))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍…𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 101))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍…𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 100))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍…𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 99))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍…𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 98))
        self.assertEqual('𝒂𝒃𝒄…𝒙𝒚𝒛', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 27))
        self.assertEqual('𝒂𝒃𝒄…𝒚𝒛', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 26))
        self.assertEqual('𝒂𝒃𝒄…𝒚𝒛', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 25))
        self.assertEqual('𝒂…', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 7))
        self.assertEqual('…', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 6))
        self.assertEqual('…', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 5))
        self.assertEqual('…', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 4))
        self.assertEqual('…', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛', 3))
        # 1 byte utf characters
        self.assertEqual('ab…yz', abbreviate_bytes('abcdefghijklmnopqrstuvwxyz', 7))
        self.assertEqual('ab…z', abbreviate_bytes('abcdefghijklmnopqrstuvwxyz', 6))
        self.assertEqual('a…z', abbreviate_bytes('abcdefghijklmnopqrstuvwxyz', 5))
        self.assertEqual('a…', abbreviate_bytes('abcdefghijklmnopqrstuvwxyz', 4))
        self.assertEqual('…', abbreviate_bytes('abcdefghijklmnopqrstuvwxyz', 3))
        # mixed utf bytes: lengths=[1, 2, 3, 4, 4, 3, 2, 1]
        self.assertEqual('a»▉𝒂𝒂▉»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 21))
        self.assertEqual('a»▉𝒂𝒂▉»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 20))
        self.assertEqual('a»▉𝒂…▉»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 19))
        self.assertEqual('a»▉…▉»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 18))
        self.assertEqual('a»▉…▉»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 17))
        self.assertEqual('a»▉…▉»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 16))
        self.assertEqual('a»▉…▉»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 15))
        self.assertEqual('a»▉…»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 14))
        self.assertEqual('a»▉…»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 13))
        self.assertEqual('a»▉…»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 12))
        self.assertEqual('a»…»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 11))
        self.assertEqual('a»…»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 10))
        self.assertEqual('a»…»a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 9))
        self.assertEqual('a»…a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 8))
        self.assertEqual('a»…a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 7))
        self.assertEqual('a…a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 6))
        self.assertEqual('a…a', abbreviate_bytes('a»▉𝒂𝒂▉»a', 5))
        self.assertEqual('a…', abbreviate_bytes('a»▉𝒂𝒂▉»a', 4))
        self.assertEqual('…', abbreviate_bytes('a»▉𝒂𝒂▉»a', 3))

        # odd number of characters
        # 4 bytes utf characters
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 101))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 100))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍…𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 99))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍…𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 98))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍…𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 97))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍…𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 96))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍…𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 95))
        self.assertEqual('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌…𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 94))
        self.assertEqual('𝒂𝒃𝒄…𝒘𝒙𝒚', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 27))
        self.assertEqual('𝒂𝒃𝒄…𝒙𝒚', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 26))
        self.assertEqual('𝒂𝒃𝒄…𝒙𝒚', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 25))
        self.assertEqual('𝒂…', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 7))
        self.assertEqual('…', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 6))
        self.assertEqual('…', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 5))
        self.assertEqual('…', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 4))
        self.assertEqual('…', abbreviate_bytes('𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚', 3))
        # 1 byte utf characters
        self.assertEqual('ab…xy', abbreviate_bytes('abcdefghijklmnopqrstuvwxy', 7))
        self.assertEqual('ab…y', abbreviate_bytes('abcdefghijklmnopqrstuvwxy', 6))
        self.assertEqual('a…y', abbreviate_bytes('abcdefghijklmnopqrstuvwxy', 5))
        self.assertEqual('a…', abbreviate_bytes('abcdefghijklmnopqrstuvwxy', 4))
        self.assertEqual('…', abbreviate_bytes('abcdefghijklmnopqrstuvwxy', 3))
        # mixed utf bytes: lengths=[1, 2, 3, 4, 1, 2, 3]
        self.assertEqual('a»▉𝒂a»▉', abbreviate_bytes('a»▉𝒂a»▉', 17))
        self.assertEqual('a»▉𝒂a»▉', abbreviate_bytes('a»▉𝒂a»▉', 16))
        self.assertEqual('a»▉…a»▉', abbreviate_bytes('a»▉𝒂a»▉', 15))
        self.assertEqual('a»▉…»▉', abbreviate_bytes('a»▉𝒂a»▉', 14))
        self.assertEqual('a»…»▉', abbreviate_bytes('a»▉𝒂a»▉', 13))
        self.assertEqual('a»…»▉', abbreviate_bytes('a»▉𝒂a»▉', 12))
        self.assertEqual('a»…»▉', abbreviate_bytes('a»▉𝒂a»▉', 11))
        self.assertEqual('a»…▉', abbreviate_bytes('a»▉𝒂a»▉', 10))
        self.assertEqual('a»…▉', abbreviate_bytes('a»▉𝒂a»▉', 9))
        self.assertEqual('a…▉', abbreviate_bytes('a»▉𝒂a»▉', 8))
        self.assertEqual('a…▉', abbreviate_bytes('a»▉𝒂a»▉', 7))
        self.assertEqual('a…', abbreviate_bytes('a»▉𝒂a»▉', 6))
        self.assertEqual('a…', abbreviate_bytes('a»▉𝒂a»▉', 5))
        self.assertEqual('a…', abbreviate_bytes('a»▉𝒂a»▉', 4))
        self.assertEqual('…', abbreviate_bytes('a»▉𝒂a»▉', 3))

        self.assertRaises(ValueError, lambda: abbreviate_bytes('abc', 2))
        self.assertRaises(ValueError, lambda: abbreviate_bytes('abc', 1))
        self.assertRaises(ValueError, lambda: abbreviate_bytes('abc', 0))
        self.assertRaises(ValueError, lambda: abbreviate_bytes('abc', -1))

    def test_get_test_name(self):
        self.assertEqual('Unknown test', get_test_name(None, None, None))
        self.assertEqual('test name', get_test_name(None, None, 'test name'))
        self.assertEqual('class name ‑ Unknown test', get_test_name(None, 'class name', None))
        self.assertEqual('class name ‑ test name', get_test_name(None, 'class name', 'test name'))
        self.assertEqual('file name ‑ Unknown test', get_test_name('file name', None, None))
        self.assertEqual('file name ‑ test name', get_test_name('file name', None, 'test name'))
        self.assertEqual('file name ‑ class name ‑ Unknown test', get_test_name('file name', 'class name', None))
        self.assertEqual('file name ‑ class name ‑ test name', get_test_name('file name', 'class name', 'test name'))

    def test_get_formatted_digits(self):
        self.assertEqual(get_formatted_digits(None), (3, 0))
        self.assertEqual(get_formatted_digits(None, 1), (3, 0))
        self.assertEqual(get_formatted_digits(None, 123), (3, 0))
        self.assertEqual(get_formatted_digits(None, 1234), (5, 0))
        self.assertEqual(get_formatted_digits(0), (1, 0))
        self.assertEqual(get_formatted_digits(1, 2, 3), (1, 0))
        self.assertEqual(get_formatted_digits(10), (2, 0))
        self.assertEqual(get_formatted_digits(100), (3, 0))
        self.assertEqual(get_formatted_digits(1234, 123, 0), (5, 0))
        with temp_locale('en_US'):
            self.assertEqual(get_formatted_digits(1234, 123, 0), (5, 0))
        with temp_locale('de_DE'):
            self.assertEqual(get_formatted_digits(1234, 123, 0), (5, 0))

        self.assertEqual(get_formatted_digits(dict()), (3, 3))
        self.assertEqual(get_formatted_digits(dict(number=1)), (1, 3))
        self.assertEqual(get_formatted_digits(dict(number=12)), (2, 3))
        self.assertEqual(get_formatted_digits(dict(number=123)), (3, 3))
        self.assertEqual(get_formatted_digits(dict(number=1234)), (5, 3))
        with temp_locale('en_US'):
            self.assertEqual(get_formatted_digits(dict(number=1234)), (5, 3))
        with temp_locale('de_DE'):
            self.assertEqual(get_formatted_digits(dict(number=1234)), (5, 3))

        self.assertEqual(get_formatted_digits(dict(delta=1)), (3, 1))
        self.assertEqual(get_formatted_digits(dict(number=1, delta=1)), (1, 1))
        self.assertEqual(get_formatted_digits(dict(number=1, delta=12)), (1, 2))
        self.assertEqual(get_formatted_digits(dict(number=1, delta=123)), (1, 3))
        self.assertEqual(get_formatted_digits(dict(number=1, delta=1234)), (1, 5))
        with temp_locale('en_US'):
            self.assertEqual(get_formatted_digits(dict(number=1, delta=1234)), (1, 5))
        with temp_locale('de_DE'):
            self.assertEqual(get_formatted_digits(dict(number=1, delta=1234)), (1, 5))

    def test_get_magnitude(self):
        self.assertEqual(None, get_magnitude(None))
        self.assertEqual(+0, get_magnitude(+0))
        self.assertEqual(-1, get_magnitude(-1))
        self.assertEqual(+2, get_magnitude(+2))
        self.assertEqual(None, get_magnitude(dict()))
        self.assertEqual(+0, get_magnitude(dict(number=+0)))
        self.assertEqual(+1, get_magnitude(dict(number=+1)))
        self.assertEqual(-2, get_magnitude(dict(number=-2)))
        self.assertEqual(3, get_magnitude(dict(number=3, delta=5)))
        self.assertEqual(3, get_magnitude(dict(duration=3)))
        self.assertEqual(3, get_magnitude(dict(duration=3, delta=5)))
        self.assertEqual(None, get_magnitude(dict(delta=5)))

    def test_get_delta(self):
        self.assertEqual(None, get_delta(None))
        self.assertEqual(None, get_delta(+0))
        self.assertEqual(None, get_delta(-1))
        self.assertEqual(None, get_delta(+2))
        self.assertEqual(None, get_delta(dict()))
        self.assertEqual(None, get_delta(dict(number=+0)))
        self.assertEqual(None, get_delta(dict(number=+1)))
        self.assertEqual(None, get_delta(dict(number=-2)))
        self.assertEqual(5, get_delta(dict(number=3, delta=5)))
        self.assertEqual(None, get_delta(dict(duration=3)))
        self.assertEqual(5, get_delta(dict(duration=3, delta=5)))
        self.assertEqual(5, get_delta(dict(delta=5)))

    def test_as_short_commit(self):
        self.assertEqual(as_short_commit(None), None)
        self.assertEqual(as_short_commit(''), None)
        self.assertEqual(as_short_commit('commit'), 'commit')
        self.assertEqual(as_short_commit('0123456789abcdef'), '01234567')
        self.assertEqual(as_short_commit('b469da3d223225fa3f014a3c9e9466b42a1471c5'), 'b469da3d')

    def test_as_delta(self):
        self.assertEqual(as_delta(0, 1), '±0')
        self.assertEqual(as_delta(+1, 1), '+1')
        self.assertEqual(as_delta(-2, 1), ' - 2')

        self.assertEqual(as_delta(0, 2), '±  0')
        self.assertEqual(as_delta(+1, 2), '+  1')
        self.assertEqual(as_delta(-2, 2), ' -   2')

        self.assertEqual(as_delta(1, 5), '+       1')
        self.assertEqual(as_delta(12, 5), '+     12')
        self.assertEqual(as_delta(123, 5), '+   123')
        self.assertEqual(as_delta(1234, 5), '+1 234')
        self.assertEqual(as_delta(1234, 6), '+  1 234')
        self.assertEqual(as_delta(123, 6), '+     123')

        with temp_locale('en_US'):
            self.assertEqual(as_delta(1234, 5), '+1 234')
            self.assertEqual(as_delta(1234, 6), '+  1 234')
            self.assertEqual(as_delta(123, 6), '+     123')
        with temp_locale('de_DE'):
            self.assertEqual(as_delta(1234, 5), '+1 234')
            self.assertEqual(as_delta(1234, 6), '+  1 234')
            self.assertEqual(as_delta(123, 6), '+     123')

    def test_as_stat_number(self):
        label = 'unit'
        self.assertEqual(as_stat_number(None, 1, 0, label), 'N/A unit')

        self.assertEqual(as_stat_number(1, 1, 0, label), '1 unit')
        self.assertEqual(as_stat_number(123, 6, 0, label), '     123 unit')
        self.assertEqual(as_stat_number(1234, 6, 0, label), '  1 234 unit')
        self.assertEqual(as_stat_number(12345, 6, 0, label), '12 345 unit')

        with temp_locale('en_US'):
            self.assertEqual(as_stat_number(123, 6, 0, label), '     123 unit')
            self.assertEqual(as_stat_number(1234, 6, 0, label), '  1 234 unit')
            self.assertEqual(as_stat_number(12345, 6, 0, label), '12 345 unit')
        with temp_locale('de_DE'):
            self.assertEqual(as_stat_number(123, 6, 0, label), '     123 unit')
            self.assertEqual(as_stat_number(1234, 6, 0, label), '  1 234 unit')
            self.assertEqual(as_stat_number(12345, 6, 0, label), '12 345 unit')

        self.assertEqual(as_stat_number(dict(number=1), 1, 0, label), '1 unit')

        self.assertEqual(as_stat_number(dict(number=1, delta=-1), 1, 1, label), '1 unit  - 1 ')
        self.assertEqual(as_stat_number(dict(number=2, delta=+0), 1, 1, label), '2 unit ±0 ')
        self.assertEqual(as_stat_number(dict(number=3, delta=+1), 1, 1, label), '3 unit +1 ')
        self.assertEqual(as_stat_number(dict(number=3, delta=+1), 1, 2, label), '3 unit +  1 ')
        self.assertEqual(as_stat_number(dict(number=3, delta=+1), 2, 2, label), '  3 unit +  1 ')
        self.assertEqual(as_stat_number(dict(number=3, delta=+1234), 1, 6, label), '3 unit +  1 234 ')
        self.assertEqual(as_stat_number(dict(number=3, delta=+12345), 1, 6, label), '3 unit +12 345 ')
        with temp_locale('en_US'):
            self.assertEqual(as_stat_number(dict(number=3, delta=+1234), 1, 6, label), '3 unit +  1 234 ')
            self.assertEqual(as_stat_number(dict(number=3, delta=+12345), 1, 6, label), '3 unit +12 345 ')
        with temp_locale('de_DE'):
            self.assertEqual(as_stat_number(dict(number=3, delta=+1234), 1, 6, label), '3 unit +  1 234 ')
            self.assertEqual(as_stat_number(dict(number=3, delta=+12345), 1, 6, label), '3 unit +12 345 ')

        self.assertEqual(as_stat_number(dict(delta=-1), 3, 1, label), 'N/A unit  - 1 ')

        self.assertEqual(as_stat_number(dict(number=1, delta=-2, new=3), 1, 1, label), '1 unit  - 2, 3 new ')
        self.assertEqual(as_stat_number(dict(number=2, delta=+0, new=3, gone=4), 1, 1, label), '2 unit ±0, 3 new, 4 gone ')
        self.assertEqual(as_stat_number(dict(number=3, delta=+1, gone=4), 1, 1, label), '3 unit +1, 4 gone ')

    def test_as_stat_duration(self):
        label = 'time'
        self.assertEqual(as_stat_duration(None, label), 'N/A time')
        self.assertEqual(as_stat_duration(0, None), '0s')
        self.assertEqual(as_stat_duration(0, label), '0s time')
        self.assertEqual(as_stat_duration(12, label), '12s time')
        self.assertEqual(as_stat_duration(72, label), '1m 12s time')
        self.assertEqual(as_stat_duration(3754, label), '1h 2m 34s time')
        self.assertEqual(as_stat_duration(-3754, label), '1h 2m 34s time')

        self.assertEqual(as_stat_duration(d(3754), label), '1h 2m 34s time')
        self.assertEqual(as_stat_duration(d(3754, 0), label), '1h 2m 34s time ±0s')
        self.assertEqual(as_stat_duration(d(3754, 1234), label), '1h 2m 34s time + 20m 34s')
        self.assertEqual(as_stat_duration(d(3754, -123), label), '1h 2m 34s time - 2m 3s')
        self.assertEqual(as_stat_duration(dict(delta=123), label), 'N/A time + 2m 3s')

    def test_get_stats_digest_undigest(self):
        digest = get_digest_from_stats(UnitTestRunResults(
            files=1, errors=[], suites=2, duration=3,
            tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
            runs=9, runs_succ=10, runs_skip=11, runs_fail=12, runs_error=13,
            commit='commit'
        ))
        self.assertTrue(isinstance(digest, str))
        self.assertTrue(len(digest) > 100)
        stats = get_stats_from_digest(digest)
        self.assertEqual(stats, UnitTestRunResults(
            files=1, errors=[], suites=2, duration=3,
            tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
            runs=9, runs_succ=10, runs_skip=11, runs_fail=12, runs_error=13,
            commit='commit'
        ))

    def test_digest_ungest_string(self):
        digest = digest_string('abc')
        self.assertTrue(isinstance(digest, str))
        self.assertTrue(len(digest) > 10)
        string = ungest_string(digest)
        self.assertEqual(string, 'abc')

    def test_get_stats_from_digest(self):
        self.assertEqual(
            get_stats_from_digest('H4sIAAAAAAAC/0XOwQ6CMBAE0F8hPXtgEVT8GdMUSDYCJdv2ZP'
                                  'x3psLW28zbZLIfM/E8BvOs6FKZkDj+SoMyJLGR/Yp6RcUh5lOr'
                                  '+RWSc4DuD2/eALcCk+UZcC8winiBPCCS1rzXn1HnqC5wzBEpnH'
                                  'PUKOgc5QedXxaOaJq+O+lMT3jdAAAA'),
            UnitTestRunResults(
                files=1, errors=[], suites=2, duration=3,
                tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
                runs=9, runs_succ=10, runs_skip=11, runs_fail=12, runs_error=13,
                commit='commit'
            )
        )

    def test_get_short_summary(self):
        self.assertEqual('No tests found', get_short_summary(UnitTestRunResults(files=0, errors=[], suites=0, duration=123, tests=0, tests_succ=0, tests_skip=0, tests_fail=0, tests_error=0, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))
        self.assertEqual('10 tests found in 2m 3s', get_short_summary(UnitTestRunResults(files=1, errors=[], suites=2, duration=123, tests=10, tests_succ=0, tests_skip=0, tests_fail=0, tests_error=0, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))
        self.assertEqual('All 10 tests pass in 2m 3s', get_short_summary(UnitTestRunResults(files=1, errors=[], suites=2, duration=123, tests=10, tests_succ=10, tests_skip=0, tests_fail=0, tests_error=0, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))
        self.assertEqual('All 9 tests pass, 1 skipped in 2m 3s', get_short_summary(UnitTestRunResults(files=1, errors=[], suites=2, duration=123, tests=10, tests_succ=9, tests_skip=1, tests_fail=0, tests_error=0, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))
        self.assertEqual('2 fail, 1 skipped, 7 pass in 2m 3s', get_short_summary(UnitTestRunResults(files=1, errors=[], suites=2, duration=123, tests=10, tests_succ=7, tests_skip=1, tests_fail=2, tests_error=0, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))
        self.assertEqual('3 errors, 2 fail, 1 skipped, 4 pass in 2m 3s', get_short_summary(UnitTestRunResults(files=1, errors=[], suites=2, duration=123, tests=10, tests_succ=4, tests_skip=1, tests_fail=2, tests_error=3, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))
        self.assertEqual('2 fail, 8 pass in 2m 3s', get_short_summary(UnitTestRunResults(files=1, errors=[], suites=2, duration=123, tests=10, tests_succ=8, tests_skip=0, tests_fail=2, tests_error=0, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))
        self.assertEqual('3 errors, 7 pass in 2m 3s', get_short_summary(UnitTestRunResults(files=1, errors=[], suites=2, duration=123, tests=10, tests_succ=7, tests_skip=0, tests_fail=0, tests_error=3, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))
        self.assertEqual('1 parse errors', get_short_summary(UnitTestRunResults(files=1, errors=errors, suites=0, duration=0, tests=0, tests_succ=0, tests_skip=0, tests_fail=0, tests_error=0, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))
        self.assertEqual('1 parse errors, 4 pass in 2m 3s', get_short_summary(UnitTestRunResults(files=2, errors=errors, suites=1, duration=123, tests=4, tests_succ=4, tests_skip=0, tests_fail=0, tests_error=0, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))
        self.assertEqual('1 parse errors, 1 skipped, 4 pass in 2m 3s', get_short_summary(UnitTestRunResults(files=2, errors=errors, suites=1, duration=123, tests=5, tests_succ=4, tests_skip=1, tests_fail=0, tests_error=0, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))
        self.assertEqual('1 parse errors, 2 fail, 1 skipped, 4 pass in 2m 3s', get_short_summary(UnitTestRunResults(files=2, errors=errors, suites=1, duration=123, tests=7, tests_succ=4, tests_skip=1, tests_fail=2, tests_error=0, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))
        self.assertEqual('1 parse errors, 3 errors, 2 fail, 1 skipped, 4 pass in 2m 3s', get_short_summary(UnitTestRunResults(files=2, errors=errors, suites=1, duration=123, tests=10, tests_succ=4, tests_skip=1, tests_fail=2, tests_error=3, runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0, commit='commit')))

    def test_get_short_summary_md(self):
        self.assertEqual(get_short_summary_md(UnitTestRunResults(
            files=1, errors=[], suites=2, duration=3,
            tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
            runs=9, runs_succ=10, runs_skip=11, runs_fail=12, runs_error=13,
            commit='commit'
        )), ('4 tests 5 :heavy_check_mark: 6 :zzz: 7 :x: 8 :fire:'))

    def test_get_short_summary_md_with_delta(self):
        self.assertEqual(get_short_summary_md(UnitTestRunDeltaResults(
            files=n(1, 2), errors=[], suites=n(2, -3), duration=d(3, 4),
            tests=n(4, -5), tests_succ=n(5, 6), tests_skip=n(6, -7), tests_fail=n(7, 8), tests_error=n(8, -9),
            runs=n(9, 10), runs_succ=n(10, -11), runs_skip=n(11, 12), runs_fail=n(12, -13), runs_error=n(13, 14),
            commit='commit',
            reference_type='type', reference_commit='0123456789abcdef'
        )), ('4 tests  - 5  5 :heavy_check_mark: +6  6 :zzz:  - 7  7 :x: +8  8 :fire:  - 9 '))

    def test_get_long_summary_md_with_single_runs(self):
        self.assertEqual(get_long_summary_md(UnitTestRunResults(
            files=1, errors=[], suites=2, duration=3,
            tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
            runs=4, runs_succ=5, runs_skip=6, runs_fail=7, runs_error=8,
            commit='commit'
        )), ('1 files  2 suites   3s :stopwatch:\n'
            '4 tests 5 :heavy_check_mark: 6 :zzz: 7 :x: 8 :fire:\n'
            '\n'
            'Results for commit commit.\n'))

    def test_get_long_summary_md_with_multiple_runs(self):
        self.assertEqual(get_long_summary_md(UnitTestRunResults(
            files=1, errors=[], suites=2, duration=3,
            tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=0,
            runs=9, runs_succ=10, runs_skip=11, runs_fail=12, runs_error=0,
            commit='commit'
        )), ('1 files    2 suites   3s :stopwatch:\n'
            '4 tests   5 :heavy_check_mark:   6 :zzz:   7 :x:\n'
            '9 runs  10 :heavy_check_mark: 11 :zzz: 12 :x:\n'
            '\n'
            'Results for commit commit.\n'))

    def test_get_long_summary_md_with_errors(self):
        self.assertEqual(get_long_summary_md(UnitTestRunResults(
            files=1, errors=[], suites=2, duration=3,
            tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
            runs=9, runs_succ=10, runs_skip=11, runs_fail=12, runs_error=13,
            commit='commit'
        )), ('1 files    2 suites   3s :stopwatch:\n'
            '4 tests   5 :heavy_check_mark:   6 :zzz:   7 :x:   8 :fire:\n'
            '9 runs  10 :heavy_check_mark: 11 :zzz: 12 :x: 13 :fire:\n'
            '\n'
            'Results for commit commit.\n'))

    def test_get_long_summary_md_with_deltas(self):
        self.assertEqual(get_long_summary_md(UnitTestRunDeltaResults(
            files=n(1, 2), errors=[], suites=n(2, -3), duration=d(3, 4),
            tests=n(4, -5), tests_succ=n(5, 6), tests_skip=n(6, -7), tests_fail=n(7, 8), tests_error=n(8, -9),
            runs=n(9, 10), runs_succ=n(10, -11), runs_skip=n(11, 12), runs_fail=n(12, -13), runs_error=n(13, 14),
            commit='123456789abcdef0', reference_type='type', reference_commit='0123456789abcdef'
        )), ('1 files  +  2    2 suites   - 3   3s :stopwatch: +4s\n'
            '4 tests  -   5    5 :heavy_check_mark: +  6    6 :zzz:  -   7    7 :x: +  8    8 :fire:  -   9 \n'
            '9 runs  +10  10 :heavy_check_mark:  - 11  11 :zzz: +12  12 :x:  - 13  13 :fire: +14 \n'
            '\n'
            'Results for commit 12345678. ± Comparison against type commit 01234567.\n'))

    def test_get_long_summary_md_with_details_url_with_fails(self):
        self.assertEqual(get_long_summary_md(
            UnitTestRunResults(
                files=1, errors=[], suites=2, duration=3,
                tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=0,
                runs=4, runs_succ=5, runs_skip=6, runs_fail=7, runs_error=0,
                commit='commit'
            ),
            'https://details.url/'
        ), ('1 files  2 suites   3s :stopwatch:\n'
            '4 tests 5 :heavy_check_mark: 6 :zzz: 7 :x:\n'
            '\n'
            'For more details on these failures, see [this check](https://details.url/).\n'
            '\n'
            'Results for commit commit.\n')
        )

    def test_get_long_summary_md_with_details_url_with_errors(self):
        self.assertEqual(get_long_summary_md(
            UnitTestRunResults(
                files=1, errors=[], suites=2, duration=3,
                tests=4, tests_succ=5, tests_skip=6, tests_fail=0, tests_error=8,
                runs=4, runs_succ=5, runs_skip=6, runs_fail=0, runs_error=8,
                commit='commit'
            ),
            'https://details.url/'
        ), ('1 files  2 suites   3s :stopwatch:\n'
            '4 tests 5 :heavy_check_mark: 6 :zzz: 0 :x: 8 :fire:\n'
            '\n'
            'For more details on these errors, see [this check](https://details.url/).\n'
            '\n'
            'Results for commit commit.\n')
        )

    def test_get_long_summary_md_with_details_url_with_parse_errors(self):
        self.assertEqual(get_long_summary_md(
            UnitTestRunResults(
                files=2, errors=errors, suites=2, duration=3,
                tests=4, tests_succ=5, tests_skip=6, tests_fail=0, tests_error=0,
                runs=4, runs_succ=5, runs_skip=6, runs_fail=0, runs_error=0,
                commit='commit'
            ),
            'https://details.url/'
        ), ('2 files  1 errors  2 suites   3s :stopwatch:\n'
            '4 tests 5 :heavy_check_mark: 6 :zzz: 0 :x:\n'
            '\n'
            'For more details on these parsing errors, see [this check](https://details.url/).\n'
            '\n'
            'Results for commit commit.\n')
        )

    def test_get_long_summary_md_with_details_url_with_fails_and_errors_and_parse_errors(self):
        self.assertEqual(get_long_summary_md(
            UnitTestRunResults(
                files=1, errors=errors, suites=2, duration=3,
                tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
                runs=4, runs_succ=5, runs_skip=6, runs_fail=7, runs_error=8,
                commit='commit'
            ),
            'https://details.url/'
        ), ('1 files  1 errors  2 suites   3s :stopwatch:\n'
            '4 tests 5 :heavy_check_mark: 6 :zzz: 7 :x: 8 :fire:\n'
            '\n'
            'For more details on these parsing errors, failures and errors, see [this check](https://details.url/).\n'
            '\n'
            'Results for commit commit.\n')
        )

    def test_get_long_summary_md_with_details_url_without_fails_or_errors_or_parse_errors(self):
        self.assertEqual(get_long_summary_md(
            UnitTestRunResults(
                files=1, errors=[], suites=2, duration=3,
                tests=4, tests_succ=5, tests_skip=6, tests_fail=0, tests_error=0,
                runs=4, runs_succ=5, runs_skip=6, runs_fail=0, runs_error=0,
                commit='commit'
            ),
            'https://details.url/'
        ), ('1 files  2 suites   3s :stopwatch:\n'
            '4 tests 5 :heavy_check_mark: 6 :zzz: 0 :x:\n'
            '\n'
            'Results for commit commit.\n')
        )

    def test_get_long_summary_md_with_test_lists(self):
        self.assertEqual(get_long_summary_md(
            UnitTestRunResults(
                files=1, errors=[], suites=2, duration=3,
                tests=4, tests_succ=5, tests_skip=6, tests_fail=0, tests_error=0,
                runs=4, runs_succ=5, runs_skip=6, runs_fail=0, runs_error=0,
                commit='commit'
            ),
            'https://details.url/',
            SomeTestChanges(
                ['test1', 'test2', 'test3', 'test4', 'test5'], ['test5', 'test6'],
                ['test2'], ['test5', 'test6']
            ),
        ), ('1 files  2 suites   3s :stopwatch:\n'
            '4 tests 5 :heavy_check_mark: 6 :zzz: 0 :x:\n'
            '\n'
            'Results for commit commit.\n'
            '\n'
            '<details>\n'
            '  <summary>This pull request <b>removes</b> 4 and <b>adds</b> 1 tests. '
            '<i>Note that renamed tests count towards both.</i></summary>\n'
            '\n'
            '```\n'
            'test1\n'
            'test2\n'
            'test3\n'
            'test4\n'
            '```\n'
            '\n'
            '```\n'
            'test6\n'
            '```\n'
            '</details>\n'
            '\n'
            '<details>\n'
            '  <summary>This pull request <b>removes</b> 1 skipped test and <b>adds</b> 1 skipped test. '
            '<i>Note that renamed tests count towards both.</i></summary>\n'
            '\n'
            '```\n'
            'test2\n'
            '```\n'
            '\n'
            '```\n'
            'test6\n'
            '```\n'
            '</details>\n'
            '\n'
            '<details>\n'
            '  <summary>This pull request <b>skips</b> 1 test.</summary>\n'
            '\n'
            '```\n'
            'test5\n'
            '```\n'
            '</details>\n')
        )

    def test_get_long_summary_md_with_test_lists_and_limit(self):
        self.assertEqual(get_long_summary_md(
            UnitTestRunResults(
                files=1, errors=[], suites=2, duration=3,
                tests=4, tests_succ=5, tests_skip=6, tests_fail=0, tests_error=0,
                runs=4, runs_succ=5, runs_skip=6, runs_fail=0, runs_error=0,
                commit='commit'
            ),
            'https://details.url/',
            SomeTestChanges(
                ['test1', 'test2', 'test3', 'test4', 'test5'], ['test5', 'test6', 'test7'],
                ['test1', 'test2'], ['test5', 'test6', 'test7']
            ),
            3
        ), ('1 files  2 suites   3s :stopwatch:\n'
            '4 tests 5 :heavy_check_mark: 6 :zzz: 0 :x:\n'
            '\n'
            'Results for commit commit.\n'
            '\n'
            '<details>\n'
            '  <summary>This pull request <b>removes</b> 4 and <b>adds</b> 2 tests. '
            '<i>Note that renamed tests count towards both.</i></summary>\n'
            '\n'
            '```\n'
            'test1\n'
            'test2\n'
            'test3\n'
            '…\n'
            '```\n'
            '\n'
            '```\n'
            'test6\n'
            'test7\n'
            '```\n'
            '</details>\n'
            '\n'
            '<details>\n'
            '  <summary>This pull request <b>removes</b> 2 skipped tests and <b>adds</b> 2 skipped tests. '
            '<i>Note that renamed tests count towards both.</i></summary>\n'
            '\n'
            '```\n'
            'test1\n'
            'test2\n'
            '```\n'
            '\n'
            '```\n'
            'test6\n'
            'test7\n'
            '```\n'
            '</details>\n'
            '\n'
            '<details>\n'
            '  <summary>This pull request <b>skips</b> 1 test.</summary>\n'
            '\n'
            '```\n'
            'test5\n'
            '```\n'
            '</details>\n')
        )

    def test_get_long_summary_md_with_test_lists_and_zero_limit(self):
        self.assertEqual(get_long_summary_md(
            UnitTestRunResults(
                files=1, errors=[], suites=2, duration=3,
                tests=4, tests_succ=5, tests_skip=6, tests_fail=0, tests_error=0,
                runs=4, runs_succ=5, runs_skip=6, runs_fail=0, runs_error=0,
                commit='commit'
            ),
            'https://details.url/',
            SomeTestChanges(
                ['test1', 'test2', 'test3', 'test4', 'test5'], ['test5', 'test6', 'test7'],
                ['test1', 'test2'], ['test5', 'test6', 'test7']
            ),
            0
        ), ('1 files  2 suites   3s :stopwatch:\n'
            '4 tests 5 :heavy_check_mark: 6 :zzz: 0 :x:\n'
            '\n'
            'Results for commit commit.\n')
        )

    def test_get_long_summary_md_with_all_tests_removed(self):
        self.assertEqual(get_long_summary_md(
            UnitTestRunResults(
                files=0, errors=[], suites=0, duration=0,
                tests=0, tests_succ=0, tests_skip=0, tests_fail=0, tests_error=0,
                runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0,
                commit='commit'
            ),
            'https://details.url/',
            SomeTestChanges(
                ['test1', 'test2', 'test3', 'test4', 'test5'], [],
                ['test2'], []
            ),
        ), ('0 files  0 suites   0s :stopwatch:\n'
            '0 tests 0 :heavy_check_mark: 0 :zzz: 0 :x:\n'
            '\n'
            'Results for commit commit.\n')
        )

    def test_get_long_summary_md_with_some_files_but_all_tests_removed(self):
        self.assertEqual(get_long_summary_md(
            UnitTestRunResults(
                files=2, errors=[], suites=0, duration=0,
                tests=0, tests_succ=0, tests_skip=0, tests_fail=0, tests_error=0,
                runs=0, runs_succ=0, runs_skip=0, runs_fail=0, runs_error=0,
                commit='commit'
            ),
            'https://details.url/',
            SomeTestChanges(
                ['test1', 'test2', 'test3', 'test4', 'test5'], [],
                ['test2'], []
            ),
        ), ('2 files  0 suites   0s :stopwatch:\n'
            '0 tests 0 :heavy_check_mark: 0 :zzz: 0 :x:\n'
            '\n'
            'Results for commit commit.\n')
        )

    def test_get_long_summary_with_digest_md_with_single_run(self):
        # makes gzipped digest deterministic
        with mock.patch('gzip.time.time', return_value=0):
            actual = get_long_summary_with_digest_md(
                UnitTestRunResults(
                    files=1, errors=[], suites=2, duration=3,
                    tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
                    runs=4, runs_succ=5, runs_skip=6, runs_fail=7, runs_error=8,
                    commit='commit'
                )
            )

        self.assertEqual(actual, '1 files  2 suites   3s :stopwatch:\n'
                                 '4 tests 5 :heavy_check_mark: 6 :zzz: 7 :x: 8 :fire:\n'
                                 '\n'
                                 'Results for commit commit.\n'
                                 '\n'
                                 '[test-results]:data:application/gzip;base64,'
                                 'H4sIAAAAAAAC/02MywqAIBQFfyVct+kd/UyEJVzKjKuuon/vZF'
                                 'juzsyBOYWibbFiyIo8E9aTC1ACZs+TI7MDKyAO91x13KP1UkI0'
                                 'v1jpgGg/oSbaILpPLMyGYXoY9nvsPTPNvfzXAiexwGlLGq3JAe'
                                 'K6buousrLZAAAA')

    def test_get_long_summary_with_digest_md_with_multiple_runs(self):
        # makes gzipped digest deterministic
        with mock.patch('gzip.time.time', return_value=0):
            actual = get_long_summary_with_digest_md(
                UnitTestRunResults(
                    files=1, errors=[], suites=2, duration=3,
                    tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=0,
                    runs=9, runs_succ=10, runs_skip=11, runs_fail=12, runs_error=0,
                    commit='commit'
                )
            )

        self.assertEqual(actual, '1 files    2 suites   3s :stopwatch:\n'
                                 '4 tests   5 :heavy_check_mark:   6 :zzz:   7 :x:\n'
                                 '9 runs  10 :heavy_check_mark: 11 :zzz: 12 :x:\n'
                                 '\n'
                                 'Results for commit commit.\n'
                                 '\n'
                                 '[test-results]:data:application/gzip;base64,'
                                 'H4sIAAAAAAAC/03MwQqDMBAE0F+RnD24aiv6M0VShaVqZJOciv'
                                 '/e0brR28wbmK8ZeRq86TLKM+Mjh6OUKO8ofWC3oFaoGMI+1Zpf'
                                 'PloLeFzw4RXwTDD2PAGaBIOIE0gBkbjsf+0Z9Y6KBP87IoXzjk'
                                 'qF+51188wBRdP2A3NU1srcAAAA')

    def test_get_long_summary_with_digest_md_with_test_errors(self):
        # makes gzipped digest deterministic
        with mock.patch('gzip.time.time', return_value=0):
            actual = get_long_summary_with_digest_md(
                UnitTestRunResults(
                    files=1, errors=[], suites=2, duration=3,
                    tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
                    runs=9, runs_succ=10, runs_skip=11, runs_fail=12, runs_error=13,
                    commit='commit'
                )
            )

        self.assertEqual(actual, '1 files    2 suites   3s :stopwatch:\n'
                                 '4 tests   5 :heavy_check_mark:   6 :zzz:   7 :x:   8 :fire:\n'
                                 '9 runs  10 :heavy_check_mark: 11 :zzz: 12 :x: 13 :fire:\n'
                                 '\n'
                                 'Results for commit commit.\n'
                                 '\n'
                                 '[test-results]:data:application/gzip;base64,'
                                 'H4sIAAAAAAAC/0XOwQ6CMBAE0F8hPXtgEVT8GdMUSDYCJdv2ZP'
                                 'x3psLW28zbZLIfM/E8BvOs6FKZkDj+SoMyJLGR/Yp6RcUh5lOr'
                                 '+RWSc4DuD2/eALcCk+UZcC8winiBPCCS1rzXn1HnqC5wzBEpnH'
                                 'PUKOgc5QedXxaOaJq+O+lMT3jdAAAA')

    def test_get_long_summary_with_digest_md_with_parse_errors(self):
        # makes gzipped digest deterministic
        with mock.patch('gzip.time.time', return_value=0):
            actual = get_long_summary_with_digest_md(
                UnitTestRunResults(
                    files=1, errors=errors, suites=2, duration=3,
                    tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
                    runs=9, runs_succ=10, runs_skip=11, runs_fail=12, runs_error=13,
                    commit='commit'
                )
            )

        self.assertEqual(actual, '1 files    1 errors    2 suites   3s :stopwatch:\n'
                                 '4 tests   5 :heavy_check_mark:   6 :zzz:   7 :x:   8 :fire:\n'
                                 '9 runs  10 :heavy_check_mark: 11 :zzz: 12 :x: 13 :fire:\n'
                                 '\n'
                                 'Results for commit commit.\n'
                                 '\n'
                                 '[test-results]:data:application/gzip;base64,'
                                 'H4sIAAAAAAAC/0XOwQ6CMBAE0F8hPXtgEVT8GdMUSDYCJdv2ZP'
                                 'x3psLW28zbZLIfM/E8BvOs6FKZkDj+SoMyJLGR/Yp6RcUh5lOr'
                                 '+RWSc4DuD2/eALcCk+UZcC8winiBPCCS1rzXn1HnqC5wzBEpnH'
                                 'PUKOgc5QedXxaOaJq+O+lMT3jdAAAA')

    def test_get_long_summary_with_digest_md_with_delta(self):
        # makes gzipped digest deterministic
        with mock.patch('gzip.time.time', return_value=0):
            actual = get_long_summary_with_digest_md(
                UnitTestRunDeltaResults(
                    files=n(1, 2), errors=[], suites=n(2, -3), duration=d(3, 4),
                    tests=n(4, -5), tests_succ=n(5, 6), tests_skip=n(6, -7), tests_fail=n(7, 8), tests_error=n(8, -9),
                    runs=n(9, 10), runs_succ=n(10, -11), runs_skip=n(11, 12), runs_fail=n(12, -13), runs_error=n(13, 14),
                    commit='123456789abcdef0', reference_type='type', reference_commit='0123456789abcdef'
                ), UnitTestRunResults(
                    files=1, errors=[], suites=2, duration=3,
                    tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
                    runs=4, runs_succ=5, runs_skip=6, runs_fail=7, runs_error=8,
                    commit='commit'
                )
            )

        self.assertEqual(actual, '1 files  +  2    2 suites   - 3   3s :stopwatch: +4s\n'
                                 '4 tests  -   5    5 :heavy_check_mark: +  6    6 :zzz:  -   7    7 :x: +  8    8 :fire:  -   9 \n'
                                 '9 runs  +10  10 :heavy_check_mark:  - 11  11 :zzz: +12  12 :x:  - 13  13 :fire: +14 \n'
                                 '\n'
                                 'Results for commit 12345678. ± Comparison against type commit 01234567.\n'
                                 '\n'
                                 '[test-results]:data:application/gzip;base64,'
                                 'H4sIAAAAAAAC/02MywqAIBQFfyVct+kd/UyEJVzKjKuuon/vZF'
                                 'juzsyBOYWibbFiyIo8E9aTC1ACZs+TI7MDKyAO91x13KP1UkI0'
                                 'v1jpgGg/oSbaILpPLMyGYXoY9nvsPTPNvfzXAiexwGlLGq3JAe'
                                 'K6buousrLZAAAA')

    def test_get_long_summary_with_digest_md_with_delta_and_parse_errors(self):
        # makes gzipped digest deterministic
        with mock.patch('gzip.time.time', return_value=0):
            actual = get_long_summary_with_digest_md(
                UnitTestRunDeltaResults(
                    files=n(1, 2), errors=errors, suites=n(2, -3), duration=d(3, 4),
                    tests=n(4, -5), tests_succ=n(5, 6), tests_skip=n(6, -7), tests_fail=n(7, 8), tests_error=n(8, -9),
                    runs=n(9, 10), runs_succ=n(10, -11), runs_skip=n(11, 12), runs_fail=n(12, -13), runs_error=n(13, 14),
                    commit='123456789abcdef0', reference_type='type', reference_commit='0123456789abcdef'
                ), UnitTestRunResults(
                    files=1, errors=[], suites=2, duration=3,
                    tests=4, tests_succ=5, tests_skip=6, tests_fail=7, tests_error=8,
                    runs=4, runs_succ=5, runs_skip=6, runs_fail=7, runs_error=8,
                    commit='commit'
                )
            )

        self.assertEqual(actual, '1 files  +  2    1 errors    2 suites   - 3   3s :stopwatch: +4s\n'
                                 '4 tests  -   5    5 :heavy_check_mark: +  6    6 :zzz:  -   7    7 :x: +  8    8 :fire:  -   9 \n'
                                 '9 runs  +10  10 :heavy_check_mark:  - 11  11 :zzz: +12  12 :x:  - 13  13 :fire: +14 \n'
                                 '\n'
                                 'Results for commit 12345678. ± Comparison against type commit 01234567.\n'
                                 '\n'
                                 '[test-results]:data:application/gzip;base64,'
                                 'H4sIAAAAAAAC/02MywqAIBQFfyVct+kd/UyEJVzKjKuuon/vZF'
                                 'juzsyBOYWibbFiyIo8E9aTC1ACZs+TI7MDKyAO91x13KP1UkI0'
                                 'v1jpgGg/oSbaILpPLMyGYXoY9nvsPTPNvfzXAiexwGlLGq3JAe'
                                 'K6buousrLZAAAA')

    def test_get_long_summary_with_digest_md_with_delta_results_only(self):
        with self.assertRaises(ValueError) as context:
            get_long_summary_with_digest_md(UnitTestRunDeltaResults(
                files=n(1, 2), errors=[], suites=n(2, -3), duration=d(3, 4),
                tests=n(4, -5), tests_succ=n(5, 6), tests_skip=n(6, -7), tests_fail=n(7, 8), tests_error=n(8, -9),
                runs=n(9, 10), runs_succ=n(10, -11), runs_skip=n(11, 12), runs_fail=n(12, -13), runs_error=n(13, 14),
                commit='123456789abcdef0', reference_type='type', reference_commit='0123456789abcdef'
            ))
        self.assertIn('stats must be UnitTestRunResults when no digest_stats is given', context.exception.args)

    def test_get_test_changes_md(self):
        self.assertEqual(
            '<details>\n'
            '  <summary>the summary</summary>\n'
            '\n'
            '```\n'
            'test1\n'
            'test2\n'
            '```\n'
            '</details>\n',
            get_test_changes_md('the summary', 3, ['test1', 'test2'])
        )
        self.assertEqual(
            '<details>\n'
            '  <summary>the summary</summary>\n'
            '\n'
            '```\n'
            'test1\n'
            'test2\n'
            '```\n'
            '\n'
            '```\n'
            'test3\n'
            'test4\n'
            'test5\n'
            '…\n'
            '```\n'
            '</details>\n',
            get_test_changes_md('the summary', 3, ['test1', 'test2'], ['test3', 'test4', 'test5', 'test6'])
        )

    def test_get_test_changes_list_md(self):
        self.assertEqual('```\n\n```\n', get_test_changes_list_md([], 3))
        self.assertEqual('```\ntest1\n```\n', get_test_changes_list_md(['test1'], 3))
        self.assertEqual('```\ntest1\ntest2\n```\n', get_test_changes_list_md(['test1', 'test2'], 3))
        self.assertEqual('```\ntest1\ntest2\ntest3\n```\n', get_test_changes_list_md(['test1', 'test2', 'test3'], 3))
        self.assertEqual('```\ntest1\ntest2\ntest3\n…\n```\n', get_test_changes_list_md(['test1', 'test2', 'test3', 'test4'], 3))

    def test_get_test_changes_summary_md(self):
        changes = SomeTestChanges(
            ['test', 'test1', 'test2', 'test3'], ['test', 'test 1', 'test 2', 'test 3'],
            ['test1', 'test2'], ['test 1', 'test 2', 'test 3']
        )
        self.assertEqual('<details>\n'
                         '  <summary>This pull request <b>removes</b> 3 and <b>adds</b> 3 tests. '
                         '<i>Note that renamed tests count towards both.</i></summary>\n'
                         '\n'
                         '```\n'
                         'test1\n'
                         'test2\n'
                         'test3\n'
                         '```\n'
                         '\n'
                         '```\n'
                         'test 1\n'
                         'test 2\n'
                         'test 3\n'
                         '```\n'
                         '</details>\n'
                         '\n'
                         '<details>\n'
                         '  <summary>This pull request <b>removes</b> 2 skipped tests and <b>adds</b> 3 skipped tests. '
                         '<i>Note that renamed tests count towards both.</i></summary>\n'
                         '\n'
                         '```\n'
                         'test1\n'
                         'test2\n'
                         '```\n'
                         '\n'
                         '```\n'
                         'test 1\n'
                         'test 2\n'
                         'test 3\n'
                         '```\n'
                         '</details>\n',
                         get_test_changes_summary_md(changes, 3))

    def test_get_test_changes_summary_md_with_nones(self):
        expected = ''
        changes = mock.Mock(SomeTestChanges)
        changes.removes = mock.Mock(return_value=None)
        changes.adds = mock.Mock(return_value=None)
        changes.remaining_and_skipped = mock.Mock(return_value=None)
        changes.remaining_and_un_skipped = mock.Mock(return_value=None)
        changes.removed_skips = mock.Mock(return_value=None)
        changes.added_and_skipped = mock.Mock(return_value=None)
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

        changes.removes = mock.Mock(return_value=[])
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

        changes.removes = mock.Mock(return_value=['test1'])
        expected = (
            '<details>\n'
            '  <summary>This pull request <b>removes</b> 1 test.</summary>\n'
            '\n'
            '```\n'
            'test1\n'
            '```\n'
            '</details>\n'
        )
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

        changes.adds = mock.Mock(return_value=[])
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

        changes.adds = mock.Mock(return_value=['test2'])
        expected = expected.replace('1 test.', '1 and <b>adds</b> 1 tests. '
                                               '<i>Note that renamed tests count towards both.</i>')
        expected = expected.replace('test1', 'test1\n```\n\n```\ntest2')
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

        changes.removed_skips = mock.Mock(return_value=[])
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

        changes.added_and_skipped = mock.Mock(return_value=[])
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

        changes.removed_skips = mock.Mock(return_value=['test5'])
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

        changes.added_and_skipped = mock.Mock(return_value=['test6'])
        expected = expected + (
            '\n'
            '<details>\n'
            '  <summary>This pull request <b>removes</b> 1 skipped test and <b>adds</b> 1 skipped test. '
            '<i>Note that renamed tests count towards both.</i></summary>\n'
            '\n'
            '```\n'
            'test5\n'
            '```\n'
            '\n'
            '```\n'
            'test6\n'
            '```\n'
            '</details>\n'
        )
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

        changes.remaining_and_skipped = mock.Mock(return_value=[])
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

        changes.remaining_and_skipped = mock.Mock(return_value=['test3'])
        expected = expected + (
            '\n'
            '<details>\n'
            '  <summary>This pull request <b>skips</b> 1 test.</summary>\n'
            '\n'
            '```\n'
            'test3\n'
            '```\n'
            '</details>\n'
        )
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

        changes.remaining_and_un_skipped = mock.Mock(return_value=[])
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

        changes.remaining_and_un_skipped = mock.Mock(return_value=['test4'])
        expected = expected.replace('This pull request <b>skips</b> 1 test.', 'This pull request <b>skips</b> 1 and <b>un-skips</b> 1 tests.')
        expected = expected.replace('test3', 'test3\n```\n\n```\ntest4')
        self.assertEqual(expected, get_test_changes_summary_md(changes, 3))

    def test_get_test_changes_summary_md_add_tests(self):
        changes = SomeTestChanges(
            ['test1'], ['test1', 'test2', 'test3'],
            [], []
        )
        self.assertEqual('', get_test_changes_summary_md(changes, 3))

    def test_get_test_changes_summary_md_remove_test(self):
        changes = SomeTestChanges(
            ['test1', 'test2', 'test3'], ['test1', 'test3'],
            [], []
        )
        self.assertEqual('<details>\n'
                         '  <summary>This pull request <b>removes</b> 1 test.</summary>\n'
                         '\n'
                         '```\n'
                         'test2\n'
                         '```\n'
                         '</details>\n',
                         get_test_changes_summary_md(changes, 3))

    def test_get_test_changes_summary_md_remove_tests(self):
        changes = SomeTestChanges(
            ['test1', 'test2', 'test3'], ['test1'],
            [], []
        )
        self.assertEqual('<details>\n'
                         '  <summary>This pull request <b>removes</b> 2 tests.</summary>\n'
                         '\n'
                         '```\n'
                         'test2\n'
                         'test3\n'
                         '```\n'
                         '</details>\n',
                         get_test_changes_summary_md(changes, 3))

    def test_get_test_changes_summary_md_rename_tests(self):
        changes = SomeTestChanges(
            ['test1', 'test2', 'test3'], ['test 1', 'test 2', 'test 3'],
            [], []
        )
        self.assertEqual('<details>\n'
                         '  <summary>This pull request <b>removes</b> 3 and <b>adds</b> 3 tests. '
                         '<i>Note that renamed tests count towards both.</i></summary>\n'
                         '\n'
                         '```\n'
                         'test1\n'
                         'test2\n'
                         'test3\n'
                         '```\n'
                         '\n'
                         '```\n'
                         'test 1\n'
                         'test 2\n'
                         'test 3\n'
                         '```\n'
                         '</details>\n',
                         get_test_changes_summary_md(changes, 3))

    def test_get_test_changes_summary_md_skip_test(self):
        changes = SomeTestChanges(
            ['test1', 'test2', 'test3'], ['test1', 'test2', 'test3'],
            [], ['test1']
        )
        self.assertEqual('<details>\n'
                         '  <summary>This pull request <b>skips</b> 1 test.</summary>\n'
                         '\n'
                         '```\n'
                         'test1\n'
                         '```\n'
                         '</details>\n',
                         get_test_changes_summary_md(changes, 3))

    def test_get_test_changes_summary_md_skip_tests(self):
        changes = SomeTestChanges(
            ['test1', 'test2', 'test3'], ['test1', 'test2', 'test3'],
            [], ['test1', 'test3']
        )
        self.assertEqual('<details>\n'
                         '  <summary>This pull request <b>skips</b> 2 tests.</summary>\n'
                         '\n'
                         '```\n'
                         'test1\n'
                         'test3\n'
                         '```\n'
                         '</details>\n',
                         get_test_changes_summary_md(changes, 3))

    def test_get_test_changes_summary_md_un_skip_tests(self):
        changes = SomeTestChanges(
            ['test1', 'test2', 'test3'], ['test1', 'test2', 'test3'],
            ['test1', 'test3'], []
        )
        self.assertEqual('', get_test_changes_summary_md(changes, 3))

    def test_get_test_changes_summary_md_skip_and_un_skip_tests(self):
        changes = SomeTestChanges(
            ['test1', 'test2', 'test3'], ['test1', 'test2', 'test3'],
            ['test1', 'test2'], ['test1', 'test3']
        )
        self.assertEqual('<details>\n'
                         '  <summary>This pull request <b>skips</b> 1 and <b>un-skips</b> 1 tests.</summary>\n'
                         '\n'
                         '```\n'
                         'test3\n'
                         '```\n'
                         '\n'
                         '```\n'
                         'test2\n'
                         '```\n'
                         '</details>\n',
                         get_test_changes_summary_md(changes, 3))

    def test_get_test_changes_summary_md_rename_skip_tests(self):
        changes = SomeTestChanges(
            ['test1', 'test2', 'test3'], ['test 1', 'test 2', 'test 3'],
            ['test1', 'test2'], ['test 1', 'test 2']
        )
        self.assertEqual('<details>\n'
                         '  <summary>This pull request <b>removes</b> 3 and <b>adds</b> 3 tests. '
                         '<i>Note that renamed tests count towards both.</i></summary>\n'
                         '\n'
                         '```\n'
                         'test1\n'
                         'test2\n'
                         'test3\n'
                         '```\n'
                         '\n'
                         '```\n'
                         'test 1\n'
                         'test 2\n'
                         'test 3\n'
                         '```\n'
                         '</details>\n'
                         '\n'
                         '<details>\n'
                         '  <summary>This pull request <b>removes</b> 2 skipped tests and <b>adds</b> 2 skipped tests. '
                         '<i>Note that renamed tests count towards both.</i></summary>\n'
                         '\n'
                         '```\n'
                         'test1\n'
                         'test2\n'
                         '```\n'
                         '\n'
                         '```\n'
                         'test 1\n'
                         'test 2\n'
                         '```\n'
                         '</details>\n',
                         get_test_changes_summary_md(changes, 3))

    def test_get_case_messages(self):
        results = UnitTestCaseResults([
            ((None, 'class1', 'test1'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='success', message='message1', content='content1', time=1.0),
                    UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='success', message='message1', content='content1', time=1.1),
                    UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='success', message='message2', content='content2', time=1.2),
                ])),
                ('skipped', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='skipped', message='message2', content='content2', time=None),
                    UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='skipped', message='message3', content='content3', time=None),
                ])),
                ('failure', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='failure', message='message4', content='content4', time=1.23),
                    UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='failure', message='message4', content='content4', time=1.234),
                ])),
                ('error', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='error', message='message5', content='content5', time=1.2345),
                ])),
            ])),
            ((None, 'class2', 'test2'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='success', message=None, content=None, time=None)
                ])),
                ('skipped', list([
                    UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='skipped', message=None, content=None, time=None)
                ])),
                ('failure', list([
                    UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='failure', message=None, content=None, time=None)
                ])),
                ('error', list([
                    UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='error', message=None, content=None, time=None)
                ])),
            ]))
        ])

        expected = CaseMessages([
            ((None, 'class1', 'test1'), dict([
                ('success', defaultdict(list, [
                    ('content1', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='success', message='message1', content='content1', time=1.0),
                        UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='success', message='message1', content='content1', time=1.1),
                    ])),
                    ('content2', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='success', message='message2', content='content2', time=1.2),
                    ]))
                ])),
                ('skipped', defaultdict(list, [
                    ('message2', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='skipped', message='message2', content='content2', time=None),
                    ])),
                    ('message3', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='skipped', message='message3', content='content3', time=None),
                    ]))
                ])),
                ('failure', defaultdict(list, [
                    ('content4', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='failure', message='message4', content='content4', time=1.23),
                        UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='failure', message='message4', content='content4', time=1.234),
                    ])),
                ])),
                ('error', defaultdict(list, [
                    ('content5', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=1, class_name='class1', test_name='test1', result='error', message='message5', content='content5', time=1.2345),
                    ])),
                ])),
            ])),
            ((None, 'class2', 'test2'), dict([
                ('success', dict([
                    (None, list([
                        UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='success', message=None, content=None, time=None)
                    ])),
                ])),
                ('skipped', dict([
                    (None, list([
                        UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='skipped', message=None, content=None, time=None)
                    ])),
                ])),
                ('failure', dict([
                    (None, list([
                        UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='failure', message=None, content=None, time=None)
                    ])),
                ])),
                ('error', dict([
                    (None, list([
                        UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='error', message=None, content=None, time=None)
                    ])),
                ])),
            ]))
        ])

        actual = get_case_messages(results)

        self.assertEqual(expected, actual)

    def test_annotation_to_dict(self):
        annotation = Annotation(path='file1', start_line=123, end_line=123, start_column=4, end_column=5, annotation_level='notice', message='result-file1', title='1 out of 6 runs skipped: test1', raw_details='message2')
        self.assertEqual(dict(path='file1', start_line=123, end_line=123, start_column=4, end_column=5, annotation_level='notice', message='result-file1', title='1 out of 6 runs skipped: test1', raw_details='message2'), annotation.to_dict())
        annotation = Annotation(path='class2', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='failure', message='result-file1', title='1 out of 4 runs with error: test2 (class2)', raw_details=None)
        self.assertEqual(dict(path='class2', start_line=0, end_line=0, annotation_level='failure', message='result-file1', title='1 out of 4 runs with error: test2 (class2)'), annotation.to_dict())
        annotation = Annotation(path='file', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='notice', message='message', title=None, raw_details=None)
        self.assertEqual(dict(path='file', start_line=0, end_line=0, annotation_level='notice', message='message'), annotation.to_dict())

    def test_annotation_to_dict_abbreviation(self):
        annotation = Annotation(path='file', start_line=123, end_line=123, start_column=None, end_column=None, annotation_level='notice', message='message ' * 8000, title='title - ' * 31, raw_details='raw ' * 16000)
        self.assertEqual('message ' * 8000, annotation.to_dict().get('message'))
        self.assertEqual('title - ' * 31, annotation.to_dict().get('title'))
        self.assertEqual('raw ' * 16000, annotation.to_dict().get('raw_details'))

        annotation = Annotation(path='file', start_line=123, end_line=123, start_column=None, end_column=None, annotation_level='notice', message='message ' * 8001, title='title - ' * 32, raw_details='raw ' * 16001)
        self.assertEqual('message ' * 3999 + 'message…ssage ' + 'message ' * 3999, annotation.to_dict().get('message'))
        self.assertEqual('title - ' * 15 + 'title -…itle - ' + 'title - ' * 15, annotation.to_dict().get('title'))
        self.assertEqual('raw ' * 8000 + '…aw ' + 'raw ' * 7999, annotation.to_dict().get('raw_details'))

    def test_get_case_annotation(self):
        messages = CaseMessages([
            ((None, 'class1', 'test1'), dict([
                ('success', dict([
                    ('message1', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='success', message='message1', content=None, time=1.0)
                    ]))
                ])),
                ('skipped', dict([
                    ('message2', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name=None, test_name='test1', result='skipped', message='message2', content=None, time=1.0)
                    ]))
                ])),
                ('failure', dict([
                    ('message3', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='', test_name='test1', result='failure', message='message3', content=None, time=1.0)
                    ])),
                    ('message4', list([
                        UnitTestCase(result_file='result-file2', test_file='file1', line=123, class_name='class1', test_name='test1', result='failure', message='message4', content=None, time=1.0),
                        UnitTestCase(result_file='result-file3', test_file='file1', line=123, class_name='class1', test_name='test1', result='failure', message='message4', content=None, time=1.0)
                    ])),
                ])),
                ('error', dict([
                    ('message5', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='error', message='message6', content=None, time=1.0)
                    ]))
                ])),
            ])),
            ((None, 'class2', 'test2'), dict([
                ('success', dict([
                    (None, list([
                        UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='success', message=None, content=None, time=None)
                    ])),
                ])),
                ('skipped', dict([
                    (None, list([
                        UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='skipped', message=None, content=None, time=None)
                    ])),
                ])),
                ('failure', dict([
                    (None, list([
                        UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='failure', message=None, content=None, time=None)
                    ])),
                ])),
                ('error', dict([
                    (None, list([
                        UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='error', message=None, content=None, time=None)
                    ])),
                ])),
            ]))
        ])

        self.assertEqual(Annotation(path='file1', start_line=123, end_line=123, start_column=None, end_column=None, annotation_level='notice', message='result-file1', title='1 out of 6 runs skipped: test1', raw_details='message2'), get_case_annotation(messages, (None, 'class1', 'test1'), 'skipped', 'message2', report_individual_runs=False))
        self.assertEqual(Annotation(path='file1', start_line=123, end_line=123, start_column=None, end_column=None, annotation_level='warning', message='result-file1\nresult-file2\nresult-file3', title='3 out of 6 runs failed: test1', raw_details='message3'), get_case_annotation(messages, (None, 'class1', 'test1'), 'failure', 'message3', report_individual_runs=False))
        self.assertEqual(Annotation(path='file1', start_line=123, end_line=123, start_column=None, end_column=None, annotation_level='warning', message='result-file1\nresult-file2\nresult-file3', title='3 out of 6 runs failed: test1 (class1)', raw_details='message4'), get_case_annotation(messages, (None, 'class1', 'test1'), 'failure', 'message4', report_individual_runs=False))
        self.assertEqual(Annotation(path='file1', start_line=123, end_line=123, start_column=None, end_column=None, annotation_level='failure', message='result-file1', title='1 out of 6 runs with error: test1 (class1)', raw_details='message5'), get_case_annotation(messages, (None, 'class1', 'test1'), 'error', 'message5', report_individual_runs=False))

        self.assertEqual(Annotation(path='class2', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='notice', message='result-file1', title='1 out of 4 runs skipped: test2 (class2)', raw_details=None), get_case_annotation(messages, (None, 'class2', 'test2'), 'skipped', None, report_individual_runs=False))
        self.assertEqual(Annotation(path='class2', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='warning', message='result-file1', title='1 out of 4 runs failed: test2 (class2)', raw_details=None), get_case_annotation(messages, (None, 'class2', 'test2'), 'failure', None, report_individual_runs=False))
        self.assertEqual(Annotation(path='class2', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='failure', message='result-file1', title='1 out of 4 runs with error: test2 (class2)', raw_details=None), get_case_annotation(messages, (None, 'class2', 'test2'), 'error', None, report_individual_runs=False))

    def test_get_case_annotation_report_individual_runs(self):
        messages = CaseMessages([
            ((None, 'class1', 'test1'), dict([
                ('success', dict([
                    ('message1', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='success', message='message1', content=None, time=1.0)
                    ]))
                ])),
                ('skipped', dict([
                    ('message2', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name=None, test_name='test1', result='skipped', message='message2', content=None, time=None)
                    ]))
                ])),
                ('failure', dict([
                    ('message3', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='', test_name='test1', result='failure', message='message3', content=None, time=1.23)
                    ])),
                    ('message4', list([
                        UnitTestCase(result_file='result-file2', test_file='file1', line=123, class_name='class1', test_name='test1', result='failure', message='message4', content=None, time=1.234),
                        UnitTestCase(result_file='result-file3', test_file='file1', line=123, class_name='class1', test_name='test1', result='failure', message='message4', content=None, time=1.234)
                    ])),
                ])),
                ('error', dict([
                    ('message5', list([
                        UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='error', message='message6', content=None, time=1.2345)
                    ]))
                ])),
            ]))
        ])

        self.assertEqual(Annotation(path='file1', start_line=123, end_line=123, start_column=None, end_column=None, annotation_level='notice', message='result-file1', title='1 out of 6 runs skipped: test1', raw_details='message2'), get_case_annotation(messages, (None, 'class1', 'test1'), 'skipped', 'message2', report_individual_runs=True))
        self.assertEqual(Annotation(path='file1', start_line=123, end_line=123, start_column=None, end_column=None, annotation_level='warning', message='result-file1', title='1 out of 6 runs failed: test1', raw_details='message3'), get_case_annotation(messages, (None, 'class1', 'test1'), 'failure', 'message3', report_individual_runs=True))
        self.assertEqual(Annotation(path='file1', start_line=123, end_line=123, start_column=None, end_column=None, annotation_level='warning', message='result-file2\nresult-file3', title='2 out of 6 runs failed: test1 (class1)', raw_details='message4'), get_case_annotation(messages, (None, 'class1', 'test1'), 'failure', 'message4', report_individual_runs=True))
        self.assertEqual(Annotation(path='file1', start_line=123, end_line=123, start_column=None, end_column=None, annotation_level='failure', message='result-file1', title='1 out of 6 runs with error: test1 (class1)', raw_details='message5'), get_case_annotation(messages, (None, 'class1', 'test1'), 'error', 'message5', report_individual_runs=True))

    def test_get_case_annotations(self):
        results = UnitTestCaseResults([
            ((None, 'class1', 'test1'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='success', message='success message', content='success content', time=1.0)
                ])),
                ('skipped', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name=None, test_name='test1', result='skipped', message='skip message', content='skip content', time=None)
                ])),
                ('failure', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='failure', message='fail message 1', content='fail content 1', time=1.2),
                    UnitTestCase(result_file='result-file2', test_file='file1', line=123, class_name='class1', test_name='test1', result='failure', message='fail message 2', content='fail content 2', time=1.23),
                    UnitTestCase(result_file='result-file3', test_file='file1', line=123, class_name='class1', test_name='test1', result='failure', message='fail message 2', content='fail content 2', time=1.234)
                ])),
                ('error', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='error', message='error message', content='error content', time=1.2345)
                ])),
            ])),
            ((None, 'class2', 'test2'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='success', message=None, content=None, time=None)
                ])),
                ('skipped', list([
                    UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='skipped', message=None, content=None, time=None)
                ])),
                ('failure', list([
                    UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='failure', message=None, content=None, time=None)
                ])),
                ('error', list([
                    UnitTestCase(result_file='result-file1', test_file=None, line=None, class_name='class2', test_name='test2', result='error', message=None, content=None, time=None)
                ])),
            ]))
        ])

        expected = [
            Annotation(
                annotation_level='warning',
                end_column=None,
                end_line=123,
                message='result-file1\nresult-file2\nresult-file3',
                path='file1',
                start_column=None,
                start_line=123,
                title='3 out of 6 runs failed: test1 (class1)',
                raw_details='fail content 1'
            ), Annotation(
                annotation_level='failure',
                end_column=None,
                end_line=123,
                message='result-file1',
                path='file1',
                start_column=None,
                start_line=123,
                title='1 out of 6 runs with error: test1 (class1)',
                raw_details='error content'
            ), Annotation(
                annotation_level='warning',
                end_column=None,
                end_line=0,
                message='result-file1',
                path='class2',
                start_column=None,
                start_line=0,
                title='1 out of 4 runs failed: test2 (class2)',
                raw_details=None
            ), Annotation(
                annotation_level='failure',
                end_column=None,
                end_line=0,
                message='result-file1',
                path='class2',
                start_column=None,
                start_line=0,
                title='1 out of 4 runs with error: test2 (class2)',
                raw_details=None
            ),
        ]

        annotations = get_case_annotations(results, report_individual_runs=False)

        self.assertEqual(expected, annotations)

    def test_get_case_annotations_report_individual_runs(self):
        results = UnitTestCaseResults([
            ((None, 'class1', 'test1'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='success', message='success message', content='success content', time=1.0)
                ])),
                ('skipped', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name=None, test_name='test1', result='skipped', message='skip message', content='skip content', time=None)
                ])),
                ('failure', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='failure', message='fail message 1', content='fail content 1', time=1.2),
                    UnitTestCase(result_file='result-file2', test_file='file1', line=123, class_name='class1', test_name='test1', result='failure', message='fail message 2', content='fail content 2', time=1.23),
                    UnitTestCase(result_file='result-file3', test_file='file1', line=123, class_name='class1', test_name='test1', result='failure', message='fail message 2', content='fail content 2', time=1.234)
                ])),
                ('error', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='error', message='error message', content='error content', time=0.1)
                ])),
            ]))
        ])

        expected = [
            Annotation(
                annotation_level='warning',
                end_column=None,
                end_line=123,
                message='result-file1',
                path='file1',
                start_column=None,
                start_line=123,
                title='1 out of 6 runs failed: test1 (class1)',
                raw_details='fail content 1'
            ), Annotation(
                annotation_level='warning',
                end_column=None,
                end_line=123,
                message='result-file2\nresult-file3',
                path='file1',
                start_column=None,
                start_line=123,
                title='2 out of 6 runs failed: test1 (class1)',
                raw_details='fail content 2'
            ), Annotation(
                annotation_level='failure',
                end_column=None,
                end_line=123,
                message='result-file1',
                path='file1',
                start_column=None,
                start_line=123,
                title='1 out of 6 runs with error: test1 (class1)',
                raw_details='error content'
            )
        ]

        annotations = get_case_annotations(results, report_individual_runs=True)

        self.assertEqual(expected, annotations)

    def test_get_error_annotation(self):
        self.assertEqual(Annotation(path='file', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='failure', message='message', title='Error processing result file', raw_details='file'), get_error_annotation(ParseError('file', 'message', None, None)))
        self.assertEqual(Annotation(path='file', start_line=12, end_line=12, start_column=None, end_column=None, annotation_level='failure', message='message', title='Error processing result file', raw_details='file'), get_error_annotation(ParseError('file', 'message', 12, None)))
        self.assertEqual(Annotation(path='file', start_line=12, end_line=12, start_column=34, end_column=34, annotation_level='failure', message='message', title='Error processing result file', raw_details='file'), get_error_annotation(ParseError('file', 'message', 12, 34)))

    def test_get_all_tests_list_annotation(self):
        results = UnitTestCaseResults([
            ((None, 'class1', 'test2'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test2', result='success', message='success message', content='success content', time=1.0)
                ])),
            ])),
            ((None, 'class1', 'test1'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='success', message='success message', content='success content', time=1.0)
                ])),
                ('skipped', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name=None, test_name='test1', result='skipped', message='skip message', content='skip content', time=None)
                ])),
            ])),
            (('file', 'class1', 'test2'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test2', result='success', message='success message', content='success content', time=1.0)
                ])),
            ]))
        ])

        self.assertEqual([], get_all_tests_list_annotation(UnitTestCaseResults()))
        self.assertEqual([Annotation(path='.github', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='notice', message='There are 3 tests, see "Raw output" for the full list of tests.', title='3 tests found', raw_details='class1 ‑ test1\nclass1 ‑ test2\nfile ‑ class1 ‑ test2')], get_all_tests_list_annotation(results))
        del results[(None, 'class1', 'test1')]
        del results[('file', 'class1', 'test2')]
        self.assertEqual([Annotation(path='.github', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='notice', message='There is 1 test, see "Raw output" for the name of the test.', title='1 test found', raw_details='class1 ‑ test2')], get_all_tests_list_annotation(results))

    def test_get_all_tests_list_annotation_chunked(self):
        results = UnitTestCaseResults([
            ((None, 'class1', 'test2'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test2', result='success', message='success message', content='success content', time=1.0)
                ])),
            ])),
            ((None, 'class1', 'test1'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='success', message='success message', content='success content', time=1.0)
                ])),
                ('skipped', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name=None, test_name='test1', result='skipped', message='skip message', content='skip content', time=None)
                ])),
            ])),
            (('file', 'class1', 'test2'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test2', result='success', message='success message', content='success content', time=1.0)
                ])),
            ]))
        ])

        self.assertEqual([], get_all_tests_list_annotation(UnitTestCaseResults()))
        self.assertEqual(
            [
                Annotation(path='.github', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='notice', message='There are 3 tests, see "Raw output" for the list of tests 1 to 2.', title='3 tests found (test 1 to 2)', raw_details='class1 ‑ test1\nclass1 ‑ test2'),
                Annotation(path='.github', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='notice', message='There are 3 tests, see "Raw output" for the list of tests 3 to 3.', title='3 tests found (test 3 to 3)', raw_details='file ‑ class1 ‑ test2')
            ],
            get_all_tests_list_annotation(results, max_chunk_size=40)
        )

    def test_get_skipped_tests_list_annotation(self):
        results = UnitTestCaseResults([
            ((None, 'class1', 'test2'), dict([
                ('skipped', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test2', result='success', message='success message', content='success content', time=1.0)
                ])),
            ])),
            ((None, 'class1', 'test1'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='success', message='success message', content='success content', time=1.0)
                ])),
                ('skipped', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name=None, test_name='test1', result='skipped', message='skip message', content='skip content', time=None)
                ])),
            ])),
            (('file', 'class1', 'test2'), dict([
                ('success', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test2', result='success', message='success message', content='success content', time=1.0)
                ])),
            ]))
        ])

        self.assertEqual([], get_skipped_tests_list_annotation(UnitTestCaseResults()))
        self.assertEqual([Annotation(path='.github', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='notice', message='There is 1 skipped test, see "Raw output" for the name of the skipped test.', title='1 skipped test found', raw_details='class1 ‑ test2')], get_skipped_tests_list_annotation(results))
        del results[(None, 'class1', 'test1')]['success']
        self.assertEqual([Annotation(path='.github', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='notice', message='There are 2 skipped tests, see "Raw output" for the full list of skipped tests.', title='2 skipped tests found', raw_details='class1 ‑ test1\nclass1 ‑ test2')], get_skipped_tests_list_annotation(results))

    def test_get_skipped_tests_list_annotation_chunked(self):
        results = UnitTestCaseResults([
            ((None, 'class1', 'test2'), dict([
                ('skipped', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test2', result='success', message='success message', content='success content', time=1.0)
                ])),
            ])),
            ((None, 'class1', 'test1'), dict([
                ('skipped', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test1', result='success', message='success message', content='success content', time=1.0)
                ])),
            ])),
            (('file', 'class1', 'test2'), dict([
                ('skipped', list([
                    UnitTestCase(result_file='result-file1', test_file='file1', line=123, class_name='class1', test_name='test2', result='success', message='success message', content='success content', time=1.0)
                ])),
            ]))
        ])

        self.assertEqual([], get_skipped_tests_list_annotation(UnitTestCaseResults()))
        self.assertEqual(
            [
                Annotation(path='.github', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='notice', message='There are 3 skipped tests, see "Raw output" for the list of skipped tests 1 to 2.', title='3 skipped tests found (test 1 to 2)', raw_details='class1 ‑ test1\nclass1 ‑ test2'),
                Annotation(path='.github', start_line=0, end_line=0, start_column=None, end_column=None, annotation_level='notice', message='There are 3 skipped tests, see "Raw output" for the list of skipped tests 3 to 3.', title='3 skipped tests found (test 3 to 3)', raw_details='file ‑ class1 ‑ test2')
            ],
            get_skipped_tests_list_annotation(results, max_chunk_size=40)
        )

    def test_chunk(self):
        self.assertEqual([], chunk_test_list([], '\n', 100))

        four_per_chunk = [['abcdefghijklmnopqrstu-0',
                           'abcdefghijklmnopqrstu-1',
                           'abcdefghijklmnopqrstu-2',
                           'abcdefghijklmnopqrstu-3'],
                          ['abcdefghijklmnopqrstu-4',
                           'abcdefghijklmnopqrstu-5',
                           'abcdefghijklmnopqrstu-6',
                           'abcdefghijklmnopqrstu-7'],
                          ['abcdefghijklmnopqrstu-8',
                           'abcdefghijklmnopqrstu-9']]

        three_per_chunk = [['abcdefghijklmnopqrstuv-0',
                            'abcdefghijklmnopqrstuv-1',
                            'abcdefghijklmnopqrstuv-2'],
                           ['abcdefghijklmnopqrstuv-3',
                            'abcdefghijklmnopqrstuv-4',
                            'abcdefghijklmnopqrstuv-5'],
                           ['abcdefghijklmnopqrstuv-6',
                            'abcdefghijklmnopqrstuv-7',
                            'abcdefghijklmnopqrstuv-8'],
                           ['abcdefghijklmnopqrstuv-9']]

        tests = [f'abcdefghijklmnopqrstu-{i}' for i in range(10)]
        chunks = chunk_test_list(tests, '\n', 100)
        self.assertEqual(four_per_chunk, chunks)

        tests = [f'abcdefghijklmnopqrstuv-{i}' for i in range(10)]
        chunks = chunk_test_list(tests, '\r\n', 100)
        self.assertEqual(three_per_chunk, chunks)

        tests = [f'abcdefghijklmnopqrstuv-{i}' for i in range(10)]
        chunks = chunk_test_list(tests, '\n', 100)
        self.assertEqual(three_per_chunk, chunks)

        tests = [f'abcdefghijklmnopqrstuvw-{i}' for i in range(10)]
        chunks = chunk_test_list(tests, '\n', 100)
        self.assertEqual([['abcdefghijklmnopqrstuvw-0',
                           'abcdefghijklmnopqrstuvw-1',
                           'abcdefghijklmnopqrstuvw-2'],
                          ['abcdefghijklmnopqrstuvw-3',
                           'abcdefghijklmnopqrstuvw-4',
                           'abcdefghijklmnopqrstuvw-5'],
                          ['abcdefghijklmnopqrstuvw-6',
                           'abcdefghijklmnopqrstuvw-7',
                           'abcdefghijklmnopqrstuvw-8'],
                          ['abcdefghijklmnopqrstuvw-9']],
                         chunks)

    def test_files(self):
        parsed = parse_junit_xml_files(['files/junit.gloo.elastic.spark.tf.xml',
                                        'files/junit.gloo.elastic.spark.torch.xml',
                                        'files/junit.gloo.elastic.xml',
                                        'files/junit.gloo.standalone.xml',
                                        'files/junit.gloo.static.xml',
                                        'files/junit.mpi.integration.xml',
                                        'files/junit.mpi.standalone.xml',
                                        'files/junit.mpi.static.xml',
                                        'files/junit.spark.integration.1.xml',
                                        'files/junit.spark.integration.2.xml']).with_commit('example')
        results = get_test_results(parsed, False)
        stats = get_stats(results)
        md = get_long_summary_md(stats)
        self.assertEqual(md, ('  10 files    10 suites   39m 1s :stopwatch:\n'
                              '217 tests 208 :heavy_check_mark:   9 :zzz: 0 :x:\n'
                              '373 runs  333 :heavy_check_mark: 40 :zzz: 0 :x:\n'
                              '\n'
                              'Results for commit example.\n'))

    def test_file_without_cases(self):
        parsed = parse_junit_xml_files(['files/no-cases.xml']).with_commit('a commit sha')
        results = get_test_results(parsed, False)
        stats = get_stats(results)
        md = get_long_summary_md(stats)
        self.assertEqual(md, ('1 files  1 suites   0s :stopwatch:\n'
                              '0 tests 0 :heavy_check_mark: 0 :zzz: 0 :x:\n'
                              '\n'
                              'Results for commit a commit.\n'))

    def test_non_parsable_file(self):
        parsed = parse_junit_xml_files(['files/empty.xml']).with_commit('a commit sha')
        results = get_test_results(parsed, False)
        stats = get_stats(results)
        md = get_long_summary_md(stats)
        self.assertEqual(md, ('1 files  1 errors  0 suites   0s :stopwatch:\n'
                              '0 tests 0 :heavy_check_mark: 0 :zzz: 0 :x:\n'
                              '\n'
                              'Results for commit a commit.\n'))

    def test_files_with_testcase_in_testcase(self):
        parsed = parse_junit_xml_files(['files/testcase-in-testcase.xml']).with_commit('example')
        results = get_test_results(parsed, False)
        stats = get_stats(results)
        md = get_long_summary_md(stats)
        self.assertEqual(md, ('1 files  1 suites   4s :stopwatch:\n'
                              '5 tests 5 :heavy_check_mark: 0 :zzz: 0 :x:\n'
                              '\n'
                              'Results for commit example.\n'))


if __name__ == '__main__':
    unittest.main()
