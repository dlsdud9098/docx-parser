"""Tests for docx_parser.utils.xml module."""

import pytest

from docx_parser.utils.xml import (
    METADATA_NAMESPACES,
    NAMESPACES,
    XMLNamespaces,
)


class TestNamespaces:
    """Tests for namespace constants."""

    def test_namespaces_has_required_keys(self):
        """Test NAMESPACES has all required keys."""
        assert 'w' in NAMESPACES
        assert 'a' in NAMESPACES
        assert 'r' in NAMESPACES
        assert 'wp' in NAMESPACES

    def test_namespaces_values_are_urls(self):
        """Test namespace values are valid URLs."""
        for key, value in NAMESPACES.items():
            assert value.startswith('http://')
            assert 'openxmlformats.org' in value or 'microsoft.com' in value

    def test_metadata_namespaces_has_required_keys(self):
        """Test METADATA_NAMESPACES has all required keys."""
        assert 'cp' in METADATA_NAMESPACES
        assert 'dc' in METADATA_NAMESPACES
        assert 'dcterms' in METADATA_NAMESPACES
        assert 'ep' in METADATA_NAMESPACES

    def test_metadata_namespaces_values_are_urls(self):
        """Test metadata namespace values are valid URLs."""
        for key, value in METADATA_NAMESPACES.items():
            assert value.startswith('http://')


class TestXMLNamespaces:
    """Tests for XMLNamespaces class."""

    def test_class_constants(self):
        """Test class constants match dictionary values."""
        assert XMLNamespaces.W == NAMESPACES['w']
        assert XMLNamespaces.A == NAMESPACES['a']
        assert XMLNamespaces.R == NAMESPACES['r']
        assert XMLNamespaces.WP == NAMESPACES['wp']

    def test_metadata_class_constants(self):
        """Test metadata class constants."""
        assert XMLNamespaces.CP == METADATA_NAMESPACES['cp']
        assert XMLNamespaces.DC == METADATA_NAMESPACES['dc']
        assert XMLNamespaces.DCTERMS == METADATA_NAMESPACES['dcterms']
        assert XMLNamespaces.EP == METADATA_NAMESPACES['ep']

    def test_w_tag(self):
        """Test w_tag method."""
        tag = XMLNamespaces.w_tag('p')
        assert tag == f'{{{XMLNamespaces.W}}}p'
        assert tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'

    def test_w_tag_complex(self):
        """Test w_tag with various tag names."""
        assert XMLNamespaces.w_tag('body').endswith('}body')
        assert XMLNamespaces.w_tag('t').endswith('}t')
        assert XMLNamespaces.w_tag('tbl').endswith('}tbl')

    def test_a_tag(self):
        """Test a_tag method."""
        tag = XMLNamespaces.a_tag('blip')
        assert tag == f'{{{XMLNamespaces.A}}}blip'

    def test_r_tag(self):
        """Test r_tag method."""
        tag = XMLNamespaces.r_tag('embed')
        assert tag == f'{{{XMLNamespaces.R}}}embed'

    def test_wp_tag(self):
        """Test wp_tag method."""
        tag = XMLNamespaces.wp_tag('inline')
        assert tag == f'{{{XMLNamespaces.WP}}}inline'

    def test_dc_tag(self):
        """Test dc_tag method."""
        tag = XMLNamespaces.dc_tag('creator')
        assert tag == f'{{{XMLNamespaces.DC}}}creator'

    def test_dcterms_tag(self):
        """Test dcterms_tag method."""
        tag = XMLNamespaces.dcterms_tag('created')
        assert tag == f'{{{XMLNamespaces.DCTERMS}}}created'

    def test_cp_tag(self):
        """Test cp_tag method."""
        tag = XMLNamespaces.cp_tag('coreProperties')
        assert tag == f'{{{XMLNamespaces.CP}}}coreProperties'

    def test_ep_tag(self):
        """Test ep_tag method."""
        tag = XMLNamespaces.ep_tag('Application')
        assert tag == f'{{{XMLNamespaces.EP}}}Application'

    def test_get_all_namespaces(self):
        """Test get_all_namespaces combines both dictionaries."""
        all_ns = XMLNamespaces.get_all_namespaces()

        # Should include all from NAMESPACES
        for key, value in NAMESPACES.items():
            assert key in all_ns
            assert all_ns[key] == value

        # Should include all from METADATA_NAMESPACES
        for key, value in METADATA_NAMESPACES.items():
            assert key in all_ns
            assert all_ns[key] == value

    def test_get_all_namespaces_count(self):
        """Test get_all_namespaces has correct count."""
        all_ns = XMLNamespaces.get_all_namespaces()
        expected_count = len(NAMESPACES) + len(METADATA_NAMESPACES)
        assert len(all_ns) == expected_count
