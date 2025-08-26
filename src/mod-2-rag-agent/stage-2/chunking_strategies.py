"""
Advanced chunking strategies module for intelligent document segmentation.

This module implements semantic, hierarchical, and decoupled chunking strategies
to optimize both retrieval accuracy and synthesis quality.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import hashlib
from enum import Enum

from llama_index.core import Document
from llama_index.core.node_parser import (
    SimpleNodeParser,
    SemanticSplitterNodeParser,
    HierarchicalNodeParser,
    SentenceWindowNodeParser,
    TokenTextSplitter
)
from llama_index.core.schema import BaseNode, TextNode, IndexNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.embeddings import BaseEmbedding
from loguru import logger
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import tiktoken

from config import Settings, ChunkingConfig


class ChunkType(Enum):
    """Enumeration of chunk types for hierarchical organization."""
    DOCUMENT_SUMMARY = "document_summary"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    RETRIEVAL = "retrieval"
    SYNTHESIS = "synthesis"


@dataclass
class Chunk:
    """
    Data class representing a text chunk with metadata.
    """
    id: str
    text: str
    chunk_type: ChunkType
    metadata: Dict[str, Any]
    parent_id: Optional[str] = None
    child_ids: List[str] = None
    embedding: Optional[np.ndarray] = None
    
    def __post_init__(self):
        """Initialize child_ids if not provided."""
        if self.child_ids is None:
            self.child_ids = []
    
    def to_node(self) -> TextNode:
        """
        Convert chunk to LlamaIndex TextNode.
        
        Returns:
            TextNode representation of the chunk
        """
        return TextNode(
            text=self.text,
            id_=self.id,
            metadata={
                **self.metadata,
                'chunk_type': self.chunk_type.value,
                'parent_id': self.parent_id,
                'child_ids': self.child_ids
            }
        )


class SemanticChunker:
    """
    Semantic chunking using embedding similarity.
    
    Groups semantically related sentences together based on
    embedding similarity thresholds.
    """
    
    def __init__(self, embedding_model: BaseEmbedding, config: ChunkingConfig):
        """
        Initialize semantic chunker.
        
        Args:
            embedding_model: Embedding model for similarity computation
            config: Chunking configuration
        """
        self.embedding_model = embedding_model
        self.config = config
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
    
    def chunk_document(self, document: Document) -> List[Chunk]:
        """
        Chunk document using semantic similarity.
        
        Args:
            document: Document to chunk
            
        Returns:
            List of semantic chunks
        """
        # Split into sentences
        sentences = self._split_into_sentences(document.text)
        
        if not sentences:
            return []
        
        # Generate embeddings for sentences
        embeddings = self._generate_embeddings(sentences)
        
        # Group sentences by similarity
        chunks = self._group_by_similarity(sentences, embeddings, document.metadata)
        
        logger.info(f"Created {len(chunks)} semantic chunks from {len(sentences)} sentences")
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        import re
        
        # Simple sentence splitting (can be enhanced with spacy)
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text)
        
        # Filter empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for text segments.
        
        Args:
            texts: List of text segments
            
        Returns:
            Array of embeddings
        """
        try:
            embeddings = []
            for text in texts:
                embedding = self.embedding_model.get_text_embedding(text)
                embeddings.append(embedding)
            return np.array(embeddings)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return np.array([])
    
    def _group_by_similarity(
        self, 
        sentences: List[str], 
        embeddings: np.ndarray,
        base_metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Group sentences by semantic similarity.
        
        Args:
            sentences: List of sentences
            embeddings: Sentence embeddings
            base_metadata: Base metadata for chunks
            
        Returns:
            List of grouped chunks
        """
        if len(sentences) == 0 or len(embeddings) == 0:
            return []
        
        chunks = []
        current_group = [sentences[0]]
        current_embeddings = [embeddings[0]]
        
        for i in range(1, len(sentences)):
            # Calculate similarity with current group
            avg_embedding = np.mean(current_embeddings, axis=0)
            similarity = cosine_similarity([embeddings[i]], [avg_embedding])[0][0]
            
            # Check if should add to current group
            threshold = self.config.semantic_breakpoint_threshold / 100.0
            
            if similarity >= threshold and self._get_token_count(' '.join(current_group + [sentences[i]])) <= self.config.max_size:
                current_group.append(sentences[i])
                current_embeddings.append(embeddings[i])
            else:
                # Create chunk from current group
                chunk = self._create_chunk(current_group, base_metadata, ChunkType.PARAGRAPH)
                chunks.append(chunk)
                
                # Start new group
                current_group = [sentences[i]]
                current_embeddings = [embeddings[i]]
        
        # Add final group
        if current_group:
            chunk = self._create_chunk(current_group, base_metadata, ChunkType.PARAGRAPH)
            chunks.append(chunk)
        
        return chunks
    
    def _get_token_count(self, text: str) -> int:
        """
        Get token count for text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Token count
        """
        return len(self.tokenizer.encode(text))
    
    def _create_chunk(
        self, 
        sentences: List[str], 
        base_metadata: Dict[str, Any],
        chunk_type: ChunkType
    ) -> Chunk:
        """
        Create a chunk from grouped sentences.
        
        Args:
            sentences: List of sentences
            base_metadata: Base metadata
            chunk_type: Type of chunk
            
        Returns:
            Created chunk
        """
        text = ' '.join(sentences)
        chunk_id = hashlib.md5(text.encode()).hexdigest()
        
        return Chunk(
            id=chunk_id,
            text=text,
            chunk_type=chunk_type,
            metadata={
                **base_metadata,
                'sentence_count': len(sentences),
                'token_count': self._get_token_count(text),
                'char_count': len(text)
            }
        )


class HierarchicalChunker:
    """
    Hierarchical chunking for multi-level document organization.
    
    Creates chunks at different granularity levels: document,
    section, paragraph, and sentence.
    """
    
    def __init__(self, config: ChunkingConfig, llm=None):
        """
        Initialize hierarchical chunker.
        
        Args:
            config: Chunking configuration
            llm: Optional LLM for summary generation
        """
        self.config = config
        self.llm = llm
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
    
    def chunk_document(self, document: Document) -> Dict[str, List[Chunk]]:
        """
        Create hierarchical chunks from document.
        
        Args:
            document: Document to chunk
            
        Returns:
            Dictionary of chunks organized by level
        """
        chunks_by_level = {
            'document': [],
            'section': [],
            'paragraph': [],
            'sentence': []
        }
        
        # Create document-level summary chunk
        doc_chunk = self._create_document_chunk(document)
        chunks_by_level['document'].append(doc_chunk)
        
        # Extract sections
        sections = self._extract_sections(document.text)
        
        for section_idx, section in enumerate(sections):
            # Create section chunk
            section_chunk = self._create_section_chunk(
                section, 
                doc_chunk.id, 
                section_idx,
                document.metadata
            )
            chunks_by_level['section'].append(section_chunk)
            
            # Extract paragraphs from section
            paragraphs = self._extract_paragraphs(section['content'])
            
            for para_idx, paragraph in enumerate(paragraphs):
                # Create paragraph chunk
                para_chunk = self._create_paragraph_chunk(
                    paragraph,
                    section_chunk.id,
                    para_idx,
                    document.metadata
                )
                chunks_by_level['paragraph'].append(para_chunk)
                
                # Extract sentences from paragraph
                sentences = self._extract_sentences(paragraph)
                
                for sent_idx, sentence in enumerate(sentences):
                    # Create sentence chunk
                    sent_chunk = self._create_sentence_chunk(
                        sentence,
                        para_chunk.id,
                        sent_idx,
                        document.metadata
                    )
                    chunks_by_level['sentence'].append(sent_chunk)
                    
                    # Update parent-child relationships
                    para_chunk.child_ids.append(sent_chunk.id)
                
                section_chunk.child_ids.append(para_chunk.id)
            
            doc_chunk.child_ids.append(section_chunk.id)
        
        logger.info(
            f"Created hierarchical chunks: "
            f"{len(chunks_by_level['document'])} documents, "
            f"{len(chunks_by_level['section'])} sections, "
            f"{len(chunks_by_level['paragraph'])} paragraphs, "
            f"{len(chunks_by_level['sentence'])} sentences"
        )
        
        return chunks_by_level
    
    def _create_document_chunk(self, document: Document) -> Chunk:
        """
        Create document-level summary chunk.
        
        Args:
            document: Source document
            
        Returns:
            Document-level chunk
        """
        # Generate summary if LLM available
        if self.llm:
            summary = self._generate_summary(document.text, max_tokens=200)
        else:
            # Use first N tokens as summary
            summary = self._truncate_to_tokens(document.text, 200)
        
        chunk_id = hashlib.md5(f"doc_{document.metadata.get('filename', '')}".encode()).hexdigest()
        
        return Chunk(
            id=chunk_id,
            text=summary,
            chunk_type=ChunkType.DOCUMENT_SUMMARY,
            metadata={
                **document.metadata,
                'level': 'document',
                'original_length': len(document.text)
            }
        )
    
    def _create_section_chunk(
        self, 
        section: Dict[str, str], 
        parent_id: str,
        index: int,
        base_metadata: Dict[str, Any]
    ) -> Chunk:
        """
        Create section-level chunk.
        
        Args:
            section: Section data
            parent_id: Parent document chunk ID
            index: Section index
            base_metadata: Base metadata
            
        Returns:
            Section-level chunk
        """
        chunk_id = hashlib.md5(f"section_{parent_id}_{index}".encode()).hexdigest()
        
        return Chunk(
            id=chunk_id,
            text=section['content'][:self.config.max_size],
            chunk_type=ChunkType.SECTION,
            metadata={
                **base_metadata,
                'level': 'section',
                'section_title': section.get('title', f'Section {index + 1}'),
                'section_index': index
            },
            parent_id=parent_id
        )
    
    def _create_paragraph_chunk(
        self,
        paragraph: str,
        parent_id: str,
        index: int,
        base_metadata: Dict[str, Any]
    ) -> Chunk:
        """
        Create paragraph-level chunk.
        
        Args:
            paragraph: Paragraph text
            parent_id: Parent section chunk ID
            index: Paragraph index
            base_metadata: Base metadata
            
        Returns:
            Paragraph-level chunk
        """
        chunk_id = hashlib.md5(f"para_{parent_id}_{index}".encode()).hexdigest()
        
        return Chunk(
            id=chunk_id,
            text=paragraph,
            chunk_type=ChunkType.PARAGRAPH,
            metadata={
                **base_metadata,
                'level': 'paragraph',
                'paragraph_index': index,
                'token_count': self._get_token_count(paragraph)
            },
            parent_id=parent_id
        )
    
    def _create_sentence_chunk(
        self,
        sentence: str,
        parent_id: str,
        index: int,
        base_metadata: Dict[str, Any]
    ) -> Chunk:
        """
        Create sentence-level chunk with window context.
        
        Args:
            sentence: Sentence text
            parent_id: Parent paragraph chunk ID
            index: Sentence index
            base_metadata: Base metadata
            
        Returns:
            Sentence-level chunk
        """
        chunk_id = hashlib.md5(f"sent_{parent_id}_{index}".encode()).hexdigest()
        
        return Chunk(
            id=chunk_id,
            text=sentence,
            chunk_type=ChunkType.SENTENCE,
            metadata={
                **base_metadata,
                'level': 'sentence',
                'sentence_index': index,
                'token_count': self._get_token_count(sentence)
            },
            parent_id=parent_id
        )
    
    def _extract_sections(self, text: str) -> List[Dict[str, str]]:
        """
        Extract sections from text.
        
        Args:
            text: Document text
            
        Returns:
            List of sections with titles and content
        """
        import re
        
        # Pattern for section headers (various formats)
        header_patterns = [
            re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE),  # Markdown
            re.compile(r'^([A-Z][^.!?]*):$', re.MULTILINE),   # Title with colon
            re.compile(r'^\d+\.\s+([A-Z].+)$', re.MULTILINE), # Numbered sections
        ]
        
        sections = []
        current_section = {'title': 'Introduction', 'content': ''}
        
        lines = text.split('\n')
        
        for line in lines:
            is_header = False
            header_title = None
            
            for pattern in header_patterns:
                match = pattern.match(line)
                if match:
                    is_header = True
                    header_title = match.group(2) if pattern == header_patterns[0] else match.group(1)
                    break
            
            if is_header:
                # Save current section if it has content
                if current_section['content'].strip():
                    sections.append(current_section)
                
                # Start new section
                current_section = {'title': header_title, 'content': ''}
            else:
                current_section['content'] += line + '\n'
        
        # Add final section
        if current_section['content'].strip():
            sections.append(current_section)
        
        # If no sections found, treat entire text as one section
        if not sections:
            sections = [{'title': 'Content', 'content': text}]
        
        return sections
    
    def _extract_paragraphs(self, text: str) -> List[str]:
        """
        Extract paragraphs from text.
        
        Args:
            text: Section text
            
        Returns:
            List of paragraphs
        """
        # Split by double newlines or single newlines with substantial text
        paragraphs = text.split('\n\n')
        
        # Clean and filter paragraphs
        cleaned = []
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > self.config.min_size:
                cleaned.append(para)
        
        return cleaned
    
    def _extract_sentences(self, text: str) -> List[str]:
        """
        Extract sentences from text.
        
        Args:
            text: Paragraph text
            
        Returns:
            List of sentences
        """
        import re
        
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text)
        
        return [s.strip() for s in sentences if s.strip()]
    
    def _generate_summary(self, text: str, max_tokens: int) -> str:
        """
        Generate summary using LLM.
        
        Args:
            text: Text to summarize
            max_tokens: Maximum tokens for summary
            
        Returns:
            Generated summary
        """
        if not self.llm:
            return self._truncate_to_tokens(text, max_tokens)
        
        try:
            prompt = f"Summarize the following text in {max_tokens} tokens or less:\n\n{text[:3000]}"
            response = self.llm.complete(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return self._truncate_to_tokens(text, max_tokens)
    
    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to maximum token count.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum token count
            
        Returns:
            Truncated text
        """
        tokens = self.tokenizer.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        truncated_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(truncated_tokens)
    
    def _get_token_count(self, text: str) -> int:
        """
        Get token count for text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Token count
        """
        return len(self.tokenizer.encode(text))


class DecoupledChunker:
    """
    Decoupled chunking strategy separating retrieval and synthesis chunks.
    
    Creates small chunks for retrieval accuracy and larger chunks
    for synthesis context.
    """
    
    def __init__(self, config: ChunkingConfig):
        """
        Initialize decoupled chunker.
        
        Args:
            config: Chunking configuration
        """
        self.config = config
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
    
    def create_decoupled_chunks(self, document: Document) -> Tuple[List[Chunk], List[Chunk]]:
        """
        Create separate retrieval and synthesis chunks.
        
        Args:
            document: Document to chunk
            
        Returns:
            Tuple of (retrieval_chunks, synthesis_chunks)
        """
        # Create small retrieval chunks
        retrieval_chunks = self._create_retrieval_chunks(document)
        
        # Create larger synthesis chunks
        synthesis_chunks = self._create_synthesis_chunks(document)
        
        # Link retrieval chunks to synthesis chunks
        self._link_chunks(retrieval_chunks, synthesis_chunks)
        
        logger.info(
            f"Created {len(retrieval_chunks)} retrieval chunks and "
            f"{len(synthesis_chunks)} synthesis chunks"
        )
        
        return retrieval_chunks, synthesis_chunks
    
    def _create_retrieval_chunks(self, document: Document) -> List[Chunk]:
        """
        Create small chunks optimized for retrieval.
        
        Args:
            document: Source document
            
        Returns:
            List of retrieval chunks
        """
        chunks = []
        text = document.text
        
        # Use smaller chunk size for retrieval
        chunk_size = min(self.config.max_size // 2, 256)
        overlap = self.config.overlap
        
        tokens = self.tokenizer.encode(text)
        
        for i in range(0, len(tokens), chunk_size - overlap):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunk_id = hashlib.md5(f"retrieval_{i}_{chunk_text[:50]}".encode()).hexdigest()
            
            chunk = Chunk(
                id=chunk_id,
                text=chunk_text,
                chunk_type=ChunkType.RETRIEVAL,
                metadata={
                    **document.metadata,
                    'start_position': i,
                    'token_count': len(chunk_tokens),
                    'chunk_index': i // (chunk_size - overlap)
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_synthesis_chunks(self, document: Document) -> List[Chunk]:
        """
        Create larger chunks optimized for synthesis.
        
        Args:
            document: Source document
            
        Returns:
            List of synthesis chunks
        """
        chunks = []
        text = document.text
        
        # Use larger chunk size for synthesis
        chunk_size = self.config.max_size
        overlap = self.config.overlap * 2  # More overlap for better context
        
        tokens = self.tokenizer.encode(text)
        
        for i in range(0, len(tokens), chunk_size - overlap):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunk_id = hashlib.md5(f"synthesis_{i}_{chunk_text[:50]}".encode()).hexdigest()
            
            chunk = Chunk(
                id=chunk_id,
                text=chunk_text,
                chunk_type=ChunkType.SYNTHESIS,
                metadata={
                    **document.metadata,
                    'start_position': i,
                    'token_count': len(chunk_tokens),
                    'chunk_index': i // (chunk_size - overlap)
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _link_chunks(self, retrieval_chunks: List[Chunk], synthesis_chunks: List[Chunk]):
        """
        Link retrieval chunks to their corresponding synthesis chunks.
        
        Args:
            retrieval_chunks: List of retrieval chunks
            synthesis_chunks: List of synthesis chunks
        """
        for ret_chunk in retrieval_chunks:
            ret_start = ret_chunk.metadata['start_position']
            
            # Find overlapping synthesis chunks
            for syn_chunk in synthesis_chunks:
                syn_start = syn_chunk.metadata['start_position']
                syn_end = syn_start + syn_chunk.metadata['token_count']
                
                # Check if retrieval chunk falls within synthesis chunk
                if syn_start <= ret_start < syn_end:
                    ret_chunk.parent_id = syn_chunk.id
                    if ret_chunk.id not in syn_chunk.child_ids:
                        syn_chunk.child_ids.append(ret_chunk.id)
                    break


class SmartChunkingPipeline:
    """
    Main chunking pipeline orchestrator.
    
    Combines different chunking strategies to create a comprehensive
    chunk structure for optimal retrieval and synthesis.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize smart chunking pipeline.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.config = settings.chunking
        
        # Initialize embedding model
        self.embedding_model = OpenAIEmbedding(
            api_key=settings.openai.api_key,
            model=settings.openai.embedding_model
        )
        
        # Initialize chunkers
        self.semantic_chunker = SemanticChunker(self.embedding_model, self.config)
        self.hierarchical_chunker = HierarchicalChunker(self.config)
        self.decoupled_chunker = DecoupledChunker(self.config)
    
    def chunk_document(self, document: Document) -> Dict[str, Any]:
        """
        Apply smart chunking strategies to document.
        
        Args:
            document: Document to chunk
            
        Returns:
            Dictionary containing all chunk types
        """
        result = {
            'semantic_chunks': [],
            'hierarchical_chunks': {},
            'retrieval_chunks': [],
            'synthesis_chunks': [],
            'metadata': {}
        }
        
        try:
            # Apply semantic chunking
            result['semantic_chunks'] = self.semantic_chunker.chunk_document(document)
            
            # Apply hierarchical chunking
            result['hierarchical_chunks'] = self.hierarchical_chunker.chunk_document(document)
            
            # Apply decoupled chunking
            retrieval, synthesis = self.decoupled_chunker.create_decoupled_chunks(document)
            result['retrieval_chunks'] = retrieval
            result['synthesis_chunks'] = synthesis
            
            # Add metadata
            result['metadata'] = {
                'total_chunks': (
                    len(result['semantic_chunks']) +
                    sum(len(v) for v in result['hierarchical_chunks'].values()) +
                    len(result['retrieval_chunks']) +
                    len(result['synthesis_chunks'])
                ),
                'document_id': document.metadata.get('filename', 'unknown'),
                'chunking_timestamp': logger.time()
            }
            
            logger.info(f"Successfully chunked document with {result['metadata']['total_chunks']} total chunks")
            
        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            raise
        
        return result
    
    def chunk_batch(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        Apply smart chunking to batch of documents.
        
        Args:
            documents: List of documents to chunk
            
        Returns:
            List of chunking results
        """
        results = []
        
        for doc in documents:
            try:
                result = self.chunk_document(doc)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to chunk document {doc.metadata.get('filename', 'unknown')}: {e}")
                continue
        
        logger.info(f"Chunked {len(results)} out of {len(documents)} documents")
        return results