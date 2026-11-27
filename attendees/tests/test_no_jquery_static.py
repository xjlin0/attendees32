import json
import re
from pathlib import Path
import pytest
from django.conf import settings

ROOT_DIR = getattr(settings, "ROOT_DIR", Path(__file__).resolve().parent.parent.parent)

JQUERY_PATTERNS = [
    # 1. Direct invocations or properties: $(...), $.prop, jQuery(...), jQuery.prop, window.$, (window as any).$
    re.compile(
        r'(?<![a-zA-Z0-9_\$])(?:(?:\$|jQuery)\s*[\(\.]|(?:window|\(\s*window\s+as\s+any\s*\)|\(\s*<any>\s*window\s*\))\s*\.\s*(?:\$|jQuery)(?![a-zA-Z0-9_\$]))'
    ),
    # 2. Ambient declarations in TS: declare const $, declare var jQuery, etc.
    re.compile(
        r'\bdeclare\s+(?:const|let|var)\s+(?:\$|jQuery)(?![a-zA-Z0-9_\$])'
    ),
    # 3. Imports: import ... from 'jquery', require('jquery')
    re.compile(
        r'''\b(?:import|require)\s*(?:\(?\s*['\"]jquery['\"]|.*?from\s*['\"]jquery['\"])'''
    ),
]


def find_jquery_js_violations(file_path: Path):
    """
    Statically scans a JavaScript or TypeScript file for jQuery / $ invocations,
    ambient declarations, type-cast window accesses, and module imports.
    Returns a list of tuples: (line_number, line_content, matched_text).
    Allows ES6 template literals (${...}) and regex anchors (/^...$/).
    """
    violations = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            # Strip single-line comments // ...
            code_line = line.split("//")[0]
            for pattern in JQUERY_PATTERNS:
                match = pattern.search(code_line)
                if match:
                    violations.append((line_num, line.strip(), match.group()))
                    break

    return violations


class TestNoJqueryStaticScan:
    """
    Static analysis unit tests to ensure that designated templates, package configs,
    and frontend source files do NOT include or invoke jQuery / $ in any form.
    """

    def test_package_json_has_no_jquery_dependencies(self):
        """Ensures package.json does not depend on jquery or @types/jquery."""
        pkg_path = ROOT_DIR / "package.json"
        assert pkg_path.is_file(), f"package.json not found at {pkg_path}"

        with open(pkg_path, "r", encoding="utf-8") as f:
            pkg_data = json.load(f)

        all_deps = {}
        for section in ("dependencies", "devDependencies", "_original_dependencies"):
            all_deps.update(pkg_data.get(section, {}))

        jquery_deps = [dep for dep in all_deps if "jquery" in dep.lower()]
        assert not jquery_deps, (
            f"package.json must not include any jQuery dependencies, but found: {jquery_deps}"
        )

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
                for pattern in JQUERY_PATTERNS:
                    if pattern.search(code_line):
                        violations.append((line_num, line.strip()))
                        break
            assert not violations, f"Inline script in base_without_jquery.html has jQuery calls: {violations}"

    def test_all_frontend_ts_and_vue_files_do_not_invoke_jquery(self):
        """Scans all TypeScript and Vue files in attendees/frontend for jQuery usages."""
        frontend_dir = ROOT_DIR / "attendees" / "frontend"
        assert frontend_dir.is_dir(), f"Frontend directory not found at {frontend_dir}"

        files_to_scan = sorted(list(frontend_dir.rglob("*.ts")) + list(frontend_dir.rglob("*.vue")))
        assert len(files_to_scan) > 0, "Expected at least one TypeScript or Vue file in frontend directory"

        all_violations = {}
        for file_path in files_to_scan:
            violations = find_jquery_js_violations(file_path)
            if violations:
                rel_path = file_path.relative_to(ROOT_DIR).as_posix()
                all_violations[rel_path] = violations

        assert not all_violations, (
            f"Detected jQuery / $ usage in frontend files:\n"
            + "\n".join(
                [
                    f"{path}:\n" + "\n".join([f"  Line {v[0]}: {v[1]} (matched: {v[2]})" for v in viols])
                    for path, viols in all_violations.items()
                ]
            )
        )

    def test_scanner_catches_jquery_violations(self, tmp_path):
        """Self-test to ensure the violation detector catches jQuery invocations, declarations, and imports."""
        bad_sample = tmp_path / "bad.ts"
        bad_sample.write_text(
            'const x = $("#app");\n'
            'const y = `${variable}`;\n'
            'const z = $.ajax({});\n'
            'const w = jQuery(".btn");\n'
            'const v = window.$;\n'
            'const v2 = (window as any).$;\n'
            'declare const $: any;\n'
            'declare var jQuery: any;\n'
            'import $ from "jquery";\n'
            'const safeIdentifier = $foo;\n'
        )
        violations = find_jquery_js_violations(bad_sample)
        # Expected violations on lines 1, 3, 4, 5, 6, 7, 8, 9
        # Safe lines: 2 (`${variable}`), 10 ($foo)
        violation_lines = [v[0] for v in violations]
        assert violation_lines == [1, 3, 4, 5, 6, 7, 8, 9], f"Unexpected violation lines: {violation_lines}"
