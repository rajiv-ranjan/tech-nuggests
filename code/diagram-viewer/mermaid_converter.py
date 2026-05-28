#!/usr/bin/env python3
"""
Mermaid Diagram Converter and Viewer
Converts Mermaid (.mmd, .mermaid) files to SVG and HTML, generates an index page, and optionally serves them via HTTP
"""

import subprocess
import sys
import logging
import argparse
import http.server
import socketserver
import webbrowser
import os
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# Set up logger
logger = logging.getLogger(__name__)


class MermaidConverter:
    """Converts Mermaid diagram files to SVG and HTML formats"""

    def __init__(self, root_dir: Path, dry_run: bool = False):
        """
        Initialize the Mermaid Converter

        Args:
            root_dir: Root directory to scan for .mmd and .mermaid files
            dry_run: If True, only show what would be converted without generating files
        """
        self.root_dir = root_dir
        self.dry_run = dry_run

    def check_mmdc_installed(self) -> bool:
        """
        Check if mmdc (mermaid-cli) is installed

        Returns:
            True if mmdc is installed, False otherwise
        """
        try:
            result = subprocess.run(
                ['mmdc', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.debug(f"mmdc version: {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            logger.error("✗ mmdc (mermaid-cli) is not installed")
            logger.error("Install it with: npm install -g @mermaid-js/mermaid-cli")
            return False
        except Exception as e:
            logger.error(f"Error checking mmdc: {e}")
            return False

        return False

    def find_mermaid_files(self) -> List[Path]:
        """
        Recursively find all .mmd and .mermaid files

        Returns:
            List of Path objects for mermaid files
        """
        mermaid_files = []

        for pattern in ['**/*.mmd', '**/*.mermaid']:
            try:
                mermaid_files.extend(self.root_dir.glob(pattern))
            except Exception as e:
                logger.warning(f"Error scanning for {pattern}: {e}")

        # Sort for consistent ordering
        mermaid_files.sort()

        logger.debug(f"Found {len(mermaid_files)} mermaid files")
        return mermaid_files

    def _run_mmdc(self, input_path: Path, output_path: Path) -> bool:
        """
        Execute mmdc CLI command to convert a mermaid file

        Args:
            input_path: Path to input .mmd file
            output_path: Path to output file (SVG or HTML)

        Returns:
            True if conversion succeeded, False otherwise
        """
        cmd = ['mmdc', '-i', str(input_path), '-o', str(output_path)]

        logger.debug(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.debug(f"✓ Generated {output_path.name}")
                return True
            else:
                logger.error(f"✗ Failed to generate {output_path.name}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"✗ Timeout converting {input_path.name}")
            return False
        except Exception as e:
            logger.error(f"✗ Error converting {input_path.name}: {e}")
            return False

    def _create_html_from_svg(self, svg_path: Path, html_path: Path, title: str) -> bool:
        """
        Create a self-contained HTML file that embeds the SVG

        Args:
            svg_path: Path to the SVG file
            html_path: Path where HTML should be written
            title: Title for the HTML page

        Returns:
            True if HTML was created successfully, False otherwise
        """
        try:
            svg_content = svg_path.read_text(encoding='utf-8')

            html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f7fa;
            margin: 0;
            padding: 32px;
        }}
        h1 {{
            color: #1a1a2e;
            font-size: 1.5rem;
            margin: 0 0 24px;
        }}
        .diagram-container {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 16px rgba(0,0,0,0.08);
            padding: 40px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="diagram-container">
        {svg_content}
    </div>
</body>
</html>
'''

            html_path.write_text(html_template, encoding='utf-8')
            logger.debug(f"✓ Created {html_path.name}")
            return True

        except Exception as e:
            logger.error(f"✗ Error creating HTML for {svg_path.name}: {e}")
            return False

    def convert_file(self, mmd_path: Path) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Convert a single .mmd file to SVG and HTML in a generated-diagram folder

        Args:
            mmd_path: Path to the .mmd or .mermaid file

        Returns:
            Tuple of (svg_path, html_path) if successful, (None, None) on error
        """
        # Create generated-diagram folder in the same directory as the .mmd file
        generated_dir = mmd_path.parent / 'generated-diagram'
        svg_path = generated_dir / f"{mmd_path.stem}.svg"
        html_path = generated_dir / f"{mmd_path.stem}.html"

        if self.dry_run:
            logger.info(f"[DRY RUN] Would convert: {mmd_path.relative_to(self.root_dir)}")
            logger.info(f"          → {svg_path.relative_to(self.root_dir)}")
            logger.info(f"          → {html_path.relative_to(self.root_dir)}")
            return (svg_path, html_path)

        logger.info(f"Converting: {mmd_path.relative_to(self.root_dir)}")

        # Create generated-diagram directory if it doesn't exist
        try:
            generated_dir.mkdir(exist_ok=True)
            logger.debug(f"Created directory: {generated_dir.relative_to(self.root_dir)}")
        except Exception as e:
            logger.error(f"✗ Error creating directory {generated_dir}: {e}")
            return (None, None)

        # Generate SVG using mmdc
        svg_success = self._run_mmdc(mmd_path, svg_path)

        if not svg_success:
            return (None, None)

        # Create self-contained HTML from SVG
        title = mmd_path.stem.replace('-', ' ').replace('_', ' ').title()
        html_success = self._create_html_from_svg(svg_path, html_path, title)

        if svg_success and html_success:
            logger.info(f"✓ {mmd_path.relative_to(self.root_dir)} → SVG, HTML")
            return (svg_path, html_path)
        else:
            return (None, None)

    def convert_all(self) -> Dict[str, int]:
        """
        Convert all mermaid files found in the root directory

        Returns:
            Dictionary with conversion statistics
        """
        mermaid_files = self.find_mermaid_files()

        if not mermaid_files:
            logger.info("No .mmd or .mermaid files found")
            return {'total': 0, 'success': 0, 'failed': 0}

        logger.info(f"Found {len(mermaid_files)} mermaid file(s)")

        stats = {'total': len(mermaid_files), 'success': 0, 'failed': 0}

        for mmd_file in mermaid_files:
            svg_path, html_path = self.convert_file(mmd_file)

            if svg_path and html_path:
                stats['success'] += 1
            else:
                stats['failed'] += 1

        return stats


class DiagramIndexGenerator:
    """Generates an index HTML page with navigation to all diagram HTML files"""

    def __init__(self, root_dir: Path):
        """
        Initialize the Diagram Index Generator

        Args:
            root_dir: Root directory to scan for generated HTML files
        """
        self.root_dir = root_dir

    def find_diagram_htmls(self) -> List[Path]:
        """
        Find all generated .html files from .mmd conversions in generated-diagram folders

        Returns:
            List of Path objects for HTML diagram files
        """
        html_files = []

        # Look specifically in generated-diagram folders
        for generated_dir in self.root_dir.glob('**/generated-diagram'):
            for html_file in generated_dir.glob('*.html'):
                # Check if there's a corresponding .mmd or .mermaid file in the parent directory
                parent_dir = generated_dir.parent
                mmd_file = parent_dir / f"{html_file.stem}.mmd"
                mermaid_file = parent_dir / f"{html_file.stem}.mermaid"

                if mmd_file.exists() or mermaid_file.exists():
                    html_files.append(html_file)

        html_files.sort()
        logger.debug(f"Found {len(html_files)} diagram HTML files")
        return html_files

    def _group_by_directory(self, html_files: List[Path]) -> Dict[str, List[Path]]:
        """
        Group HTML files by their source directory (parent of generated-diagram)

        Args:
            html_files: List of HTML file paths

        Returns:
            Dictionary mapping directory paths to list of HTML files
        """
        grouped = {}

        for html_file in html_files:
            # HTML files are in generated-diagram folder, group by parent of that
            source_dir = html_file.parent.parent
            dir_rel_path = str(source_dir.relative_to(self.root_dir))

            if dir_rel_path not in grouped:
                grouped[dir_rel_path] = []

            grouped[dir_rel_path].append(html_file)

        return grouped

    def _create_html_structure(self, diagrams_by_dir: Dict[str, List[Path]]) -> str:
        """
        Create the HTML structure for the index page

        Args:
            diagrams_by_dir: Dictionary of diagrams grouped by directory

        Returns:
            HTML string
        """
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '    <title>Tech Nuggests - Diagram Index</title>',
            '    <style>',
            '        * { margin: 0; padding: 0; box-sizing: border-box; }',
            '        body {',
            '            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;',
            '            line-height: 1.6;',
            '            color: #333;',
            '            background: #f5f5f5;',
            '            padding: 20px;',
            '        }',
            '        .container {',
            '            max-width: 1200px;',
            '            margin: 0 auto;',
            '            background: white;',
            '            padding: 30px;',
            '            border-radius: 8px;',
            '            box-shadow: 0 2px 4px rgba(0,0,0,0.1);',
            '        }',
            '        h1 {',
            '            color: #2c3e50;',
            '            margin-bottom: 10px;',
            '            border-bottom: 3px solid #3498db;',
            '            padding-bottom: 10px;',
            '        }',
            '        .subtitle {',
            '            color: #7f8c8d;',
            '            margin-bottom: 30px;',
            '        }',
            '        .directory {',
            '            margin-bottom: 25px;',
            '        }',
            '        .directory-header {',
            '            background: #ecf0f1;',
            '            padding: 12px 15px;',
            '            border-left: 4px solid #3498db;',
            '            cursor: pointer;',
            '            font-weight: 600;',
            '            color: #2c3e50;',
            '            user-select: none;',
            '            display: flex;',
            '            align-items: center;',
            '            gap: 8px;',
            '        }',
            '        .directory-header:hover {',
            '            background: #d5dbdb;',
            '        }',
            '        .directory-header::before {',
            '            content: "▼";',
            '            display: inline-block;',
            '            transition: transform 0.2s;',
            '        }',
            '        .directory-header.collapsed::before {',
            '            transform: rotate(-90deg);',
            '        }',
            '        .diagram-list {',
            '            list-style: none;',
            '            padding: 15px 15px 15px 35px;',
            '        }',
            '        .diagram-list.hidden {',
            '            display: none;',
            '        }',
            '        .diagram-list li {',
            '            margin: 8px 0;',
            '        }',
            '        .diagram-list a {',
            '            color: #3498db;',
            '            text-decoration: none;',
            '            padding: 6px 10px;',
            '            display: inline-block;',
            '            border-radius: 4px;',
            '            transition: all 0.2s;',
            '        }',
            '        .diagram-list a:hover {',
            '            background: #3498db;',
            '            color: white;',
            '            transform: translateX(5px);',
            '        }',
            '        .empty-state {',
            '            text-align: center;',
            '            padding: 60px 20px;',
            '            color: #95a5a6;',
            '        }',
            '        .search-box {',
            '            margin-bottom: 25px;',
            '        }',
            '        .search-box input {',
            '            width: 100%;',
            '            padding: 12px 15px;',
            '            border: 2px solid #ecf0f1;',
            '            border-radius: 6px;',
            '            font-size: 16px;',
            '            transition: border-color 0.2s;',
            '        }',
            '        .search-box input:focus {',
            '            outline: none;',
            '            border-color: #3498db;',
            '        }',
            '        .stats {',
            '            background: #e8f5e9;',
            '            padding: 12px 15px;',
            '            border-radius: 6px;',
            '            margin-bottom: 20px;',
            '            color: #2e7d32;',
            '            border-left: 4px solid #4caf50;',
            '        }',
            '    </style>',
            '</head>',
            '<body>',
            '    <div class="container">',
            '        <h1>📊 Tech Nuggests - Diagram Index</h1>',
            '        <p class="subtitle">Browse all Mermaid diagrams in the repository</p>',
        ]

        if not diagrams_by_dir:
            html_parts.extend([
                '        <div class="empty-state">',
                '            <h2>No diagrams found</h2>',
                '            <p>Run the converter to generate diagrams from .mmd files</p>',
                '        </div>',
            ])
        else:
            total_diagrams = sum(len(files) for files in diagrams_by_dir.values())
            html_parts.append(f'        <div class="stats">Found {total_diagrams} diagram(s) in {len(diagrams_by_dir)} location(s)</div>')

            html_parts.extend([
                '        <div class="search-box">',
                '            <input type="text" id="searchInput" placeholder="Search diagrams..." onkeyup="filterDiagrams()">',
                '        </div>',
                '        <div id="diagramsContainer">',
            ])

            for dir_path in sorted(diagrams_by_dir.keys()):
                files = diagrams_by_dir[dir_path]
                html_parts.append(f'            <div class="directory" data-path="{dir_path}">')
                html_parts.append(f'                <div class="directory-header" onclick="toggleDirectory(this)">{dir_path}</div>')
                html_parts.append('                <ul class="diagram-list">')

                for html_file in files:
                    rel_path = html_file.relative_to(self.root_dir)
                    file_name = html_file.stem
                    html_parts.append(f'                    <li><a href="{rel_path}" target="_blank">{file_name}</a></li>')

                html_parts.append('                </ul>')
                html_parts.append('            </div>')

            html_parts.append('        </div>')

        html_parts.extend([
            '    </div>',
            '    <script>',
            '        function toggleDirectory(header) {',
            '            header.classList.toggle("collapsed");',
            '            const list = header.nextElementSibling;',
            '            list.classList.toggle("hidden");',
            '        }',
            '        function filterDiagrams() {',
            '            const input = document.getElementById("searchInput");',
            '            const filter = input.value.toLowerCase();',
            '            const directories = document.querySelectorAll(".directory");',
            '            ',
            '            directories.forEach(dir => {',
            '                const path = dir.dataset.path.toLowerCase();',
            '                const links = dir.querySelectorAll(".diagram-list a");',
            '                let hasMatch = false;',
            '                ',
            '                links.forEach(link => {',
            '                    const text = link.textContent.toLowerCase();',
            '                    if (text.includes(filter) || path.includes(filter)) {',
            '                        link.parentElement.style.display = "";',
            '                        hasMatch = true;',
            '                    } else {',
            '                        link.parentElement.style.display = "none";',
            '                    }',
            '                });',
            '                ',
            '                dir.style.display = hasMatch ? "" : "none";',
            '            });',
            '        }',
            '    </script>',
            '</body>',
            '</html>',
        ])

        return '\n'.join(html_parts)

    def generate_index(self, output_path: Path) -> None:
        """
        Generate the diagram-index.html file

        Args:
            output_path: Path where the index HTML should be written
        """
        logger.info("Generating diagram index...")

        html_files = self.find_diagram_htmls()
        diagrams_by_dir = self._group_by_directory(html_files)

        html_content = self._create_html_structure(diagrams_by_dir)

        output_path.write_text(html_content, encoding='utf-8')
        logger.info(f"✓ Generated index: {output_path}")


class DiagramHTTPServer:
    """Simple HTTP server to serve diagram files"""

    def __init__(self, root_dir: Path):
        """
        Initialize the HTTP server

        Args:
            root_dir: Root directory to serve files from
        """
        self.root_dir = root_dir

    def start(self, port: int = 8080, open_browser: bool = True) -> None:
        """
        Start the HTTP server and optionally open browser

        Args:
            port: Port number to listen on
            open_browser: Whether to automatically open browser
        """
        os.chdir(self.root_dir)

        handler = http.server.SimpleHTTPRequestHandler

        try:
            with socketserver.TCPServer(("", port), handler) as httpd:
                url = f"http://localhost:{port}/diagram-index.html"

                logger.info(f"✓ Serving diagrams at: {url}")
                logger.info("Press Ctrl+C to stop the server")

                if open_browser:
                    try:
                        webbrowser.open(url)
                        logger.info("✓ Opened browser")
                    except Exception as e:
                        logger.warning(f"Could not open browser: {e}")
                        logger.info(f"Please navigate to: {url}")

                httpd.serve_forever()

        except OSError as e:
            if 'Address already in use' in str(e):
                logger.error(f"✗ Port {port} is already in use")
                logger.error(f"Try a different port with: --port <number>")
            else:
                logger.error(f"✗ Error starting server: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            logger.info("\n✓ Server stopped")
            sys.exit(0)


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging settings

    Args:
        verbose: If True, set log level to DEBUG, otherwise INFO
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(message)s'
    )


def main() -> None:
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(
        description='Convert Mermaid diagrams to SVG/HTML and serve them via HTTP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Convert all diagrams (dry run)
  %(prog)s --dry-run

  # Convert all diagrams
  %(prog)s

  # Convert and start HTTP server
  %(prog)s --serve

  # Start server on custom port
  %(prog)s --serve --port 3000

  # Convert with verbose logging
  %(prog)s --verbose
        '''
    )

    parser.add_argument(
        '--root-dir',
        type=Path,
        default=None,
        help='Root directory to scan (default: parent of this script)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be converted without generating files'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--serve',
        action='store_true',
        help='Start HTTP server after conversion'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='HTTP server port (default: 8080)'
    )

    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not auto-open browser when serving'
    )

    parser.add_argument(
        '--skip-convert',
        action='store_true',
        help='Skip conversion, only serve existing diagrams'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Determine root directory
    if args.root_dir:
        root_dir = args.root_dir.resolve()
    else:
        # Default to parent directory of this script (tech-nuggests root)
        script_dir = Path(__file__).parent
        root_dir = script_dir.parent.parent

    if not root_dir.exists():
        logger.error(f"✗ Root directory does not exist: {root_dir}")
        sys.exit(1)

    logger.info(f"Root directory: {root_dir}")

    # Convert diagrams (unless --skip-convert)
    if not args.skip_convert:
        converter = MermaidConverter(root_dir, dry_run=args.dry_run)

        # Check if mmdc is installed
        if not args.dry_run and not converter.check_mmdc_installed():
            sys.exit(1)

        # Convert all files
        stats = converter.convert_all()

        if not args.dry_run:
            logger.info(f"\nConversion complete: {stats['success']}/{stats['total']} succeeded, {stats['failed']} failed")

        # Generate index page (unless dry run)
        if not args.dry_run:
            index_generator = DiagramIndexGenerator(root_dir)
            index_path = root_dir / 'diagram-index.html'
            index_generator.generate_index(index_path)

    # Start HTTP server if requested
    if args.serve:
        server = DiagramHTTPServer(root_dir)
        server.start(port=args.port, open_browser=not args.no_browser)


if __name__ == '__main__':
    main()
