# PDF Tools

A comprehensive command-line utility for downloading, merging, and compressing PDF files.

## Features

- **Download**: Scrape PDF files from any webpage
- **Merge**: Combine PDF files into a specified number of evenly-sized output files
- **Compress**: Reduce PDF file sizes using various quality settings
- **Aggressive Compression**: Special handling for large files (>100MB)
- **All-in-one**: Run the full workflow from download to compression in a single command

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/pdf-tools.git
   cd pdf-tools
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Download PDFs from a URL

```
python pdf_tools.py download <URL> [options]
```

Options:
- `--output`, `-o`: Output directory for downloaded PDFs (default: auto-generated based on URL)
- `--workers`, `-w`: Number of parallel download workers (default: 10)

Example:
```
python pdf_tools.py download https://www.archives.gov/research/jfk/release --output JFK_PDFs
```

### Merge PDFs into evenly-sized files

```
python pdf_tools.py merge [options]
```

Options:
- `--input`, `-i`: Input directory containing PDFs (default: most recent download directory)
- `--output`, `-o`: Output directory for merged PDFs (default: Merged_PDFs)
- `--count`, `-c`: Number of output files to create (default: 250)

Example:
```
python pdf_tools.py merge --input JFK_PDFs --output Merged_JFK_PDFs --count 100
```

### Compress PDFs to reduce file size

```
python pdf_tools.py compress [options]
```

Options:
- `--input`, `-i`: Input directory containing PDFs
- `--output`, `-o`: Output directory for compressed PDFs (default: Compressed_PDFs)
- `--quality`, `-q`: Compression quality - screen, ebook, printer, prepress (default: screen)
- `--workers`, `-w`: Number of parallel compression workers (default: 4)

Example:
```
python pdf_tools.py compress --input Merged_JFK_PDFs --quality ebook
```

### Run the full workflow (download, merge, compress)

```
python pdf_tools.py all <URL> [options]
```

Options:
- `--output`, `-o`: Final output directory (default: Processed_PDFs)
- `--count`, `-c`: Number of merged files to create (default: 250)
- `--quality`, `-q`: Compression quality (default: screen)
- `--download-workers`, `-dw`: Number of download workers (default: 10)
- `--compress-workers`, `-cw`: Number of compression workers (default: auto)

Example:
```
python pdf_tools.py all https://www.archives.gov/research/jfk/release --output JFK_Final --count 100
```

## Compression Quality Settings

- `screen`: Lowest quality, smallest file size (72 dpi)
- `ebook`: Medium quality, good file size (150 dpi)
- `printer`: Better quality, larger file size (300 dpi)
- `prepress`: Best quality, largest file size (300 dpi with additional features)

## Requirements

- Python 3.6+
- PyPDF2
- Requests
- BeautifulSoup4
- Ghostscript (must be installed on your system)

## License

MIT 