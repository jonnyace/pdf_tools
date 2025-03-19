#!/usr/bin/env python3
import requests
import os
import PyPDF2
import time
import subprocess
import shutil
import argparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

class PDFTools:
    """A comprehensive tool for downloading, merging, and compressing PDF files."""
    
    def __init__(self):
        """Initialize the PDFTools class."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
    
    # ==================== DOWNLOAD FUNCTIONS ====================
    
    def download_pdf(self, pdf_url, download_dir, session, num_retries=3):
        """Download a single PDF file with retry logic."""
        # Get the filename from the URL
        filename = os.path.join(download_dir, pdf_url.split('/')[-1].split('?')[0])
        # Clean filename
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        
        retry_count = 0
        while retry_count < num_retries:
            try:
                # Download the PDF
                pdf_response = session.get(pdf_url, stream=True)
                pdf_response.raise_for_status()
                
                with open(filename, 'wb') as f:
                    for chunk in pdf_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                return True, filename
            except requests.RequestException as e:
                retry_count += 1
                if retry_count < num_retries:
                    print(f"Error downloading {pdf_url}: {e}. Retrying ({retry_count}/{num_retries})...")
                    time.sleep(2)  # Wait before retrying
                else:
                    print(f"Failed to download {pdf_url} after {num_retries} attempts: {e}")
                    return False, None
            except Exception as e:
                print(f"Error processing {pdf_url}: {e}")
                return False, None
    
    def download_pdfs_from_url(self, target_url, download_dir=None, max_workers=10):
        """Download all PDF files from a given URL."""
        print(f"Starting to scrape PDFs from: {target_url}")
        
        # Create a downloads directory if not specified
        if download_dir is None:
            download_dir = f"PDF_Downloads_{os.path.basename(target_url)}"
        os.makedirs(download_dir, exist_ok=True)
        
        start_time = time.time()
        
        try:
            # Create a session for better performance
            with requests.Session() as session:
                session.headers.update(self.headers)
                
                # Fetch the webpage
                print("Fetching webpage...")
                response = session.get(target_url)
                response.raise_for_status()
                
                # Parse HTML content
                print("Parsing HTML content...")
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all links
                pdf_urls = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    
                    # Check if it's a PDF link
                    if re.search(r'\.pdf(?:$|\?)', href, re.IGNORECASE):
                        # Convert relative URLs to absolute URLs
                        full_url = urljoin(target_url, href)
                        pdf_urls.append(full_url)
                
                # Remove duplicates
                pdf_urls = list(set(pdf_urls))
                
                print(f"Found {len(pdf_urls)} unique PDF links on the page.")
                
                if not pdf_urls:
                    print("No PDF links found. Please check the website structure.")
                    return None
                
                # Download PDFs in parallel
                print(f"Downloading {len(pdf_urls)} PDF files to {download_dir}...")
                
                successful_downloads = 0
                failed_downloads = 0
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_url = {
                        executor.submit(self.download_pdf, url, download_dir, session): url 
                        for url in pdf_urls
                    }
                    
                    for i, future in enumerate(as_completed(future_to_url), 1):
                        url = future_to_url[future]
                        try:
                            success, filename = future.result()
                            if success:
                                successful_downloads += 1
                                print(f"Progress: [{i}/{len(pdf_urls)}] Downloaded: {os.path.basename(filename)}")
                            else:
                                failed_downloads += 1
                                print(f"Progress: [{i}/{len(pdf_urls)}] Failed to download: {url}")
                        except Exception as e:
                            failed_downloads += 1
                            print(f"Progress: [{i}/{len(pdf_urls)}] Error processing {url}: {e}")
                
                elapsed_time = time.time() - start_time
                print(f"\nDownload complete in {elapsed_time:.2f} seconds!")
                print(f"Successfully downloaded: {successful_downloads} files")
                print(f"Failed downloads: {failed_downloads} files")
                print(f"All files saved to: {download_dir}")
                
                return download_dir
        
        except requests.RequestException as e:
            print(f"Error fetching webpage {target_url}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            
        return None
    
    # ==================== PDF ANALYSIS FUNCTIONS ====================
    
    def get_pdf_size_info(self, pdf_path):
        """Get the file size and number of pages for a PDF."""
        try:
            file_size = os.path.getsize(pdf_path)
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                num_pages = len(reader.pages)
            return file_size, num_pages, pdf_path
        except Exception as e:
            print(f"Error analyzing {pdf_path}: {str(e)}")
            return 0, 0, pdf_path
    
    # ==================== MERGE FUNCTIONS ====================
    
    def merge_pdf_bucket(self, bucket, output_file):
        """Merge a bucket of PDFs into a single file."""
        pdf_merger = PyPDF2.PdfMerger()
        merged_count = 0
        
        for pdf_file in bucket:
            try:
                pdf_merger.append(pdf_file)
                merged_count += 1
            except Exception as e:
                print(f"Error adding {pdf_file} to {output_file}: {str(e)}")
        
        if merged_count > 0:
            try:
                pdf_merger.write(output_file)
                pdf_merger.close()
                print(f"Created: {output_file} with {merged_count} PDFs")
                return True
            except Exception as e:
                print(f"Error writing {output_file}: {str(e)}")
        else:
            print(f"No valid PDFs to merge for {output_file}")
        
        return False
    
    def merge_pdfs(self, pdf_dir=None, output_dir="Merged_PDFs", num_output_files=250):
        """Merge PDFs into a specified number of evenly-sized output files."""
        start_time = time.time()
        
        # Look for the directory with the downloaded PDFs if not specified
        if pdf_dir is None:
            pdf_dirs = [d for d in os.listdir('.') if os.path.isdir(d) and d.startswith('PDF_Downloads_')]
            if not pdf_dirs:
                print("No PDF download directories found. Please run the download function first or specify a directory.")
                return None
            pdf_dir = pdf_dirs[-1]  # Use the most recent directory
        
        print(f"Using PDF directory: {pdf_dir}")
        
        # Get all PDF files in the directory
        all_files = [os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
        
        if not all_files:
            print(f"No PDF files found in {pdf_dir}.")
            return None
        
        print(f"Found {len(all_files)} PDF files. Analyzing...")
        
        # Filter for valid PDFs and get their info in parallel
        valid_pdfs = []
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = [executor.submit(self.get_pdf_size_info, pdf_file) for pdf_file in all_files]
            for future in as_completed(futures):
                file_size, num_pages, pdf_path = future.result()
                if file_size > 0:  # Valid PDFs have size > 0
                    valid_pdfs.append((file_size, num_pages, pdf_path))
        
        print(f"Found {len(valid_pdfs)} valid PDFs")
        
        if not valid_pdfs:
            print("No valid PDFs to merge.")
            return None
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Calculate how many files to create (at most the requested number, but could be fewer)
        num_output_files = min(num_output_files, len(valid_pdfs))
        print(f"Will create up to {num_output_files} merged PDF files")
        
        # Strategy: Use a greedy algorithm to distribute files evenly
        # Create empty buckets
        buckets = [[] for _ in range(num_output_files)]
        bucket_sizes = [0] * num_output_files
        
        # Sort files by size (largest first)
        valid_pdfs.sort(reverse=True)
        
        # Assign each file to the bucket with the smallest current total size
        for file_size, num_pages, file_path in valid_pdfs:
            # Find the bucket with the smallest total size
            min_idx = bucket_sizes.index(min(bucket_sizes))
            buckets[min_idx].append(file_path)
            bucket_sizes[min_idx] += file_size
        
        # Now merge PDFs in each bucket
        successfully_merged = 0
        
        for i, bucket in enumerate(buckets):
            if not bucket:  # Skip empty buckets
                continue
                
            output_file = os.path.join(output_dir, f"merged_{i+1:03d}.pdf")
            if self.merge_pdf_bucket(bucket, output_file):
                successfully_merged += 1
        
        elapsed_time = time.time() - start_time
        print(f"\nMerge complete in {elapsed_time:.2f} seconds!")
        print(f"Created {successfully_merged} merged PDF files in {output_dir}")
        
        return output_dir
    
    # ==================== COMPRESSION FUNCTIONS ====================
    
    def compress_pdf(self, input_file, output_file, quality='screen'):
        """Compress a PDF file using Ghostscript."""
        quality_settings = {
            'screen': '/screen',  # 72 dpi - lowest quality, smallest size
            'ebook': '/ebook',    # 150 dpi - medium quality, good size
            'printer': '/printer',  # 300 dpi - better quality, larger size
            'prepress': '/prepress'  # 300 dpi - best quality, largest size
        }
        
        gs_setting = quality_settings.get(quality, '/ebook')
        
        try:
            cmd = [
                'gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                f'-dPDFSETTINGS={gs_setting}', '-dNOPAUSE', '-dQUIET', '-dBATCH',
                f'-sOutputFile={output_file}', input_file
            ]
            
            subprocess.run(cmd, check=True)
            
            original_size = os.path.getsize(input_file)
            compressed_size = os.path.getsize(output_file)
            reduction = (1 - compressed_size / original_size) * 100
            
            print(f"Compressed {os.path.basename(input_file)} from {original_size/1024/1024:.2f}MB to {compressed_size/1024/1024:.2f}MB ({reduction:.2f}% reduction)")
            return True, original_size, compressed_size
        except subprocess.CalledProcessError as e:
            print(f"Error compressing {input_file}: {str(e)}")
            # If compression fails, copy the original file
            shutil.copy(input_file, output_file)
            original_size = os.path.getsize(input_file)
            return False, original_size, original_size
    
    def super_compress_pdf(self, input_file, output_file):
        """Aggressively compress a PDF file to make it smaller than 100MB."""
        print(f"Aggressively compressing {os.path.basename(input_file)}...")
        
        original_size = os.path.getsize(input_file)
        original_size_mb = original_size / (1024 * 1024)
        
        # First attempt: Strong compression with low resolution
        cmd = [
            'gs', '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/screen',  # Lowest quality setting
            '-dColorImageResolution=72',  # Lower image resolution
            '-dGrayImageResolution=72',
            '-dMonoImageResolution=72',
            '-dColorImageDownsampleType=/Bicubic',
            '-dGrayImageDownsampleType=/Bicubic',
            '-dMonoImageDownsampleType=/Bicubic',
            '-dOptimize=true',
            '-dEmbedAllFonts=true',
            '-dSubsetFonts=true',
            '-dNOPAUSE', '-dQUIET', '-dBATCH',
            f'-sOutputFile={output_file}',
            input_file
        ]
        
        try:
            subprocess.run(cmd, check=True)
            compressed_size = os.path.getsize(output_file)
            compressed_size_mb = compressed_size / (1024 * 1024)
            reduction = (1 - compressed_size / original_size) * 100
            
            print(f"Compressed from {original_size_mb:.2f}MB to {compressed_size_mb:.2f}MB ({reduction:.2f}% reduction)")
            
            # If still over 100MB, try more aggressive compression
            if compressed_size_mb > 100:
                print(f"File still over 100MB, trying more aggressive compression...")
                more_aggressive_output = output_file.replace('.pdf', '_more_compressed.pdf')
                
                # More aggressive compression with grayscale conversion
                cmd2 = [
                    'gs', '-sDEVICE=pdfwrite',
                    '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/screen',
                    '-dColorImageResolution=50',  # Even lower resolution
                    '-dGrayImageResolution=50',
                    '-dMonoImageResolution=50',
                    '-dDownsampleColorImages=true',
                    '-dDownsampleGrayImages=true',
                    '-dDownsampleMonoImages=true',
                    '-dColorConversionStrategy=/Gray',  # Convert to grayscale
                    '-dDetectDuplicateImages=true',
                    '-dCompressFonts=true',
                    '-dEmbedAllFonts=false',
                    '-dNOPAUSE', '-dQUIET', '-dBATCH',
                    f'-sOutputFile={more_aggressive_output}',
                    input_file
                ]
                
                subprocess.run(cmd2, check=True)
                more_compressed_size = os.path.getsize(more_aggressive_output)
                more_compressed_size_mb = more_compressed_size / (1024 * 1024)
                more_reduction = (1 - more_compressed_size / original_size) * 100
                
                print(f"More aggressive compression: {original_size_mb:.2f}MB to {more_compressed_size_mb:.2f}MB ({more_reduction:.2f}% reduction)")
                
                # Use the smallest file
                if more_compressed_size < compressed_size:
                    print(f"Using more aggressive compression result")
                    os.remove(output_file)
                    os.rename(more_aggressive_output, output_file)
                    compressed_size = more_compressed_size
                    compressed_size_mb = more_compressed_size_mb
                    reduction = more_reduction
                else:
                    print(f"Original compression was better, keeping that one")
                    if os.path.exists(more_aggressive_output):
                        os.remove(more_aggressive_output)
            
            return compressed_size_mb < 100, compressed_size_mb
            
        except subprocess.CalledProcessError as e:
            print(f"Error compressing {input_file}: {e}")
            return False, original_size_mb
    
    def compress_pdf_directory(self, input_dir, output_dir="Compressed_PDFs", quality='screen', max_workers=None):
        """Compress all PDFs in a directory."""
        start_time = time.time()
        
        # Make sure input directory exists
        if not os.path.exists(input_dir):
            print(f"Input directory '{input_dir}' not found.")
            return None
        
        # Get all PDF files in the directory
        pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print(f"No PDF files found in {input_dir}.")
            return None
        
        print(f"Found {len(pdf_files)} PDF files in {input_dir}")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Track total sizes
        total_original_size = 0
        total_compressed_size = 0
        successfully_compressed = 0
        
        # Check for large files first
        large_pdfs = []
        for filename in pdf_files:
            filepath = os.path.join(input_dir, filename)
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if size_mb > 100:
                large_pdfs.append((filepath, size_mb))
        
        # Process large files with super compression
        if large_pdfs:
            print(f"Found {len(large_pdfs)} PDFs over 100MB, applying aggressive compression...")
            for pdf_path, size in large_pdfs:
                filename = os.path.basename(pdf_path)
                output_path = os.path.join(output_dir, filename)
                
                print(f"\nProcessing large file: {filename} ({size:.2f}MB)")
                result, final_size = self.super_compress_pdf(pdf_path, output_path)
                
                if result:
                    print(f"Successfully compressed {filename} to under 100MB: {final_size:.2f}MB")
                else:
                    print(f"Warning: Could not compress {filename} below 100MB limit. Final size: {final_size:.2f}MB")
        
        # Regular compression for the rest of the files
        regular_pdfs = [f for f in pdf_files if os.path.join(input_dir, f) not in [p[0] for p in large_pdfs]]
        
        if not max_workers:
            max_workers = min(os.cpu_count(), 4)  # Limit to 4 workers by default to avoid memory issues
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create future to result mapping
            future_to_file = {}
            
            # Submit compression tasks
            for pdf_file in regular_pdfs:
                input_path = os.path.join(input_dir, pdf_file)
                output_path = os.path.join(output_dir, pdf_file)
                future = executor.submit(self.compress_pdf, input_path, output_path, quality)
                future_to_file[future] = input_path
            
            # Process results as they complete
            for future in as_completed(future_to_file):
                input_path = future_to_file[future]
                try:
                    success, original_size, compressed_size = future.result()
                    total_original_size += original_size
                    total_compressed_size += compressed_size
                    if success:
                        successfully_compressed += 1
                except Exception as e:
                    print(f"Error processing {input_path}: {str(e)}")
        
        elapsed_time = time.time() - start_time
        
        # Calculate total size reduction
        if total_original_size > 0:
            total_reduction = (1 - total_compressed_size / total_original_size) * 100
            print(f"\nTotal size reduction: {total_reduction:.2f}%")
            print(f"Original total size: {total_original_size/1024/1024/1024:.2f}GB")
            print(f"Compressed total size: {total_compressed_size/1024/1024/1024:.2f}GB")
        
        print(f"\nCompression completed in {elapsed_time:.2f} seconds!")
        print(f"Successfully compressed {successfully_compressed} out of {len(regular_pdfs)} regular PDF files")
        print(f"All compressed files are in: {output_dir}")
        
        return output_dir

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='PDF Tools: Download, Merge, and Compress PDF files')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download PDFs from a URL')
    download_parser.add_argument('url', help='URL to download PDFs from')
    download_parser.add_argument('--output', '-o', help='Output directory for downloaded PDFs')
    download_parser.add_argument('--workers', '-w', type=int, default=10, help='Number of parallel download workers')
    
    # Merge command
    merge_parser = subparsers.add_parser('merge', help='Merge PDFs into evenly-sized files')
    merge_parser.add_argument('--input', '-i', help='Input directory containing PDFs')
    merge_parser.add_argument('--output', '-o', default='Merged_PDFs', help='Output directory for merged PDFs')
    merge_parser.add_argument('--count', '-c', type=int, default=250, help='Number of output files to create')
    
    # Compress command
    compress_parser = subparsers.add_parser('compress', help='Compress PDFs to reduce file size')
    compress_parser.add_argument('--input', '-i', help='Input directory containing PDFs')
    compress_parser.add_argument('--output', '-o', default='Compressed_PDFs', help='Output directory for compressed PDFs')
    compress_parser.add_argument('--quality', '-q', choices=['screen', 'ebook', 'printer', 'prepress'], 
                                default='screen', help='Compression quality (lower = smaller size)')
    compress_parser.add_argument('--workers', '-w', type=int, help='Number of parallel compression workers')
    
    # All-in-one command
    all_parser = subparsers.add_parser('all', help='Download, merge, and compress PDFs in one step')
    all_parser.add_argument('url', help='URL to download PDFs from')
    all_parser.add_argument('--output', '-o', default='Processed_PDFs', help='Final output directory')
    all_parser.add_argument('--count', '-c', type=int, default=250, help='Number of merged files to create')
    all_parser.add_argument('--quality', '-q', choices=['screen', 'ebook', 'printer', 'prepress'], 
                           default='screen', help='Compression quality (lower = smaller size)')
    all_parser.add_argument('--download-workers', '-dw', type=int, default=10, help='Number of parallel download workers')
    all_parser.add_argument('--compress-workers', '-cw', type=int, help='Number of parallel compression workers')
    
    args = parser.parse_args()
    
    # Create PDFTools instance
    pdf_tools = PDFTools()
    
    if args.command == 'download':
        pdf_tools.download_pdfs_from_url(args.url, args.output, args.workers)
    
    elif args.command == 'merge':
        pdf_tools.merge_pdfs(args.input, args.output, args.count)
    
    elif args.command == 'compress':
        pdf_tools.compress_pdf_directory(args.input, args.output, args.quality, args.workers)
    
    elif args.command == 'all':
        print("=== STEP 1: DOWNLOADING PDFs ===")
        download_dir = pdf_tools.download_pdfs_from_url(args.url, max_workers=args.download_workers)
        
        if download_dir:
            print("\n=== STEP 2: MERGING PDFs ===")
            merged_dir = pdf_tools.merge_pdfs(download_dir, "Temp_Merged_PDFs", args.count)
            
            if merged_dir:
                print("\n=== STEP 3: COMPRESSING PDFs ===")
                pdf_tools.compress_pdf_directory(merged_dir, args.output, args.quality, args.compress_workers)
                
                # Clean up temporary directory
                print("\nCleaning up temporary files...")
                try:
                    shutil.rmtree(merged_dir)
                    print(f"Removed temporary directory: {merged_dir}")
                except Exception as e:
                    print(f"Warning: Could not remove temporary directory {merged_dir}: {e}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 