"""
Data preprocessing module for cleaning and normalizing text.

This module provides comprehensive text cleaning and normalization
functionality to prepare documents for chunking and embedding.
"""

import re
import unicodedata
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import string
from collections import Counter

from llama_index.core import Document
from llama_index.core.node_parser import NodeParser
from loguru import logger
import pandas as pd


class TextCleaner:
    """
    Text cleaning utilities for document preprocessing.
    
    Handles removal of unwanted characters, fixing encoding issues,
    and standardizing text format.
    """
    
    def __init__(self):
        """Initialize text cleaner with default settings."""
        self.control_chars = self._get_control_characters()
        self.whitespace_pattern = re.compile(r'\s+')
        self.bullet_patterns = [
            re.compile(r'^[\u2022\u2023\u2043\u204C\u204D\u2219\u25AA\u25CF\u25E6]\s*'),
            re.compile(r'^[•·∙◦‣⁃]\s*'),
            re.compile(r'^\s*[-*+]\s+')
        ]
        
    def _get_control_characters(self) -> Set[str]:
        """
        Get set of control characters to remove.
        
        Returns:
            Set of control characters excluding newline and tab
        """
        chars = set()
        for i in range(32):
            if i not in [9, 10, 13]:  # Keep tab, newline, carriage return
                chars.add(chr(i))
        chars.add(chr(127))  # DEL character
        return chars
    
    def clean_text(self, text: str) -> str:
        """
        Perform comprehensive text cleaning.
        
        Args:
            text: Input text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove control characters
        text = self.remove_control_characters(text)
        
        # Fix encoding issues
        text = self.fix_encoding_issues(text)
        
        # Normalize whitespace
        text = self.normalize_whitespace(text)
        
        # Remove zero-width characters
        text = self.remove_zero_width_characters(text)
        
        # Fix quotes and apostrophes
        text = self.standardize_quotes(text)
        
        # Clean up excessive punctuation
        text = self.clean_punctuation(text)
        
        return text.strip()
    
    def remove_control_characters(self, text: str) -> str:
        """
        Remove control characters from text.
        
        Args:
            text: Input text
            
        Returns:
            Text without control characters
        """
        return ''.join(char for char in text if char not in self.control_chars)
    
    def fix_encoding_issues(self, text: str) -> str:
        """
        Fix common encoding issues in text.
        
        Args:
            text: Input text
            
        Returns:
            Text with fixed encoding
        """
        replacements = {
            'â€™': "'",
            'â€œ': '"',
            'â€': '"',
            'â€"': '—',
            'â€"': '–',
            'â€¦': '...',
            'Ã©': 'é',
            'Ã¨': 'è',
            'Ã ': 'à',
            'Ã¢': 'â',
            'Ã®': 'î',
            'Ã´': 'ô',
            'Ã»': 'û'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace in text.
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = self.whitespace_pattern.sub(' ', text)
        
        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove spaces before punctuation
        text = re.sub(r'\s+([.,;!?])', r'\1', text)
        
        # Add space after punctuation if missing
        text = re.sub(r'([.,;!?])([A-Za-z])', r'\1 \2', text)
        
        return text
    
    def remove_zero_width_characters(self, text: str) -> str:
        """
        Remove zero-width and invisible characters.
        
        Args:
            text: Input text
            
        Returns:
            Text without zero-width characters
        """
        zero_width_chars = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\ufeff',  # Zero-width no-break space
            '\u2060',  # Word joiner
        ]
        
        for char in zero_width_chars:
            text = text.replace(char, '')
        
        return text
    
    def standardize_quotes(self, text: str) -> str:
        """
        Standardize various quote styles.
        
        Args:
            text: Input text
            
        Returns:
            Text with standardized quotes
        """
        # Smart quotes to regular quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # French quotes
        text = text.replace('«', '"').replace('»', '"')
        
        # Angle quotes
        text = text.replace('‹', "'").replace('›', "'")
        
        return text
    
    def clean_punctuation(self, text: str) -> str:
        """
        Clean up excessive or malformed punctuation.
        
        Args:
            text: Input text
            
        Returns:
            Text with cleaned punctuation
        """
        # Remove multiple exclamation/question marks
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # Fix ellipsis
        text = re.sub(r'\.{2,}', '...', text)
        
        # Remove trailing punctuation from headers (if detected)
        text = re.sub(r'^(#{1,6}[^#\n]+)[.,;:]$', r'\1', text, flags=re.MULTILINE)
        
        return text
    
    def clean_bullets(self, text: str) -> str:
        """
        Standardize bullet points in text.
        
        Args:
            text: Input text
            
        Returns:
            Text with standardized bullets
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            cleaned_line = line
            for pattern in self.bullet_patterns:
                cleaned_line = pattern.sub('• ', cleaned_line)
            cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)


class TextNormalizer:
    """
    Text normalization utilities for standardizing document content.
    
    Handles linguistic and structural normalization to ensure
    consistent text format across documents.
    """
    
    def __init__(self):
        """Initialize text normalizer with default settings."""
        self.abbreviations = self._load_common_abbreviations()
        self.date_patterns = [
            re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b'),
            re.compile(r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b')
        ]
        self.number_patterns = {
            'currency': re.compile(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE),
            'percentage': re.compile(r'(\d+(?:\.\d+)?)\s*%'),
            'decimal': re.compile(r'\b\d+\.\d+\b'),
            'integer': re.compile(r'\b\d+\b')
        }
    
    def _load_common_abbreviations(self) -> Dict[str, str]:
        """
        Load common abbreviations for expansion.
        
        Returns:
            Dictionary mapping abbreviations to full forms
        """
        return {
            'Dr.': 'Doctor',
            'Mr.': 'Mister',
            'Mrs.': 'Missus',
            'Ms.': 'Miss',
            'Prof.': 'Professor',
            'Sr.': 'Senior',
            'Jr.': 'Junior',
            'Corp.': 'Corporation',
            'Inc.': 'Incorporated',
            'Ltd.': 'Limited',
            'Co.': 'Company',
            'vs.': 'versus',
            'etc.': 'et cetera',
            'i.e.': 'that is',
            'e.g.': 'for example',
            'cf.': 'compare',
            'et al.': 'and others'
        }
    
    def normalize_text(self, text: str, preserve_case: bool = True) -> str:
        """
        Perform comprehensive text normalization.
        
        Args:
            text: Input text to normalize
            preserve_case: Whether to preserve original casing
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        # Unicode normalization
        text = self.normalize_unicode(text)
        
        # Normalize dates
        text = self.normalize_dates(text)
        
        # Normalize numbers
        text = self.normalize_numbers(text)
        
        # Expand abbreviations (optional)
        # text = self.expand_abbreviations(text)
        
        # Normalize case if requested
        if not preserve_case:
            text = self.normalize_case(text)
        
        # Normalize punctuation spacing
        text = self.normalize_punctuation_spacing(text)
        
        return text
    
    def normalize_unicode(self, text: str, form: str = 'NFC') -> str:
        """
        Normalize Unicode characters.
        
        Args:
            text: Input text
            form: Unicode normalization form (NFC, NFD, NFKC, NFKD)
            
        Returns:
            Unicode-normalized text
        """
        return unicodedata.normalize(form, text)
    
    def normalize_dates(self, text: str) -> str:
        """
        Normalize date formats to ISO standard.
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized dates
        """
        def replace_date(match):
            groups = match.groups()
            try:
                if len(groups[2]) == 2:
                    year = '20' + groups[2] if int(groups[2]) < 50 else '19' + groups[2]
                else:
                    year = groups[2]
                
                if '/' in match.group() or '-' in match.group():
                    if len(groups[0]) == 4:  # YYYY-MM-DD format
                        return f"{groups[0]}-{groups[1]:0>2}-{groups[2]:0>2}"
                    else:  # MM-DD-YYYY or DD-MM-YYYY
                        return f"{year}-{groups[0]:0>2}-{groups[1]:0>2}"
            except:
                return match.group()
        
        for pattern in self.date_patterns:
            text = pattern.sub(replace_date, text)
        
        return text
    
    def normalize_numbers(self, text: str) -> str:
        """
        Normalize number formats.
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized numbers
        """
        # Normalize currency
        text = self.number_patterns['currency'].sub(
            lambda m: f"${m.group(1).replace(',', '')}",
            text
        )
        
        # Normalize percentages
        text = self.number_patterns['percentage'].sub(
            lambda m: f"{m.group(1)}%",
            text
        )
        
        return text
    
    def expand_abbreviations(self, text: str) -> str:
        """
        Expand common abbreviations to full forms.
        
        Args:
            text: Input text
            
        Returns:
            Text with expanded abbreviations
        """
        for abbr, full in self.abbreviations.items():
            pattern = re.compile(r'\b' + re.escape(abbr) + r'\b')
            text = pattern.sub(full, text)
        
        return text
    
    def normalize_case(self, text: str) -> str:
        """
        Normalize text casing while preserving acronyms.
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized casing
        """
        sentences = text.split('. ')
        normalized = []
        
        for sentence in sentences:
            if sentence:
                words = sentence.split()
                normalized_words = []
                
                for i, word in enumerate(words):
                    if word.isupper() and len(word) > 1:
                        # Likely an acronym, preserve it
                        normalized_words.append(word)
                    elif i == 0:
                        # First word of sentence
                        normalized_words.append(word.capitalize())
                    else:
                        # Regular word
                        normalized_words.append(word.lower())
                
                normalized.append(' '.join(normalized_words))
        
        return '. '.join(normalized)
    
    def normalize_punctuation_spacing(self, text: str) -> str:
        """
        Normalize spacing around punctuation marks.
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized punctuation spacing
        """
        # Remove space before punctuation
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        
        # Add space after punctuation if followed by letter
        text = re.sub(r'([.,;:!?])([A-Za-z])', r'\1 \2', text)
        
        # Fix spacing around quotes
        text = re.sub(r'"\s+', '"', text)
        text = re.sub(r'\s+"', '"', text)
        
        # Fix spacing around parentheses
        text = re.sub(r'\(\s+', '(', text)
        text = re.sub(r'\s+\)', ')', text)
        
        return text


class DocumentPreprocessor:
    """
    Main document preprocessing orchestrator.
    
    Combines cleaning and normalization steps to prepare
    documents for further processing.
    """
    
    def __init__(self):
        """Initialize document preprocessor with cleaner and normalizer."""
        self.cleaner = TextCleaner()
        self.normalizer = TextNormalizer()
        self.stats = {}
    
    def preprocess_document(self, document: Document) -> Document:
        """
        Preprocess a single document.
        
        Args:
            document: Input LlamaIndex Document
            
        Returns:
            Preprocessed Document with cleaned and normalized text
        """
        original_text = document.text
        original_length = len(original_text)
        
        # Clean text
        cleaned_text = self.cleaner.clean_text(original_text)
        
        # Normalize text
        normalized_text = self.normalizer.normalize_text(cleaned_text)
        
        # Clean bullets after normalization
        final_text = self.cleaner.clean_bullets(normalized_text)
        
        # Calculate statistics
        final_length = len(final_text)
        reduction_pct = ((original_length - final_length) / original_length * 100) if original_length > 0 else 0
        
        # Create new document with preprocessed text
        # LlamaIndex Documents are immutable, so create a new one
        preprocessed_doc = Document(
            text=final_text,
            metadata={**document.metadata}
        )
        
        # Add preprocessing metadata
        preprocessed_doc.metadata['preprocessing'] = {
            'original_length': original_length,
            'final_length': final_length,
            'reduction_percentage': round(reduction_pct, 2),
            'cleaned': True,
            'normalized': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.debug(f"Preprocessed document: {original_length} -> {final_length} chars ({reduction_pct:.1f}% reduction)")
        
        return preprocessed_doc
    
    def preprocess_batch(self, documents: List[Document]) -> List[Document]:
        """
        Preprocess a batch of documents.
        
        Args:
            documents: List of input Documents
            
        Returns:
            List of preprocessed Documents
        """
        preprocessed = []
        total_original = 0
        total_final = 0
        
        for doc in documents:
            processed_doc = self.preprocess_document(doc)
            preprocessed.append(processed_doc)
            
            total_original += doc.metadata['preprocessing']['original_length']
            total_final += doc.metadata['preprocessing']['final_length']
        
        # Log batch statistics
        if total_original > 0:
            total_reduction = ((total_original - total_final) / total_original * 100)
            logger.info(
                f"Preprocessed {len(documents)} documents: "
                f"{total_original} -> {total_final} chars "
                f"({total_reduction:.1f}% reduction)"
            )
        
        return preprocessed
    
    def validate_preprocessing(self, document: Document) -> Tuple[bool, List[str]]:
        """
        Validate preprocessed document quality.
        
        Args:
            document: Preprocessed document to validate
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        
        # Check for empty content
        if not document.text or len(document.text.strip()) == 0:
            issues.append("Document text is empty after preprocessing")
        
        # Check for excessive reduction
        if 'preprocessing' in document.metadata:
            reduction = document.metadata['preprocessing'].get('reduction_percentage', 0)
            if reduction > 50:
                issues.append(f"Excessive content reduction: {reduction}%")
        
        # Check for control characters
        control_chars = sum(1 for c in document.text if ord(c) < 32 and c not in '\n\t\r')
        if control_chars > 0:
            issues.append(f"Found {control_chars} control characters")
        
        # Check for encoding issues
        encoding_issues = ['â€', 'Ã©', 'Ã¨', 'Ã ', 'â€™', 'â€œ']
        for issue in encoding_issues:
            if issue in document.text:
                issues.append(f"Potential encoding issue: found '{issue}'")
        
        return len(issues) == 0, issues