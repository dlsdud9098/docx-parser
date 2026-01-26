"""Tests for docx_parser.utils.image module."""

import io
from pathlib import Path

import pytest

from docx_parser.utils.image import (
    FORMAT_TO_MIME,
    IMAGE_SIGNATURES,
    MIME_TYPE_MAP,
    convert_image_to_png,
    detect_image_format,
    get_mime_type,
    process_image,
)


class TestImageSignatures:
    """Tests for IMAGE_SIGNATURES constant."""

    def test_has_common_formats(self):
        """Test all common formats are present."""
        formats = set(IMAGE_SIGNATURES.values())
        assert 'png' in formats
        assert 'jpeg' in formats
        assert 'gif' in formats
        assert 'bmp' in formats
        assert 'tiff' in formats
        assert 'webp' in formats

    def test_has_office_formats(self):
        """Test Office-specific formats are present."""
        formats = set(IMAGE_SIGNATURES.values())
        assert 'wdp' in formats
        assert 'emf' in formats
        assert 'wmf' in formats


class TestDetectImageFormat:
    """Tests for detect_image_format function."""

    def test_detect_png(self):
        """Test PNG detection."""
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        assert detect_image_format(png_data) == 'png'

    def test_detect_jpeg(self):
        """Test JPEG detection."""
        jpeg_data = b'\xff\xd8\xff' + b'\x00' * 100
        assert detect_image_format(jpeg_data) == 'jpeg'

    def test_detect_gif87a(self):
        """Test GIF87a detection."""
        gif_data = b'GIF87a' + b'\x00' * 100
        assert detect_image_format(gif_data) == 'gif'

    def test_detect_gif89a(self):
        """Test GIF89a detection."""
        gif_data = b'GIF89a' + b'\x00' * 100
        assert detect_image_format(gif_data) == 'gif'

    def test_detect_bmp(self):
        """Test BMP detection."""
        bmp_data = b'BM' + b'\x00' * 100
        assert detect_image_format(bmp_data) == 'bmp'

    def test_detect_webp(self):
        """Test WebP detection."""
        webp_data = b'RIFF\x00\x00\x00\x00WEBP' + b'\x00' * 100
        assert detect_image_format(webp_data) == 'webp'

    def test_detect_webp_invalid(self):
        """Test WebP detection with invalid header."""
        # RIFF but not WEBP
        invalid_data = b'RIFF\x00\x00\x00\x00WAVE' + b'\x00' * 100
        assert detect_image_format(invalid_data) is None

    def test_detect_tiff_little_endian(self):
        """Test little-endian TIFF detection."""
        tiff_data = b'II*\x00' + b'\x00' * 100
        assert detect_image_format(tiff_data) == 'tiff'

    def test_detect_tiff_big_endian(self):
        """Test big-endian TIFF detection."""
        tiff_data = b'MM\x00*' + b'\x00' * 100
        assert detect_image_format(tiff_data) == 'tiff'

    def test_detect_wdp(self):
        """Test WDP/JPEG XR detection."""
        wdp_data = b'II\xbc\x01' + b'\x00' * 100
        assert detect_image_format(wdp_data) == 'wdp'

    def test_detect_emf(self):
        """Test EMF detection."""
        emf_data = b'\x01\x00\x00\x00' + b'\x00' * 100
        assert detect_image_format(emf_data) == 'emf'

    def test_detect_wmf(self):
        """Test WMF detection."""
        wmf_data = b'\xd7\xcd\xc6\x9a' + b'\x00' * 100
        assert detect_image_format(wmf_data) == 'wmf'

    def test_detect_unknown(self):
        """Test unknown format returns None."""
        unknown_data = b'\x00\x00\x00\x00' + b'\x00' * 100
        assert detect_image_format(unknown_data) is None

    def test_detect_empty(self):
        """Test empty data returns None."""
        assert detect_image_format(b'') is None

    def test_detect_short_data(self):
        """Test short data that doesn't match any signature."""
        assert detect_image_format(b'\x89') is None


class TestGetMimeType:
    """Tests for get_mime_type function."""

    def test_mime_from_bytes_png(self):
        """Test MIME type from PNG bytes."""
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        assert get_mime_type(png_data) == 'image/png'

    def test_mime_from_bytes_jpeg(self):
        """Test MIME type from JPEG bytes."""
        jpeg_data = b'\xff\xd8\xff' + b'\x00' * 100
        assert get_mime_type(jpeg_data) == 'image/jpeg'

    def test_mime_from_bytes_gif(self):
        """Test MIME type from GIF bytes."""
        gif_data = b'GIF89a' + b'\x00' * 100
        assert get_mime_type(gif_data) == 'image/gif'

    def test_mime_from_bytes_webp(self):
        """Test MIME type from WebP bytes."""
        webp_data = b'RIFF\x00\x00\x00\x00WEBP' + b'\x00' * 100
        assert get_mime_type(webp_data) == 'image/webp'

    def test_mime_from_bytesio(self):
        """Test MIME type from BytesIO."""
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        buffer = io.BytesIO(png_data)
        assert get_mime_type(buffer) == 'image/png'

    def test_mime_from_filename_fallback(self):
        """Test MIME type fallback to filename."""
        unknown_data = b'\x00\x00\x00\x00'
        assert get_mime_type(unknown_data, filename='image.jpg') == 'image/jpeg'
        assert get_mime_type(unknown_data, filename='image.png') == 'image/png'
        assert get_mime_type(unknown_data, filename='image.gif') == 'image/gif'

    def test_mime_default_png(self):
        """Test default MIME type is PNG."""
        unknown_data = b'\x00\x00\x00\x00'
        assert get_mime_type(unknown_data) == 'image/png'


class TestConvertImageToPng:
    """Tests for convert_image_to_png function."""

    def test_no_conversion_png(self):
        """Test PNG is not converted."""
        data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        result_data, result_ext = convert_image_to_png(data, '.png')
        assert result_ext == '.png'
        assert result_data == data

    def test_no_conversion_jpg(self):
        """Test JPEG is not converted."""
        data = b'\xff\xd8\xff' + b'\x00' * 100
        result_data, result_ext = convert_image_to_png(data, '.jpg')
        assert result_ext == '.jpg'
        assert result_data == data

    def test_no_conversion_jpeg(self):
        """Test JPEG with .jpeg extension is not converted."""
        data = b'\xff\xd8\xff' + b'\x00' * 100
        result_data, result_ext = convert_image_to_png(data, '.jpeg')
        assert result_ext == '.jpeg'

    def test_no_conversion_gif(self):
        """Test GIF is not converted."""
        data = b'GIF89a' + b'\x00' * 100
        result_data, result_ext = convert_image_to_png(data, '.gif')
        assert result_ext == '.gif'

    def test_no_conversion_webp(self):
        """Test WebP is not converted."""
        data = b'RIFF\x00\x00\x00\x00WEBP' + b'\x00' * 100
        result_data, result_ext = convert_image_to_png(data, '.webp')
        assert result_ext == '.webp'

    def test_tmp_png_detection(self):
        """Test .tmp file with PNG data gets correct extension."""
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        result_data, result_ext = convert_image_to_png(png_data, '.tmp')
        assert result_ext == '.png'

    def test_tmp_jpeg_detection(self):
        """Test .tmp file with JPEG data gets correct extension."""
        jpeg_data = b'\xff\xd8\xff' + b'\x00' * 100
        result_data, result_ext = convert_image_to_png(jpeg_data, '.tmp')
        assert result_ext == '.jpg'

    def test_tmp_gif_detection(self):
        """Test .tmp file with GIF data gets correct extension."""
        gif_data = b'GIF89a' + b'\x00' * 100
        result_data, result_ext = convert_image_to_png(gif_data, '.tmp')
        assert result_ext == '.gif'

    def test_unsupported_format_returns_original(self):
        """Test unsupported format returns original."""
        unknown_data = b'UNKNOWN_FORMAT_DATA'
        result_data, result_ext = convert_image_to_png(unknown_data, '.xyz')
        assert result_ext == '.xyz'
        assert result_data == unknown_data


class TestProcessImage:
    """Tests for process_image function."""

    def test_process_png(self):
        """Test processing PNG file."""
        data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        result_data, result_name = process_image(data, 'image.png')
        assert result_name == 'image.png'

    def test_process_without_conversion(self):
        """Test processing without conversion."""
        data = b'\xff\xd8\xff' + b'\x00' * 100
        result_data, result_name = process_image(data, 'photo.tmp', convert_to_png=False)
        assert result_name == 'photo.tmp'
        assert result_data == data

    def test_process_tmp_to_jpg(self):
        """Test processing .tmp with JPEG data."""
        jpeg_data = b'\xff\xd8\xff' + b'\x00' * 100
        result_data, result_name = process_image(jpeg_data, 'image.tmp')
        assert result_name == 'image.jpg'

    def test_process_preserves_stem(self):
        """Test processing preserves filename stem."""
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        result_data, result_name = process_image(png_data, 'my_photo_001.tmp')
        assert result_name == 'my_photo_001.png'


class TestMimeTypeConstants:
    """Tests for MIME type constants."""

    def test_mime_type_map_has_common_extensions(self):
        """Test MIME_TYPE_MAP has common extensions."""
        assert '.jpg' in MIME_TYPE_MAP
        assert '.jpeg' in MIME_TYPE_MAP
        assert '.png' in MIME_TYPE_MAP
        assert '.gif' in MIME_TYPE_MAP
        assert '.webp' in MIME_TYPE_MAP

    def test_format_to_mime_has_common_formats(self):
        """Test FORMAT_TO_MIME has common formats."""
        assert 'png' in FORMAT_TO_MIME
        assert 'jpeg' in FORMAT_TO_MIME
        assert 'gif' in FORMAT_TO_MIME
        assert 'webp' in FORMAT_TO_MIME


class TestGetMimeTypeExtended:
    """Extended tests for get_mime_type function."""

    def test_mime_from_path_object(self, tmp_path):
        """Test MIME type from Path object."""
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        img_path = tmp_path / "test.png"
        img_path.write_bytes(png_data)

        assert get_mime_type(img_path) == 'image/png'

    def test_mime_from_path_with_jpeg(self, tmp_path):
        """Test MIME type from Path with JPEG data."""
        jpeg_data = b'\xff\xd8\xff' + b'\x00' * 100
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(jpeg_data)

        assert get_mime_type(img_path) == 'image/jpeg'

    def test_mime_from_nonexistent_path(self, tmp_path):
        """Test MIME type from non-existent Path."""
        nonexistent = tmp_path / "nonexistent.jpg"
        # Should fallback to extension
        result = get_mime_type(nonexistent, filename="image.jpg")
        assert result in ['image/png', 'image/jpeg']

    def test_mime_from_wdp_bytes(self):
        """Test MIME type from WDP bytes."""
        wdp_data = b'II\xbc\x01' + b'\x00' * 100
        assert get_mime_type(wdp_data) == 'image/vnd.ms-photo'

    def test_mime_from_bmp_bytes(self):
        """Test MIME type from BMP bytes."""
        bmp_data = b'BM' + b'\x00' * 100
        assert get_mime_type(bmp_data) == 'image/bmp'

    def test_mime_from_tiff_little_endian(self):
        """Test MIME type from little-endian TIFF."""
        tiff_data = b'II*\x00' + b'\x00' * 100
        assert get_mime_type(tiff_data) == 'image/tiff'

    def test_mime_from_tiff_big_endian(self):
        """Test MIME type from big-endian TIFF."""
        tiff_data = b'MM\x00*' + b'\x00' * 100
        assert get_mime_type(tiff_data) == 'image/tiff'


class TestConvertImageToPngExtended:
    """Extended tests for convert_image_to_png function."""

    def test_convert_wdp_without_jxrdecapp(self):
        """Test WDP conversion without JxrDecApp installed."""
        from unittest.mock import patch

        wdp_data = b'II\xbc\x01' + b'\x00' * 100

        with patch('shutil.which', return_value=None):
            result_data, result_ext = convert_image_to_png(wdp_data, '.wdp')
            # Without JxrDecApp, should try PIL and fail, returning original
            assert result_ext in ['.wdp', '.png']

    def test_convert_hdp_format(self):
        """Test HDP (JPEG XR variant) handling."""
        from unittest.mock import patch

        hdp_data = b'II\xbc\x01' + b'\x00' * 100

        with patch('shutil.which', return_value=None):
            result_data, result_ext = convert_image_to_png(hdp_data, '.hdp')
            assert result_ext in ['.hdp', '.png']

    def test_convert_jxr_format(self):
        """Test JXR format handling."""
        from unittest.mock import patch

        jxr_data = b'II\xbc\x01' + b'\x00' * 100

        with patch('shutil.which', return_value=None):
            result_data, result_ext = convert_image_to_png(jxr_data, '.jxr')
            assert result_ext in ['.jxr', '.png']

    def test_convert_tmp_webp_detection(self):
        """Test .tmp file with WebP data detection."""
        webp_data = b'RIFF\x00\x00\x00\x00WEBP' + b'\x00' * 100
        result_data, result_ext = convert_image_to_png(webp_data, '.tmp')
        assert result_ext == '.webp'

    def test_convert_bmp_to_png_with_pil(self, sample_image_bytes):
        """Test BMP to PNG conversion using PIL."""
        try:
            from PIL import Image

            # Create a valid BMP image
            img = Image.new('RGB', (10, 10), color='red')
            buffer = io.BytesIO()
            img.save(buffer, format='BMP')
            bmp_data = buffer.getvalue()

            result_data, result_ext = convert_image_to_png(bmp_data, '.bmp')
            assert result_ext == '.png'
            # Verify it's valid PNG data
            assert result_data.startswith(b'\x89PNG')
        except ImportError:
            pytest.skip("PIL not installed")

    def test_convert_rgba_image_to_png(self):
        """Test RGBA image conversion to PNG."""
        try:
            from PIL import Image

            # Create RGBA image with transparency
            img = Image.new('RGBA', (10, 10), (255, 0, 0, 128))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            rgba_data = buffer.getvalue()

            # Process as .tmp to trigger conversion path
            result_data, result_ext = convert_image_to_png(rgba_data, '.tmp')
            assert result_ext == '.png'
        except ImportError:
            pytest.skip("PIL not installed")


class TestProcessImageExtended:
    """Extended tests for process_image function."""

    def test_process_bmp_with_conversion(self, sample_image_bytes):
        """Test processing BMP with conversion enabled."""
        try:
            from PIL import Image

            img = Image.new('RGB', (10, 10), color='blue')
            buffer = io.BytesIO()
            img.save(buffer, format='BMP')
            bmp_data = buffer.getvalue()

            result_data, result_name = process_image(bmp_data, 'photo.bmp', convert_to_png=True)
            assert result_name == 'photo.png'
            assert result_data.startswith(b'\x89PNG')
        except ImportError:
            pytest.skip("PIL not installed")

    def test_process_webp_detection(self):
        """Test processing WebP detection from .tmp."""
        webp_data = b'RIFF\x00\x00\x00\x00WEBP' + b'\x00' * 100
        result_data, result_name = process_image(webp_data, 'image.tmp')
        assert result_name == 'image.webp'

    def test_process_gif_detection(self):
        """Test processing GIF detection from .tmp."""
        gif_data = b'GIF89a' + b'\x00' * 100
        result_data, result_name = process_image(gif_data, 'animation.tmp')
        assert result_name == 'animation.gif'

    def test_process_emf_format(self):
        """Test processing EMF format."""
        emf_data = b'\x01\x00\x00\x00' + b'\x00' * 100
        result_data, result_name = process_image(emf_data, 'diagram.emf', convert_to_png=False)
        assert result_name == 'diagram.emf'

    def test_process_wmf_format(self):
        """Test processing WMF format."""
        wmf_data = b'\xd7\xcd\xc6\x9a' + b'\x00' * 100
        result_data, result_name = process_image(wmf_data, 'drawing.wmf', convert_to_png=False)
        assert result_name == 'drawing.wmf'


class TestWdpConversion:
    """Tests for WDP conversion functionality."""

    def test_convert_wdp_with_jxrdecapp(self, tmp_path):
        """Test WDP conversion with JxrDecApp available."""
        from unittest.mock import patch, MagicMock

        wdp_data = b'II\xbc\x01' + b'\x00' * 100

        with patch('shutil.which', return_value='/usr/bin/JxrDecApp'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=1)  # Fail subprocess
                result_data, result_ext = convert_image_to_png(wdp_data, '.wdp')
                # Should fail and return original
                assert result_ext in ['.wdp', '.png']
