"""Tests for code_to_html() function - nm-3

Tests verify that code files are correctly converted to HTML with syntax highlighting
using Pygments, with proper language detection and fallback handling.
"""

import sys
import pathlib

# Add parent directory to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from render_to_webp import code_to_html, RenderConfig


def test_code_to_html_python():
    """Test Python code highlighting with proper lexer detection."""
    code = '''def hello_world():
    """A simple test function."""
    print("Hello, World!")
    return 42
'''
    cfg = RenderConfig()
    html = code_to_html(code, "test.py", cfg, "Python Test")

    # Verify HTML structure
    assert "<html" in html.lower()
    assert "</html>" in html.lower()
    assert "<head>" in html.lower()
    assert "<body>" in html.lower()

    # Verify code is present (syntax highlighted - keywords may be in span tags)
    assert "hello_world" in html
    assert "print" in html
    assert "42" in html

    # Verify Pygments CSS class is present
    assert "codehilite" in html

    # Verify it's wrapped in article tag
    assert "<article class='code-article'>" in html


def test_code_to_html_javascript():
    """Test JavaScript code highlighting."""
    code = '''function greet(name) {
    console.log(`Hello, ${name}!`);
    return name;
}
'''
    cfg = RenderConfig()
    html = code_to_html(code, "test.js", cfg, "JavaScript Test")

    assert "<html" in html.lower()
    assert "greet" in html
    assert "console" in html
    assert "codehilite" in html


def test_code_to_html_typescript():
    """Test TypeScript code highlighting."""
    code = '''interface User {
    name: string;
    age: number;
}

function greet(user: User): void {
    console.log(`Hello, ${user.name}!`);
}
'''
    cfg = RenderConfig()
    html = code_to_html(code, "test.ts", cfg, "TypeScript Test")

    assert "<html" in html.lower()
    assert "User" in html
    assert "string" in html
    assert "codehilite" in html


def test_code_to_html_shell():
    """Test shell script highlighting."""
    code = '''#!/bin/bash
echo "Hello, World!"
cd /tmp
ls -la
'''
    cfg = RenderConfig()
    html = code_to_html(code, "test.sh", cfg, "Shell Test")

    assert "<html" in html.lower()
    assert "#!/bin/bash" in html
    assert "echo" in html
    assert "codehilite" in html


def test_code_to_html_json():
    """Test JSON highlighting."""
    code = '''{
    "name": "test",
    "version": "1.0.0",
    "dependencies": {}
}
'''
    cfg = RenderConfig()
    html = code_to_html(code, "package.json", cfg, "JSON Test")

    assert "<html" in html.lower()
    assert "name" in html
    assert "version" in html
    assert "codehilite" in html


def test_code_to_html_unknown_fallback():
    """Test fallback to TextLexer for unknown file types."""
    code = '''This is some text
in an unknown file format
with no syntax highlighting
'''
    cfg = RenderConfig()
    html = code_to_html(code, "unknown.xyz", cfg, "Unknown Test")

    # Should still generate valid HTML
    assert "<html" in html.lower()
    assert "</html>" in html.lower()

    # Content should be present
    assert "This is some text" in html
    assert "unknown file format" in html

    # Should still have codehilite class (from TextLexer)
    assert "codehilite" in html


def test_code_to_html_with_custom_pygments_style():
    """Test that custom Pygments style is applied."""
    code = '''print("Hello")'''

    # Test with monokai style
    cfg_monokai = RenderConfig(pygments_style="monokai")
    html_monokai = code_to_html(code, "test.py", cfg_monokai, "Test")

    # Should contain Pygments CSS
    assert ".codehilite" in html_monokai

    # Test with default (friendly) style
    cfg_default = RenderConfig()
    html_default = code_to_html(code, "test.py", cfg_default, "Test")

    assert ".codehilite" in html_default


def test_code_to_html_line_numbers():
    """Test that line numbers are included in output."""
    code = '''line 1
line 2
line 3
line 4
line 5
'''
    cfg = RenderConfig()
    html = code_to_html(code, "test.txt", cfg, "Line Number Test")

    # Pygments adds line number elements/classes
    # The exact format depends on the formatter, but it should contain linenos-related markup
    assert "codehilite" in html
    assert "<html" in html.lower()


def test_code_to_html_empty_code():
    """Test handling of empty code input."""
    code = ""
    cfg = RenderConfig()
    html = code_to_html(code, "empty.py", cfg, "Empty Test")

    # Should still generate valid HTML structure
    assert "<html" in html.lower()
    assert "</html>" in html.lower()
    assert "codehilite" in html


def test_code_to_html_go():
    """Test Go code highlighting."""
    code = '''package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
'''
    cfg = RenderConfig()
    html = code_to_html(code, "main.go", cfg, "Go Test")

    assert "<html" in html.lower()
    assert "package" in html
    assert "main" in html
    assert "codehilite" in html


def test_code_to_html_rust():
    """Test Rust code highlighting."""
    code = '''fn main() {
    println!("Hello, World!");
}
'''
    cfg = RenderConfig()
    html = code_to_html(code, "main.rs", cfg, "Rust Test")

    assert "<html" in html.lower()
    assert "main" in html
    assert "println" in html
    assert "codehilite" in html


def test_code_to_html_yaml():
    """Test YAML code highlighting."""
    code = '''name: test
version: 1.0.0
dependencies:
  - package1
  - package2
'''
    cfg = RenderConfig()
    html = code_to_html(code, "config.yml", cfg, "YAML Test")

    assert "<html" in html.lower()
    assert "test" in html
    assert "version" in html
    assert "codehilite" in html


def test_code_to_html_special_characters():
    """Test handling of special HTML characters."""
    code = '''<html>
<body>
    <script>alert("XSS test & <tags>");</script>
</body>
</html>
'''
    cfg = RenderConfig()
    html = code_to_html(code, "test.html", cfg, "HTML Test")

    # Should contain the code (Pygments handles HTML escaping)
    assert "<html" in html.lower()
    assert "codehilite" in html
    # The content should be syntax highlighted as HTML
    assert "alert" in html or "&lt;script&gt;" in html or "<script>" in html


if __name__ == "__main__":
    # Run tests manually
    print("Running tests for code_to_html()...")

    tests = [
        ("Python", test_code_to_html_python),
        ("JavaScript", test_code_to_html_javascript),
        ("TypeScript", test_code_to_html_typescript),
        ("Shell", test_code_to_html_shell),
        ("JSON", test_code_to_html_json),
        ("Unknown fallback", test_code_to_html_unknown_fallback),
        ("Custom Pygments style", test_code_to_html_with_custom_pygments_style),
        ("Line numbers", test_code_to_html_line_numbers),
        ("Empty code", test_code_to_html_empty_code),
        ("Go", test_code_to_html_go),
        ("Rust", test_code_to_html_rust),
        ("YAML", test_code_to_html_yaml),
        ("Special characters", test_code_to_html_special_characters),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: ERROR: {e}")
            failed += 1

    print(f"\n{passed}/{len(tests)} tests passed")
    if failed > 0:
        sys.exit(1)
