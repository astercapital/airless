
from typing import List
import os

import fitz

from airless.core.hook import BaseHook


class PDFHook(BaseHook):

    def __init__(self):
        super().__init__()

    def chunk_in_pages(self, filepath: str, pages_per_chunk: int) -> List[str]:
        """
        Splits the PDF into chunks with a specified number of pages per chunk.
        Saves the chunks in the current working directory.

        :param filepath: Path to the PDF file.
        :param pages_per_chunk: Number of pages per chunk.
        :return: List of file paths to the chunked PDF files.
        """
        doc = fitz.open(filepath)
        total_pages = doc.page_count
        chunks = []
        base_name = os.path.splitext(os.path.basename(filepath))[0]

        for i in range(0, total_pages, pages_per_chunk):
            chunk_doc = fitz.open()
            start_page = i
            end_page = min(i + pages_per_chunk - 1, total_pages - 1)
            chunk_doc.insert_pdf(doc, from_page=start_page, to_page=end_page)

            if start_page == end_page:
                chunk_filename = f"{base_name}_page_{start_page + 1}.pdf"
            else:
                chunk_filename = f"{base_name}_page_{start_page + 1}_to_{end_page + 1}.pdf"

            chunk_path = os.path.join('/tmp', chunk_filename)
            chunk_doc.save(chunk_path)
            chunk_doc.close()
            chunks.append(chunk_path)

        doc.close()
        return chunks

    def generate_page_screenshot(filepath: str, dpi: int = 300, output_format: str = 'png') -> List[str]:
        """
        Converts each page of a PDF into an image.

        Args:
            filepath (str): The file path to the PDF.
            dpi (int, optional): Dots per inch for the output image. Defaults to 300.
            output_format (str, optional): The format of the output images (e.g., 'png', 'jpg'). Defaults to 'png'.

        Returns:
            List[str]: A list of file paths to the generated images.
        """
        # PDF default DPI is 72, so zoom factor is dpi / 72
        zoom_factor = dpi / 72
        matrix = fitz.Matrix(zoom_factor, zoom_factor)

        with fitz.open(filepath) as doc:
            image_paths = []
            base_name = os.path.splitext(os.path.basename(filepath))[0]

            for page_number in range(len(doc)):
                page = doc.load_page(page_number)  # 0-based index
                pix = page.get_pixmap(matrix=matrix)

                # Construct the image file name
                image_filename = f"{base_name}_page_{page_number + 1}.{output_format}"
                image_path = os.path.join('/tmp', image_filename)

                # Save the image
                pix.save(image_path)

                # Append the path to the list
                image_paths.append(image_path)

            return image_paths
