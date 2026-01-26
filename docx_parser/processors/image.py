"""
Image extraction processor for DOCX files.

Handles extracting images from DOCX archives and managing image mappings.
"""

from __future__ import annotations

import logging
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models import ImageInfo
from ..utils.image import process_image
from .base import ParsingContext, Processor

logger = logging.getLogger(__name__)


class ImageProcessor(Processor):
    """
    Processor for extracting and managing images from DOCX files.

    Handles:
    - Parsing relationship files to find images
    - Extracting image data from the archive
    - Converting image formats if needed
    - Saving images to disk or memory
    """

    def __init__(
        self,
        extract_images: bool = True,
        convert_images: bool = True,
        image_placeholder: str = "[IMAGE_{num}]",
    ) -> None:
        """
        Initialize image processor.

        Args:
            extract_images: Whether to extract image data.
            convert_images: Whether to convert non-standard formats.
            image_placeholder: Format string for image placeholders.
        """
        self._extract_images = extract_images
        self._convert_images = convert_images
        self._image_placeholder = image_placeholder

    def process(
        self,
        context: ParsingContext,
        output_dir: Optional[Path] = None,
        docx_stem: str = "document",
        **kwargs: Any,
    ) -> Tuple[Dict[int, Path], Dict[int, str], List[ImageInfo]]:
        """
        Extract images from the DOCX file.

        Args:
            context: ParsingContext containing the ZipFile.
            output_dir: Directory to save images (optional).
            docx_stem: Base name for the image subdirectory.

        Returns:
            Tuple of (images dict, image_mapping dict, images_list).
        """
        if context.zip_file is None:
            return {}, {}, []

        # Parse relationships to find images
        rid_to_file = self.parse_relationships(context.zip_file)

        # Create numbered mapping
        img_files = sorted(set(rid_to_file.values()))
        file_to_num = {f: i + 1 for i, f in enumerate(img_files)}
        rid_to_num = {rid: file_to_num[f] for rid, f in rid_to_file.items()}

        # Update context with mappings
        context.rid_to_file = rid_to_file
        context.rid_to_num = rid_to_num

        # Setup output directory (use as-is, parent already created subdirs)
        img_dir = None
        if output_dir:
            img_dir = output_dir
            img_dir.mkdir(parents=True, exist_ok=True)

        # Extract images
        images, image_mapping, images_list = self._extract_all_images(
            context.zip_file, img_files, file_to_num, img_dir
        )

        return images, image_mapping, images_list

    def parse_relationships(self, z: zipfile.ZipFile) -> Dict[str, str]:
        """
        Parse document.xml.rels to get rId -> image filename mapping.

        Args:
            z: Open ZipFile handle.

        Returns:
            Dict mapping relationship IDs to image filenames.
        """
        try:
            rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
        except KeyError:
            logger.debug("No document.xml.rels found")
            return {}

        rid_to_file = {}
        for match in re.finditer(r'Id="(rId\d+)"[^>]*Target="media/([^"]+)"', rels):
            rid_to_file[match.group(1)] = match.group(2)

        logger.debug(f"Found {len(rid_to_file)} image relationships")
        return rid_to_file

    def _extract_all_images(
        self,
        z: zipfile.ZipFile,
        img_files: List[str],
        file_to_num: Dict[str, int],
        img_dir: Optional[Path],
    ) -> Tuple[Dict[int, Path], Dict[int, str], List[ImageInfo]]:
        """
        Extract all images from the archive.

        Args:
            z: Open ZipFile handle.
            img_files: List of image filenames to extract.
            file_to_num: Mapping of filename to image number.
            img_dir: Directory to save images (optional).

        Returns:
            Tuple of (images dict, image_mapping dict, images_list).
        """
        images: Dict[int, Path] = {}
        image_mapping: Dict[int, str] = {}
        images_list: List[ImageInfo] = []

        if self._extract_images:
            for img_name in img_files:
                num = file_to_num[img_name]
                try:
                    img_data = z.read(f"word/media/{img_name}")

                    # Convert image if needed
                    if self._convert_images:
                        img_data, converted_name = process_image(
                            img_data, img_name, convert_to_png=True
                        )
                    else:
                        converted_name = img_name

                    new_name = f"{num:03d}_{converted_name}"

                    if img_dir:
                        # Save to file
                        img_path = img_dir / new_name
                        with open(img_path, "wb") as f:
                            f.write(img_data)
                        images[num] = img_path
                        image_mapping[num] = new_name
                        images_list.append(
                            ImageInfo(
                                index=num,
                                name=new_name,
                                path=str(img_path),
                                original_name=img_name,
                                data=img_data,
                            )
                        )
                    else:
                        # Store in memory only
                        image_mapping[num] = converted_name
                        images_list.append(
                            ImageInfo(
                                index=num,
                                name=converted_name,
                                path=None,
                                original_name=img_name,
                                data=img_data,
                            )
                        )
                except KeyError:
                    logger.warning(f"Image not found in archive: {img_name}")
        else:
            # Just create mappings without extracting data
            for img_name in img_files:
                num = file_to_num[img_name]
                image_mapping[num] = img_name
                images_list.append(
                    ImageInfo(
                        index=num,
                        name=img_name,
                        path=None,
                        original_name=img_name,
                        data=None,
                    )
                )

        return images, image_mapping, images_list

    def get_placeholder(self, num: int) -> str:
        """
        Get the placeholder string for an image number.

        Args:
            num: Image number.

        Returns:
            Formatted placeholder string.
        """
        return self._image_placeholder.format(num=num)
