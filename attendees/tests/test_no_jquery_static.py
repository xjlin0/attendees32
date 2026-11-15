import re
from pathlib import Path
import pytest
from django.conf import settings

ROOT_DIR = getattr(settings, "ROOT_DIR", Path(__file__).resolve().parent.parent.parent)


def find_jquery_js_violations(file_path: Path):
    """
    Statically scans a JavaScript file for jQuery / $ invocations.
    Returns a list of tuples: (line_number, line_content, matched_text).
    Allows ES6 template literals (${...}) and regex anchors (/^...$/).
    """
    violations = []
    # Matches:
    # 1. $(...) or $.prop
    # 2. jQuery(...) or jQuery.prop
    # 3. window.$ or window.jQuery
    jquery_pattern = re.compile(
        r'(?<![a-zA-Z0-9_\$])(?:(?:\$|jQuery)\s*[\(\.]|window\s*\.\s*(?:\$|jQuery)(?![a-zA-Z0-9_\$]))'
    )

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            # Strip single-line comments // ...
            code_line = line.split("//")[0]
            match = jquery_pattern.search(code_line)
            if match:
                violations.append((line_num, line.strip(), match.group()))

    return violations


class TestNoJqueryStaticScan:
    """
    Static analysis unit tests to ensure that designated templates and JS files
    do NOT include or invoke jQuery / $ in any form.
    """

    def test_base_without_jquery_html_does_not_load_jquery(self):
        template_path = ROOT_DIR / "attendees" / "templates" / "base_without_jquery.html"
        assert template_path.is_file(), f"Template not found at {template_path}"

        content = template_path.read_text(encoding="utf-8")

        # Extract all <script src="..."> tags
        script_src_pattern = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
        loaded_scripts = script_src_pattern.findall(content)

        jquery_loaded = []
        for src in loaded_scripts:
            # Check if source contains 'jquery' but is NOT a '*without_jquery*' file
            if re.search(r'(?<!without_)jquery', src, re.IGNORECASE):
                jquery_loaded.append(src)

        assert not jquery_loaded, (
            f"base_without_jquery.html must not load any jQuery scripts, "
            f"but found: {jquery_loaded}"
        )

        # Check inline script blocks if any
        inline_script_pattern = re.compile(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', re.IGNORECASE | re.DOTALL)
        for inline_block in inline_script_pattern.findall(content):
            violations = []
            for line_num, line in enumerate(inline_block.splitlines(), 1):
                code_line = line.split("//")[0]
                if re.search(r'(?<![a-zA-Z0-9_\$])(?:(?:\$|jQuery)\s*[\(\.]|window\s*\.\s*(?:\$|jQuery)(?![a-zA-Z0-9_\$]))', code_line):
                    violations.append((line_num, line.strip()))
            assert not violations, f"Inline script in base_without_jquery.html has jQuery calls: {violations}"

    @pytest.mark.parametrize(
        "rel_path",
        [
            "attendees/static/js/shared/base_without_jquery.js",
            "attendees/static/js/shared/utilities_without_jquery.js",
            "attendees/static/js/occasions/rosters_list_view.js",
        ],
    )
    def test_js_files_do_not_invoke_jquery_or_dollar(self, rel_path):
        js_path = ROOT_DIR / rel_path
        assert js_path.is_file(), f"File not found: {js_path}"

        violations = find_jquery_js_violations(js_path)
        assert not violations, (
            f"Detected jQuery / $ usage in {rel_path}:\n"
            + "\n".join([f"  Line {v[0]}: {v[1]} (matched: {v[2]})" for v in violations])
        )

    def test_scanner_catches_jquery_violations(self, tmp_path):
        """Self-test to ensure the violation detector catches jQuery invocations but ignores safe ES6 template literals."""
        bad_sample = tmp_path / "bad.js"
        bad_sample.write_text(
            'const x = $("#app");\n'
            'const y = `${variable}`;\n'
            'const z = $.ajax({});\n'
            'const w = jQuery(".btn");\n'
            'const v = window.$;\n'
        )
        violations = find_jquery_js_violations(bad_sample)
        assert len(violations) == 4
        # Lines 1, 3, 4, 5 are violations; line 2 (template literal) is safe
        violation_lines = [v[0] for v in violations]
        assert violation_lines == [1, 3, 4, 5]
