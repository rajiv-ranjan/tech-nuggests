# Diagram Viewer

A Python utility that converts Mermaid diagram files (`.mmd`, `.mermaid`) to offline-viewable SVG, HTML, PNG, and PDF formats, generates a navigable index page, and optionally serves them via HTTP.

## Features

- 📊 **Batch Conversion**: Recursively scans and converts all Mermaid files in the repository
- 🎨 **Multiple Formats**: Generates SVG (vector graphics), self-contained HTML, PNG (high-quality raster at 4x scale), and PDF (vector-based)
- 📁 **Organized Output**: Generated files are placed in `generated-diagram` folders, keeping source and output separated
- 📑 **Index Page**: Auto-generates a navigable index with collapsible directory tree
- 🌐 **HTTP Server**: Built-in server for browsing diagrams in your browser
- ⚡ **Fast**: Uses `uv` for Python package management
- 🔍 **Search**: Filter diagrams by name or path in the index page
- 📴 **Offline**: Generated files work without internet connection
- 🗑️ **Clean Repository**: Auto-configured `.gitignore` keeps generated files out of version control

## Prerequisites

### Required

1. **Python 3.8+**
   ```bash
   python3 --version
   ```

2. **uv** (Python package manager)
   ```bash
   # Install uv if not already installed
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Node.js & npm** (for mermaid-cli)
   ```bash
   node --version
   npm --version
   ```

4. **mermaid-cli** (mmdc command)
   ```bash
   npm install -g @mermaid-js/mermaid-cli
   ```

### Verify Installation

```bash
# Check all prerequisites
uv --version
mmdc --version
```

## Installation

```bash
cd /path/to/tech-nuggests/code/diagram-viewer

# Initialize uv environment
uv sync
```

## Usage

### Basic Conversion

Convert all `.mmd` and `.mermaid` files to SVG, HTML, PNG, and PDF:

```bash
uv run python mermaid_converter.py
```

This will:
- Scan the entire `tech-nuggests` repository
- Convert each `.mmd` file to `.svg`, `.html`, `.png` (4x scale), and `.pdf` in a `generated-diagram` subfolder
- Generate `diagram-index.html` in the repository root

### Dry Run

Preview what would be converted without generating files:

```bash
uv run python mermaid_converter.py --dry-run
```

### Verbose Mode

See detailed logging output:

```bash
uv run python mermaid_converter.py --verbose
```

### Convert and Serve

Convert diagrams and start HTTP server with auto-open browser:

```bash
uv run python mermaid_converter.py --serve
```

This will:
- Convert all diagrams
- Generate the index page
- Start HTTP server at `http://localhost:8080`
- Automatically open your browser to the index page

### Serve Only (Skip Conversion)

Start HTTP server for existing diagrams without re-converting:

```bash
uv run python mermaid_converter.py --serve --skip-convert
```

### Custom Port

Use a different port for the HTTP server:

```bash
uv run python mermaid_converter.py --serve --port 3000
```

### No Auto-Browser

Start server without automatically opening the browser:

```bash
uv run python mermaid_converter.py --serve --no-browser
```

### Custom Root Directory

Scan a different directory:

```bash
uv run python mermaid_converter.py --root-dir /path/to/other/directory
```

## Generated Files

### Per Mermaid File

For each `.mmd` or `.mermaid` file, four files are generated in a `generated-diagram` subfolder:

- `filename.svg` - Vector graphic (scalable, can be embedded in docs)
- `filename.html` - Self-contained HTML with embedded diagram
- `filename.png` - High-quality raster image (4x scale for crisp display)
- `filename.pdf` - Vector-based PDF (perfect for printing and presentations, no quality loss)

The `generated-diagram` folder is automatically created in the same directory as the source `.mmd` file, keeping generated files cleanly separated from source files.

Example:
```
advance-cluster-security/
└── vulnerability-management/
    ├── roxctl-scan-v1.mmd        # Source
    └── generated-diagram/        # Auto-created folder
        ├── roxctl-scan-v1.svg    # Generated SVG
        ├── roxctl-scan-v1.html   # Generated HTML
        ├── roxctl-scan-v1.png    # Generated PNG (4x quality)
        └── roxctl-scan-v1.pdf    # Generated PDF
```

**Note:** The `generated-diagram` folders are automatically added to `.gitignore` to keep your repository clean.

### Index Page

A single `diagram-index.html` file is created in the repository root:

```
tech-nuggests/
├── diagram-index.html           # Auto-generated index
├── advance-cluster-security/
└── code/
```

The index page features:
- Collapsible directory tree navigation organized by source directory
- Search/filter functionality
- Responsive design
- Direct links to all diagrams in their `generated-diagram` folders

### Benefits of the Folder Structure

**Clean Separation:**
- Source `.mmd` files stay in your main directories
- Generated files are isolated in `generated-diagram` folders
- Easy to `.gitignore` all generated content

**Easy Cleanup:**
- Delete any `generated-diagram` folder to remove all outputs for that location
- Re-run the converter to regenerate fresh files

**Organized Repository:**
- No mixing of source and generated files
- Clear distinction between what to edit (`.mmd`) and what is auto-generated (`.svg`, `.html`, `.png`, `.pdf`)

## Command-Line Options

| Option | Description |
|--------|-------------|
| `--root-dir PATH` | Root directory to scan (default: `tech-nuggests/`) |
| `--dry-run` | Show what would be converted without generating files |
| `--verbose` | Enable verbose logging (DEBUG level) |
| `--serve` | Start HTTP server after conversion |
| `--port PORT` | HTTP server port (default: 8080) |
| `--no-browser` | Don't auto-open browser when serving |
| `--skip-convert` | Skip conversion, only serve existing diagrams |

## Troubleshooting

### `mmdc: command not found`

Install mermaid-cli:
```bash
npm install -g @mermaid-js/mermaid-cli
```

### Port Already in Use

Use a different port:
```bash
uv run python mermaid_converter.py --serve --port 3001
```

### Permission Denied

Ensure you have write permissions in the directories where diagrams are located.

### Conversion Timeout

Some complex diagrams may timeout. The default timeout is 30 seconds per diagram. Check the diagram syntax if conversion fails.

### HTML Files Not Rendering

Make sure you're viewing the generated `.html` files (not the source `.mmd` files). The HTML files should work offline without internet.

### Old Generated Files in Wrong Location

If you had previously generated files directly alongside `.mmd` files (before the `generated-diagram` folder update), you can safely delete them:

```bash
# From the tech-nuggests root directory
find . -name "*.mmd" -exec sh -c 'rm -f "${1%.mmd}.svg" "${1%.mmd}.html" "${1%.mmd}.png" "${1%.mmd}.pdf"' _ {} \;
```

Then re-run the converter to generate fresh files in the new `generated-diagram` folders.

## Development

### Project Structure

```
diagram-viewer/
├── mermaid_converter.py    # Main script
├── pyproject.toml          # Project metadata
├── uv.lock                 # uv lockfile
├── .gitignore              # Python ignores
├── .venv/                  # Virtual environment (auto-created)
└── README.md               # This file
```

### Code Style

The project follows Python best practices:
- Type hints on all functions
- Comprehensive logging
- Error handling with meaningful messages
- Docstrings on all classes and methods

## Examples

### Example 1: Quick Conversion

```bash
cd /path/to/tech-nuggests/code/diagram-viewer
uv run python mermaid_converter.py
```

Output:
```
Root directory: /Users/you/tech-nuggests
Found 4 mermaid file(s)
Converting: advance-cluster-security/vulnerability-management/roxctl-scan-v1.mmd
✓ advance-cluster-security/vulnerability-management/roxctl-scan-v1.mmd → SVG, HTML, PNG (4x), PDF
...

Conversion complete: 4/4 succeeded, 0 failed
Generating diagram index...
✓ Generated index: /Users/you/tech-nuggests/diagram-index.html
```

### Example 2: Convert and Browse

```bash
uv run python mermaid_converter.py --serve
```

Output:
```
Root directory: /Users/you/tech-nuggests
Found 4 mermaid file(s)
...
Conversion complete: 4/4 succeeded, 0 failed
✓ Generated index: /Users/you/tech-nuggests/diagram-index.html
✓ Serving diagrams at: http://localhost:8080/diagram-index.html
✓ Opened browser
Press Ctrl+C to stop the server
```

### Example 3: Just Serve (No Conversion)

```bash
uv run python mermaid_converter.py --serve --skip-convert
```

Output:
```
Root directory: /Users/you/tech-nuggests
✓ Serving diagrams at: http://localhost:8080/diagram-index.html
✓ Opened browser
Press Ctrl+C to stop the server
```

## License

Part of the tech-nuggests repository.

## Contributing

This is a utility tool for the tech-nuggests repository. Improvements and bug fixes are welcome.
