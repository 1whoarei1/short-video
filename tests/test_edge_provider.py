import unittest
from scripts.edge_provider import resolve_words


def event(text, offset=0):
    return dict(text=text, offset=offset, duration=1000000)


class EdgeBoundaryTests(unittest.TestCase):
    def test_exact_repeated_text_with_punctuation(self):
        words = resolve_words('红肉，红肉。', [event('红肉'), event('红肉', 2000000)])
        self.assertEqual([(w['char_start'], w['char_end']) for w in words], [(0, 2), (3, 5)])
        self.assertEqual(words[1]['start'], .2)

    def test_missing_middle_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_words('红肉和红肉', [event('红肉'), event('红肉')])

    def test_missing_tail_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_words('二A类', [event('二'), event('A')])

    def test_normalized_speech_is_not_guessed(self):
        with self.assertRaises(ValueError):
            resolve_words('18%', [event('十八')])

    def test_mixed_script_exact(self):
        words = resolve_words('二A类。', [event('二'), event('A'), event('类')])
        self.assertEqual(words[-1]['char_end'], 3)

    def test_no_boundaries_is_rejected(self):
        with self.assertRaises(ValueError): resolve_words('你好', [])


if __name__ == '__main__': unittest.main()
