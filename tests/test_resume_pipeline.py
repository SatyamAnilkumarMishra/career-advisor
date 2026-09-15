import os
import tempfile
import unittest

from backend.errors import ResumeParsingError
from backend.resume_pipeline import extract_resume_text, validate_resume_file


class TestValidateResumeFile(unittest.TestCase):
    def test_missing_file_raises(self):
        with self.assertRaises(ResumeParsingError):
            validate_resume_file("/nonexistent/resume.pdf", max_size_bytes=1024)

    def test_empty_file_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            path = tmp.name
        try:
            with self.assertRaises(ResumeParsingError):
                validate_resume_file(path, max_size_bytes=1024)
        finally:
            os.remove(path)

    def test_oversized_file_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"x" * 2000)
            path = tmp.name
        try:
            with self.assertRaises(ResumeParsingError):
                validate_resume_file(path, max_size_bytes=100)
        finally:
            os.remove(path)

    def test_unsupported_extension_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
            tmp.write(b"not a resume")
            path = tmp.name
        try:
            with self.assertRaises(ResumeParsingError):
                validate_resume_file(path, max_size_bytes=1024 * 1024)
        finally:
            os.remove(path)

    def test_valid_txt_file_returns_extension(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"Jane Doe, Software Engineer")
            path = tmp.name
        try:
            ext = validate_resume_file(path, max_size_bytes=1024 * 1024)
            self.assertEqual(ext, ".txt")
        finally:
            os.remove(path)


class TestExtractResumeText(unittest.TestCase):
    def test_extracts_plain_text(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as tmp:
            tmp.write("Jane Doe\nSoftware Engineer with 3 years of Python experience.")
            path = tmp.name
        try:
            text = extract_resume_text(path, max_size_bytes=1024 * 1024)
            self.assertIn("Jane Doe", text)
            self.assertIn("Python", text)
        finally:
            os.remove(path)

    def test_empty_extracted_text_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as tmp:
            tmp.write("   \n\n   ")
            path = tmp.name
        try:
            with self.assertRaises(ResumeParsingError):
                extract_resume_text(path, max_size_bytes=1024 * 1024)
        finally:
            os.remove(path)

    def test_missing_settings_and_max_size_raises_value_error(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as tmp:
            tmp.write("Jane Doe")
            path = tmp.name
        try:
            with self.assertRaises(ValueError):
                extract_resume_text(path)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
