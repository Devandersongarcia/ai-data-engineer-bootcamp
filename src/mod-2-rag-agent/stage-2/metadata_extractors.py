"""
Metadata extraction module for enriching documents with structured information.

This module provides various extractors to identify and extract metadata
such as titles, keywords, entities, summaries, and questions from documents.
"""

import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from collections import Counter
import hashlib

from llama_index.core import Document
from llama_index.core.extractors import (
    TitleExtractor,
    KeywordExtractor,
    SummaryExtractor,
    QuestionsAnsweredExtractor
)
from llama_index.core.extractors.interface import BaseExtractor
from llama_index.llms.openai import OpenAI
from llama_index.core.schema import MetadataMode
from loguru import logger
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

from config import Settings, MetadataConfig


class CustomTitleExtractor(BaseExtractor):
    """
    Custom title extractor that identifies document and section titles.
    
    Uses pattern matching and LLM to extract hierarchical titles
    from documents.
    """
    
    def __init__(self, llm: Optional[OpenAI] = None):
        """
        Initialize custom title extractor.
        
        Args:
            llm: Optional LLM for advanced title extraction
        """
        super().__init__()
        self.llm_model = llm
        self.heading_patterns = [
            re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE),  # Markdown headers
            re.compile(r'^([A-Z][^.!?]*?)$', re.MULTILINE),  # All caps lines
            re.compile(r'^\d+\.?\s+([A-Z].+)$', re.MULTILINE),  # Numbered headers
            re.compile(r'^[IVX]+\.?\s+(.+)$', re.MULTILINE),  # Roman numerals
        ]
    
    async def aextract(self, nodes: List[Document]) -> List[Dict[str, Any]]:
        """
        Asynchronously extract titles from documents.
        
        Args:
            nodes: List of documents to process
            
        Returns:
            List of metadata dictionaries with extracted titles
        """
        metadata_list = []
        
        for node in nodes:
            metadata = await self._extract_from_node(node)
            metadata_list.append(metadata)
        
        return metadata_list
    
    async def _extract_from_node(self, node: Document) -> Dict[str, Any]:
        """
        Extract titles from a single node.
        
        Args:
            node: Document node to process
            
        Returns:
            Dictionary with extracted title metadata
        """
        text = node.get_content(metadata_mode=MetadataMode.NONE)
        
        # Try pattern-based extraction first
        titles = self._extract_with_patterns(text)
        
        # If no titles found and LLM available, use LLM
        if not titles and self.llm_model:
            titles = await self._extract_with_llm(text)
        
        # Get the most likely main title
        main_title = titles[0] if titles else self._generate_default_title(text)
        
        return {
            'document_title': main_title,
            'section_titles': titles[1:] if len(titles) > 1 else [],
            'title_hierarchy': self._build_hierarchy(titles)
        }
    
    def _extract_with_patterns(self, text: str) -> List[str]:
        """
        Extract titles using regex patterns.
        
        Args:
            text: Text to extract titles from
            
        Returns:
            List of extracted titles
        """
        titles = []
        
        for pattern in self.heading_patterns:
            matches = pattern.findall(text)
            titles.extend(matches)
        
        # Deduplicate while preserving order
        seen = set()
        unique_titles = []
        for title in titles:
            if title not in seen:
                seen.add(title)
                unique_titles.append(title)
        
        return unique_titles
    
    async def _extract_with_llm(self, text: str) -> List[str]:
        """
        Extract titles using LLM.
        
        Args:
            text: Text to extract titles from
            
        Returns:
            List of extracted titles
        """
        prompt = f"""Extract all titles and section headers from the following text.
Return them as a comma-separated list, with the main title first.

Text: {text[:2000]}...

Titles:"""
        
        try:
            response = await self.llm_model.acomplete(prompt)
            titles = [t.strip() for t in response.text.split(',')]
            return titles
        except Exception as e:
            logger.error(f"LLM title extraction failed: {e}")
            return []
    
    def _generate_default_title(self, text: str) -> str:
        """
        Generate a default title from text beginning.
        
        Args:
            text: Text to generate title from
            
        Returns:
            Generated title
        """
        first_line = text.split('\n')[0] if text else "Untitled Document"
        return first_line[:100] + "..." if len(first_line) > 100 else first_line
    
    def _build_hierarchy(self, titles: List[str]) -> Dict[str, List[str]]:
        """
        Build hierarchical structure of titles.
        
        Args:
            titles: List of titles
            
        Returns:
            Hierarchical structure dictionary
        """
        if not titles:
            return {}
        
        return {
            'main': titles[0] if titles else None,
            'sections': titles[1:3] if len(titles) > 1 else [],
            'subsections': titles[3:] if len(titles) > 3 else []
        }


class AdvancedKeywordExtractor(BaseExtractor):
    """
    Advanced keyword extractor using TF-IDF and NER.
    
    Combines statistical methods with named entity recognition
    for comprehensive keyword extraction.
    """
    
    def __init__(self, llm: Optional[OpenAI] = None, max_keywords: int = 10):
        """
        Initialize advanced keyword extractor.
        
        Args:
            llm: Optional LLM for enhanced extraction
            max_keywords: Maximum number of keywords to extract
        """
        super().__init__()
        self.llm_model = llm
        self.max_keywords = max_keywords
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            logger.warning("Spacy model not found, using basic extraction")
            self.nlp = None
    
    async def aextract(self, nodes: List[Document]) -> List[Dict[str, Any]]:
        """
        Asynchronously extract keywords from documents.
        
        Args:
            nodes: List of documents to process
            
        Returns:
            List of metadata dictionaries with extracted keywords
        """
        metadata_list = []
        
        for node in nodes:
            metadata = await self._extract_from_node(node)
            metadata_list.append(metadata)
        
        return metadata_list
    
    async def _extract_from_node(self, node: Document) -> Dict[str, Any]:
        """
        Extract keywords from a single node.
        
        Args:
            node: Document node to process
            
        Returns:
            Dictionary with extracted keyword metadata
        """
        text = node.get_content(metadata_mode=MetadataMode.NONE)
        
        # Extract using multiple methods
        tfidf_keywords = self._extract_tfidf_keywords(text)
        entity_keywords = self._extract_entity_keywords(text)
        
        # Combine and rank keywords
        all_keywords = list(set(tfidf_keywords + entity_keywords))
        
        # If LLM available, refine keywords
        if self.llm_model and all_keywords:
            all_keywords = await self._refine_with_llm(text, all_keywords)
        
        # Categorize keywords
        categories = self._categorize_keywords(all_keywords)
        
        return {
            'keywords': all_keywords[:self.max_keywords],
            'keyword_categories': categories,
            'keyword_count': len(all_keywords)
        }
    
    def _extract_tfidf_keywords(self, text: str) -> List[str]:
        """
        Extract keywords using TF-IDF.
        
        Args:
            text: Text to extract keywords from
            
        Returns:
            List of TF-IDF based keywords
        """
        try:
            # Tokenize into sentences
            sentences = text.split('.')
            if len(sentences) < 2:
                sentences = [text]
            
            # Create TF-IDF vectorizer
            vectorizer = TfidfVectorizer(
                max_features=self.max_keywords,
                stop_words='english',
                ngram_range=(1, 2)
            )
            
            # Fit and transform
            tfidf_matrix = vectorizer.fit_transform(sentences)
            
            # Get feature names
            feature_names = vectorizer.get_feature_names_out()
            
            # Get top keywords based on TF-IDF scores
            scores = tfidf_matrix.sum(axis=0).A1
            top_indices = scores.argsort()[-self.max_keywords:][::-1]
            
            keywords = [feature_names[i] for i in top_indices]
            return keywords
            
        except Exception as e:
            logger.error(f"TF-IDF extraction failed: {e}")
            return []
    
    def _extract_entity_keywords(self, text: str) -> List[str]:
        """
        Extract keywords using named entity recognition.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of entity-based keywords
        """
        if not self.nlp:
            return []
        
        try:
            doc = self.nlp(text[:1000000])  # Limit text length for spacy
            
            entities = []
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'GPE', 'PRODUCT', 'EVENT']:
                    entities.append(ent.text)
            
            # Also extract noun phrases
            noun_phrases = [chunk.text for chunk in doc.noun_chunks if len(chunk.text.split()) <= 3]
            
            return list(set(entities + noun_phrases[:self.max_keywords]))
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
    
    async def _refine_with_llm(self, text: str, keywords: List[str]) -> List[str]:
        """
        Refine keywords using LLM.
        
        Args:
            text: Original text
            keywords: Initial keywords
            
        Returns:
            Refined list of keywords
        """
        prompt = f"""Given the following text and initial keywords, provide the {self.max_keywords} most relevant keywords.
        
Text excerpt: {text[:1000]}...

Initial keywords: {', '.join(keywords)}

Refined keywords (comma-separated):"""
        
        try:
            response = await self.llm_model.acomplete(prompt)
            refined = [k.strip() for k in response.text.split(',')]
            return refined[:self.max_keywords]
        except Exception as e:
            logger.error(f"LLM keyword refinement failed: {e}")
            return keywords
    
    def _categorize_keywords(self, keywords: List[str]) -> Dict[str, List[str]]:
        """
        Categorize keywords by type.
        
        Args:
            keywords: List of keywords
            
        Returns:
            Dictionary of categorized keywords
        """
        categories = {
            'technical': [],
            'concepts': [],
            'entities': [],
            'general': []
        }
        
        for keyword in keywords:
            if any(term in keyword.lower() for term in ['algorithm', 'function', 'method', 'system', 'process']):
                categories['technical'].append(keyword)
            elif keyword[0].isupper() and len(keyword.split()) == 1:
                categories['entities'].append(keyword)
            elif len(keyword.split()) > 1:
                categories['concepts'].append(keyword)
            else:
                categories['general'].append(keyword)
        
        return {k: v for k, v in categories.items() if v}


class TopicExtractor(BaseExtractor):
    """
    Extract and classify document topics.
    
    Identifies main topics and themes within documents using
    pattern matching and LLM-based classification.
    """
    
    def __init__(self, llm: Optional[OpenAI] = None):
        """
        Initialize topic extractor.
        
        Args:
            llm: Optional LLM for topic classification
        """
        super().__init__()
        self.llm_model = llm
        self.topic_patterns = {
            'data_engineering': ['pipeline', 'etl', 'data flow', 'ingestion', 'transformation'],
            'machine_learning': ['model', 'training', 'prediction', 'neural network', 'algorithm'],
            'database': ['sql', 'query', 'table', 'schema', 'index'],
            'cloud': ['aws', 'azure', 'gcp', 'cloud', 'serverless'],
            'programming': ['function', 'class', 'variable', 'loop', 'condition'],
            'architecture': ['microservice', 'api', 'design pattern', 'scalability', 'system design']
        }
    
    async def aextract(self, nodes: List[Document]) -> List[Dict[str, Any]]:
        """
        Asynchronously extract topics from documents.
        
        Args:
            nodes: List of documents to process
            
        Returns:
            List of metadata dictionaries with extracted topics
        """
        metadata_list = []
        
        for node in nodes:
            metadata = await self._extract_from_node(node)
            metadata_list.append(metadata)
        
        return metadata_list
    
    async def _extract_from_node(self, node: Document) -> Dict[str, Any]:
        """
        Extract topics from a single node.
        
        Args:
            node: Document node to process
            
        Returns:
            Dictionary with extracted topic metadata
        """
        text = node.get_content(metadata_mode=MetadataMode.NONE)
        
        # Pattern-based topic detection
        detected_topics = self._detect_topics_by_pattern(text)
        
        # LLM-based topic classification if available
        if self.llm_model:
            llm_topics = await self._classify_with_llm(text)
            detected_topics.update(llm_topics)
        
        # Calculate topic confidence scores
        topic_scores = self._calculate_topic_scores(text, detected_topics)
        
        # Get primary topic
        primary_topic = max(topic_scores, key=topic_scores.get) if topic_scores else 'general'
        
        return {
            'primary_topic': primary_topic,
            'topics': list(detected_topics),
            'topic_scores': topic_scores,
            'topic_distribution': self._calculate_distribution(topic_scores)
        }
    
    def _detect_topics_by_pattern(self, text: str) -> Set[str]:
        """
        Detect topics using keyword patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            Set of detected topics
        """
        detected = set()
        text_lower = text.lower()
        
        for topic, keywords in self.topic_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                detected.add(topic)
        
        return detected
    
    async def _classify_with_llm(self, text: str) -> Set[str]:
        """
        Classify topics using LLM.
        
        Args:
            text: Text to classify
            
        Returns:
            Set of classified topics
        """
        prompt = f"""Classify the following text into one or more of these topics:
- data_engineering
- machine_learning
- database
- cloud
- programming
- architecture

Text: {text[:1500]}...

Topics (comma-separated):"""
        
        try:
            response = await self.llm_model.acomplete(prompt)
            topics = [t.strip().lower() for t in response.text.split(',')]
            return set(topics) & set(self.topic_patterns.keys())
        except Exception as e:
            logger.error(f"LLM topic classification failed: {e}")
            return set()
    
    def _calculate_topic_scores(self, text: str, topics: Set[str]) -> Dict[str, float]:
        """
        Calculate confidence scores for each topic.
        
        Args:
            text: Text to analyze
            topics: Set of detected topics
            
        Returns:
            Dictionary of topic scores
        """
        scores = {}
        text_lower = text.lower()
        
        for topic in topics:
            if topic in self.topic_patterns:
                keywords = self.topic_patterns[topic]
                count = sum(text_lower.count(keyword) for keyword in keywords)
                scores[topic] = min(count / 10.0, 1.0)  # Normalize to 0-1
        
        return scores
    
    def _calculate_distribution(self, scores: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate topic distribution percentages.
        
        Args:
            scores: Topic scores
            
        Returns:
            Topic distribution as percentages
        """
        total = sum(scores.values())
        if total == 0:
            return {}
        
        return {topic: (score / total) * 100 for topic, score in scores.items()}


class MetadataEnricher:
    """
    Main metadata enrichment orchestrator.
    
    Combines multiple extractors to comprehensively enrich
    documents with structured metadata.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize metadata enricher with configuration.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.metadata_config = settings.metadata
        
        # Initialize LLM
        self.llm = OpenAI(
            api_key=settings.openai.api_key,
            model=settings.openai.llm_model
        )
        
        # Initialize extractors based on configuration
        self.extractors = self._initialize_extractors()
    
    def _initialize_extractors(self) -> Dict[str, BaseExtractor]:
        """
        Initialize enabled extractors.
        
        Returns:
            Dictionary of initialized extractors
        """
        extractors = {}
        
        if self.metadata_config.extract_titles:
            extractors['title'] = TitleExtractor(llm=self.llm)
        
        if self.metadata_config.extract_keywords:
            extractors['keyword'] = KeywordExtractor(llm=self.llm)
        
        if self.metadata_config.extract_summaries:
            extractors['summary'] = SummaryExtractor(llm=self.llm)
        
        if self.metadata_config.extract_questions:
            extractors['questions'] = QuestionsAnsweredExtractor(llm=self.llm)
        
        # Use custom extractors when needed
        # extractors['custom_title'] = CustomTitleExtractor(llm=self.llm)
        # extractors['advanced_keyword'] = AdvancedKeywordExtractor(llm=self.llm)
        # extractors['topic'] = TopicExtractor(llm=self.llm)
        
        logger.info(f"Initialized {len(extractors)} metadata extractors")
        return extractors
    
    async def enrich_document(self, document: Document) -> Document:
        """
        Enrich a single document with metadata.
        
        Args:
            document: Document to enrich
            
        Returns:
            Enriched document
        """
        for name, extractor in self.extractors.items():
            try:
                metadata = await extractor.aextract([document])
                if metadata and metadata[0]:
                    document.metadata[f'{name}_metadata'] = metadata[0]
            except Exception as e:
                logger.error(f"Extractor {name} failed: {e}")
                continue
        
        # Add enrichment timestamp
        document.metadata['enrichment_timestamp'] = datetime.utcnow().isoformat()
        
        return document
    
    async def enrich_batch(self, documents: List[Document]) -> List[Document]:
        """
        Enrich a batch of documents with metadata.
        
        Args:
            documents: List of documents to enrich
            
        Returns:
            List of enriched documents
        """
        enriched = []
        
        for doc in documents:
            enriched_doc = await self.enrich_document(doc)
            enriched.append(enriched_doc)
        
        logger.info(f"Enriched {len(documents)} documents with metadata")
        return enriched