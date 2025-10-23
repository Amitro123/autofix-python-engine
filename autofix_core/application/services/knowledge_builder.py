"""
Knowledge Builder Service
Preprocesses data from multiple sources using MarkItDown
Imports into RAG memory for enhanced code fixing
"""

from markitdown import MarkItDown
from typing import List, Dict, Optional
import re
from pathlib import Path
from autofix.helpers.logging_utils import get_logger

# Optional Reddit support
try:
    import praw
    REDDIT_AVAILABLE = True
except ImportError:
    REDDIT_AVAILABLE = False

from datetime import datetime

logger = get_logger(__name__)


class KnowledgeBuilder:
    """Build and enrich RAG knowledge base from multiple sources"""
    
    def __init__(self, memory_service, reddit_config=None):
        """
        Initialize knowledge builder
        
        Args:
            memory_service: MemoryService instance for storing fixes
            reddit_config: Optional dict with Reddit API credentials
                {
                    'client_id': 'your_client_id',
                    'client_secret': 'your_client_secret',
                    'user_agent': 'autofix-scraper/1.0'
                }
        """
        self.md = MarkItDown()
        self.memory = memory_service
        self.reddit = None
        
        # Initialize Reddit if config provided and available
        if reddit_config and REDDIT_AVAILABLE:
            try:
                self.reddit = praw.Reddit(**reddit_config)
                logger.info("Reddit API initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Reddit: {e}")
        elif reddit_config and not REDDIT_AVAILABLE:
            logger.warning("Reddit config provided but praw not installed. Run: pip install praw")
        
        self.stats = {
            'total_files_processed': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'total_examples_extracted': 0,
            'total_examples_stored': 0,
            'reddit_threads_processed': 0
        }
    
    def import_document(
        self, 
        file_path: str,
        source_type: str = "generic",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Import any supported document into knowledge base
        
        Args:
            file_path: Path to document (PDF, HTML, Word, Excel, etc.)
            source_type: Type of source (stackoverflow, docs, logs, github, generic)
            metadata: Additional metadata to store with examples
            
        Returns:
            Import statistics and results
        """
        try:
            logger.info(f"Importing document: {file_path} (type: {source_type})")
            
            # Convert to Markdown using MarkItDown
            result = self.md.convert(file_path)
            markdown_content = result.text_content
            
            logger.info(f"Converted to Markdown: {len(markdown_content)} characters")
            
            # Extract code examples based on source type
            if source_type == "stackoverflow":
                examples = self._extract_stackoverflow_qa(markdown_content)
            elif source_type == "docs":
                examples = self._extract_doc_examples(markdown_content)
            elif source_type == "logs":
                examples = self._extract_error_logs(markdown_content)
            elif source_type == "github":
                examples = self._extract_github_issues(markdown_content)
            else:
                examples = self._extract_generic_examples(markdown_content)
            
            logger.info(f"Extracted {len(examples)} code examples")
            
            # Store in memory with metadata
            stored_count = 0
            for example in examples:
                if self._validate_example(example):
                    # Add source metadata
                    example_metadata = {
                        'source_file': Path(file_path).name,
                        'source_type': source_type,
                        'imported_at': None,  # Will be added by memory service
                        **(metadata or {}),
                        **(example.get('metadata', {}))
                    }
                    
                    fix_id = self.memory.store_fix(
                        original_code=example['original_code'],
                        error_type=example.get('error_type', 'Unknown'),
                        fixed_code=example['fixed_code'],
                        method=f'imported_{source_type}',
                        metadata=example_metadata
                    )
                    
                    if fix_id:
                        stored_count += 1
            
            # Update stats
            self.stats['total_files_processed'] += 1
            self.stats['successful_imports'] += 1
            self.stats['total_examples_extracted'] += len(examples)
            self.stats['total_examples_stored'] += stored_count
            
            result = {
                'success': True,
                'file': file_path,
                'source_type': source_type,
                'examples_found': len(examples),
                'examples_stored': stored_count,
                'markdown_size': len(markdown_content)
            }
            
            logger.info(f"Import successful: {stored_count}/{len(examples)} examples stored")
            return result
            
        except Exception as e:
            logger.error(f"Error importing document {file_path}: {e}", exc_info=True)
            
            self.stats['total_files_processed'] += 1
            self.stats['failed_imports'] += 1
            
            return {
                'success': False,
                'file': file_path,
                'error': str(e)
            }
    
    # ==================== REDDIT SUPPORT ====================
    
    def import_from_reddit(
        self,
        subreddit_name: str,
        query: str = "python error fix",
        limit: int = 100,
        time_filter: str = "month"
    ) -> Dict:
        """
        Import code fixes from Reddit posts
        
        Args:
            subreddit_name: Subreddit to search (e.g., 'learnpython')
            query: Search query
            limit: Max posts to fetch
            time_filter: 'hour', 'day', 'week', 'month', 'year', 'all'
            
        Returns:
            Import statistics
        """
        if not self.reddit:
            return {
                'success': False,
                'error': 'Reddit API not configured or praw not installed'
            }
        
        try:
            logger.info(f"Searching r/{subreddit_name} for: {query}")
            
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Search posts
            posts = subreddit.search(
                query=query,
                limit=limit,
                time_filter=time_filter,
                sort='relevance'
            )
            
            examples_found = 0
            examples_stored = 0
            posts_processed = 0
            
            for post in posts:
                # Extract examples from post + comments
                post_examples = self._extract_reddit_post(post)
                examples_found += len(post_examples)
                
                # Store valid examples
                for example in post_examples:
                    if self._validate_example(example):
                        metadata = {
                            'source': 'reddit',
                            'subreddit': subreddit_name,
                            'post_title': post.title[:100],
                            'post_url': f'https://reddit.com{post.permalink}',
                            'post_score': post.score,
                            'post_date': datetime.fromtimestamp(post.created_utc).isoformat(),
                            **example.get('metadata', {})
                        }
                        
                        fix_id = self.memory.store_fix(
                            original_code=example['original_code'],
                            error_type=example.get('error_type', 'Unknown'),
                            fixed_code=example['fixed_code'],
                            method='reddit',
                            metadata=metadata
                        )
                        
                        if fix_id:
                            examples_stored += 1
                
                posts_processed += 1
            
            self.stats['reddit_threads_processed'] += posts_processed
            self.stats['total_examples_extracted'] += examples_found
            self.stats['total_examples_stored'] += examples_stored
            
            logger.info(f"Reddit import complete: {examples_stored}/{examples_found} examples stored from {posts_processed} posts")
            
            return {
                'success': True,
                'subreddit': subreddit_name,
                'query': query,
                'posts_processed': posts_processed,
                'examples_found': examples_found,
                'examples_stored': examples_stored
            }
            
        except Exception as e:
            logger.error(f"Error importing from Reddit: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_reddit_post(self, post) -> List[Dict]:
        """Extract code examples from Reddit post + comments"""
        examples = []
        
        # Get post body
        post_text = post.selftext
        
        # Extract code blocks from post
        post_codes = self._extract_code_blocks(post_text)
        
        # Get all comments (expand "more comments")
        try:
            post.comments.replace_more(limit=0)
        except Exception as e:
            logger.warning(f"Could not expand comments: {e}")
        
        # Look for solution patterns in comments
        for comment in post.comments.list():
            comment_text = comment.body
            
            # Check if this is likely a solution
            if self._is_solution_comment(comment_text):
                comment_codes = self._extract_code_blocks(comment_text)
                
                # Pair post code with comment code
                if post_codes and comment_codes:
                    for original in post_codes:
                        for fixed in comment_codes:
                            if original != fixed and len(original) > 20 and len(fixed) > 20:
                                examples.append({
                                    'original_code': original,
                                    'fixed_code': fixed,
                                    'error_type': self._detect_error_from_reddit_text(post_text),
                                    'metadata': {
                                        'comment_score': comment.score,
                                        'extraction_method': 'reddit_post_comment'
                                    }
                                })
        
        return examples
    
    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract Python code blocks from Reddit markdown"""
        python_blocks = []
        
        # Pattern 1: ``````
        pattern1 = re.findall(r'``````', text, re.DOTALL)
        python_blocks.extend(pattern1)
        
        # Pattern 2: `````` (without language)
        pattern2 = re.findall(r'``````', text, re.DOTALL)
        # Filter for Python-looking code
        python_blocks.extend([b for b in pattern2 if self._looks_like_python(b)])
        
        # Pattern 3: 4-space indented code blocks
        lines = text.split('\n')
        current_block = []
        for line in lines:
            if line.startswith('    '):
                current_block.append(line[4:])  # Remove 4 spaces
            else:
                if current_block:
                    block_text = '\n'.join(current_block)
                    if self._looks_like_python(block_text):
                        python_blocks.append(block_text)
                    current_block = []
        
        # Don't forget last block
        if current_block:
            block_text = '\n'.join(current_block)
            if self._looks_like_python(block_text):
                python_blocks.append(block_text)
        
        # Clean and deduplicate
        cleaned_blocks = []
        seen = set()
        for block in python_blocks:
            block = block.strip()
            if block and block not in seen and len(block) > 20:
                cleaned_blocks.append(block)
                seen.add(block)
        
        return cleaned_blocks
    
    def _is_solution_comment(self, comment_text: str) -> bool:
        """Check if comment likely contains a solution"""
        solution_indicators = [
            'try this', 'should be', 'change to', 'fix',
            'solution', 'correct', 'instead', 'better',
            'you need', 'you should', 'the issue is',
            'problem is', 'that works', 'this works',
            'use this', 'replace with', 'modify'
        ]
        
        text_lower = comment_text.lower()
        return any(indicator in text_lower for indicator in solution_indicators)
    
    def _detect_error_from_reddit_text(self, text: str) -> str:
        """Detect error type from Reddit post text"""
        text_lower = text.lower()
        
        error_patterns = {
            'IndexError': ['indexerror', 'index error', 'list index out of range'],
            'TypeError': ['typeerror', 'type error', 'cannot concatenate', 'unsupported operand'],
            'KeyError': ['keyerror', 'key error'],
            'AttributeError': ['attributeerror', 'attribute error', 'has no attribute'],
            'ValueError': ['valueerror', 'value error', 'invalid literal'],
            'ZeroDivisionError': ['zerodivisionerror', 'division by zero'],
            'ImportError': ['importerror', 'import error', 'no module named'],
            'SyntaxError': ['syntaxerror', 'syntax error', 'invalid syntax'],
            'NameError': ['nameerror', 'name error', 'is not defined']
        }
        
        for error_type, patterns in error_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return error_type
        
        return 'Unknown'
    
    def _looks_like_python(self, code: str) -> bool:
        """Quick heuristic to check if code looks like Python"""
        if not code or len(code) < 20:
            return False
        
        python_keywords = [
            'def ', 'class ', 'import ', 'from ', 'print(',
            'if ', 'for ', 'while ', 'try:', 'except',
            'with ', 'return ', 'yield ', '= '
        ]
        
        # Must have at least one Python keyword
        has_keyword = any(keyword in code for keyword in python_keywords)

        # Check for SQL keywords (negatives)
        sql_keywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE']
        is_sql = any(keyword in code.upper() for keyword in sql_keywords)

        
        # Must not look like other languages
        not_other_lang = not any([
            is_sql,
            code.strip().startswith('<?php'),  # PHP
            code.strip().startswith('package '),  # Java
            '///' in code,  # C#
            'function(' in code,  # R
        ])
        
        return has_keyword and not_other_lang
    
    def bulk_import_from_reddit(
        self,
        subreddits: List[str] = None,
        queries: List[str] = None,
        limit_per_query: int = 50
    ) -> Dict:
        """
        Import from multiple subreddits and queries
        
        Args:
            subreddits: List of subreddit names (default: Python-related)
            queries: List of search queries (default: common error patterns)
            limit_per_query: Max posts per query
            
        Returns:
            Aggregate statistics
        """
        if not self.reddit:
            return {
                'success': False,
                'error': 'Reddit API not configured'
            }
        
        # Default subreddits
        if subreddits is None:
            subreddits = ['learnpython', 'Python', 'pythonhelp']
        
        # Default queries
        if queries is None:
            queries = [
                'python error help',
                'IndexError fix',
                'TypeError python',
                'KeyError solution',
                'AttributeError help',
                'python debug',
                'beginner error'
            ]
        
        results = []
        
        for subreddit in subreddits:
            for query in queries:
                logger.info(f"Importing from r/{subreddit} with query: '{query}'")
                
                result = self.import_from_reddit(
                    subreddit_name=subreddit,
                    query=query,
                    limit=limit_per_query
                )
                
                results.append(result)
        
        # Aggregate
        summary = {
            'success': True,
            'subreddits': subreddits,
            'queries': queries,
            'total_posts_processed': sum(r.get('posts_processed', 0) for r in results if r.get('success')),
            'total_examples_found': sum(r.get('examples_found', 0) for r in results if r.get('success')),
            'total_examples_stored': sum(r.get('examples_stored', 0) for r in results if r.get('success')),
            'failed_imports': sum(1 for r in results if not r.get('success')),
            'results': results
        }
        
        return summary
    
    # ==================== FILE-BASED EXTRACTION ====================
    
    def _validate_example(self, example: Dict) -> bool:
        """Validate that example has required fields and quality"""
        if not example.get('original_code') or not example.get('fixed_code'):
            return False
        
        # Check minimum code length (avoid trivial examples)
        if len(example['original_code'].strip()) < 10:
            return False
        
        if len(example['fixed_code'].strip()) < 10:
            return False
        
        # Check that codes are different
        if example['original_code'].strip() == example['fixed_code'].strip():
            return False
        
        return True
    
    def _extract_stackoverflow_qa(self, markdown: str) -> List[Dict]:
        """Extract Q&A pairs from Stack Overflow HTML"""
        examples = []
        
        # Find all code blocks (FIXED regex!)
        code_blocks = re.findall(r'``````', markdown, re.DOTALL)
        
        # Pair consecutive code blocks as question/answer
        for i in range(0, len(code_blocks) - 1, 2):
            if i + 1 < len(code_blocks):
                original = code_blocks[i].strip()
                fixed = code_blocks[i + 1].strip()
                
                error_type = self._detect_error_type_from_code(original)
                
                examples.append({
                    'original_code': original,
                    'fixed_code': fixed,
                    'error_type': error_type,
                    'metadata': {'extraction_method': 'stackoverflow_qa'}
                })
        
        return examples
    
    def _extract_doc_examples(self, markdown: str) -> List[Dict]:
        """Extract examples from documentation"""
        examples = []
        
        sections = re.split(
            r'(?:Bad|Before|Wrong|Incorrect|❌)[\s:]+',
            markdown,
            flags=re.IGNORECASE
        )
        
        for section in sections[1:]:
            good_match = re.search(
                r'(?:Good|After|Correct|Right|✅)[\s:]+(.*?)(?:``````|$)',
                section,
                flags=re.DOTALL | re.IGNORECASE
            )
            
            if good_match:
                bad_code_match = re.search(r'``````', section, re.DOTALL)
                
                if bad_code_match:
                    bad_code = bad_code_match.group(1).strip()
                    
                    good_code_match = re.search(
                        r'``````',
                        good_match.group(0),
                        re.DOTALL
                    )
                    
                    if good_code_match:
                        good_code = good_code_match.group(1).strip()
                        
                        examples.append({
                            'original_code': bad_code,
                            'fixed_code': good_code,
                            'error_type': self._detect_error_type_from_code(bad_code),
                            'metadata': {'extraction_method': 'documentation'}
                        })
        
        return examples
    
    def _extract_error_logs(self, markdown: str) -> List[Dict]:
        """Extract error patterns from logs/tables"""
        examples = []
        
        table_rows = re.findall(r'\|(.*?)\|(.*?)\|(.*?)\|', markdown)
        
        for row in table_rows[1:]:
            if len(row) >= 3:
                code_cell = row[0].strip()
                error_cell = row[1].strip()
                fix_cell = row[2].strip()
                
                code = self._clean_code_from_cell(code_cell)
                fix = self._clean_code_from_cell(fix_cell)
                
                if code and fix:
                    examples.append({
                        'original_code': code,
                        'fixed_code': fix,
                        'error_type': error_cell if error_cell else 'Unknown',
                        'metadata': {'extraction_method': 'error_logs'}
                    })
        
        return examples
    
    def _extract_github_issues(self, markdown: str) -> List[Dict]:
        """Extract fixes from GitHub issues/PRs"""
        examples = []
        
        patterns = [
            (r'This code:.*?``````', r'Fixed version:.*?``````'),
            (r'Bug:.*?``````', r'Solution:.*?``````'),
            (r'Error:.*?``````', r'Fix:.*?``````')
        ]
        
        for bug_pattern, fix_pattern in patterns:
            bug_matches = re.finditer(bug_pattern, markdown, re.DOTALL)
            
            for bug_match in bug_matches:
                bug_code = bug_match.group(1).strip()
                
                remaining_text = markdown[bug_match.end():]
                fix_match = re.search(fix_pattern, remaining_text, re.DOTALL)
                
                if fix_match:
                    fix_code = fix_match.group(1).strip()
                    
                    examples.append({
                        'original_code': bug_code,
                        'fixed_code': fix_code,
                        'error_type': self._detect_error_type_from_code(bug_code),
                        'metadata': {'extraction_method': 'github_issues'}
                    })
        
        return examples
    
    def _extract_generic_examples(self, markdown: str) -> List[Dict]:
        """Extract code blocks from generic markdown"""
        examples = []
        
        code_blocks = re.findall(r'``````', markdown, re.DOTALL)
        
        # Pair consecutive blocks
        for i in range(0, len(code_blocks) - 1, 2):
            if i + 1 < len(code_blocks):
                original = code_blocks[i].strip()
                fixed = code_blocks[i + 1].strip()
                
                examples.append({
                    'original_code': original,
                    'fixed_code': fixed,
                    'error_type': self._detect_error_type_from_code(original),
                    'metadata': {'extraction_method': 'generic'}
                })
        
        return examples
    
    def _detect_error_type_from_code(self, code: str) -> str: #amitro to do- handle on regex and move them to constants
        """Detect likely error type from code patterns"""
        # Check KeyError FIRST (before IndexError)
        if re.search(r'\[[\'"]\w+[\'"]\]', code) and '.get(' not in code:
            return 'KeyError'
        # Then check IndexError
        elif re.search(r'\[\d+\]', code) and 'len(' not in code:
            return 'IndexError'
        elif re.search(r'\bint\(|str\(|float\(', code):
            return 'TypeError'
        elif re.search(r'\.\w+\(', code) and 'self' not in code:
            return 'AttributeError'
        elif '/' in code and 'if' not in code:
            return 'ZeroDivisionError'
        else:
            return 'Unknown'

    
    def _clean_code_from_cell(self, cell_text: str) -> str:
        """Clean code from table cell"""
        cleaned = re.sub(r'`+', '', cell_text)
        cleaned = cleaned.strip()
        if len(cleaned) > 5:
            return cleaned
        return ""
    
    def bulk_import(
        self,
        directory: str,
        source_type: str = "generic",
        pattern: str = "*",
        recursive: bool = True
    ) -> Dict:
        """Import all supported files from a directory"""
        path = Path(directory)
        
        if not path.exists():
            return {
                'success': False,
                'error': f'Directory not found: {directory}'
            }
        
        extensions = {'.pdf', '.html', '.htm', '.docx', '.xlsx', '.xls', '.md', '.txt'}
        
        if recursive:
            files = list(path.rglob(pattern))
        else:
            files = list(path.glob(pattern))
        
        files = [f for f in files if f.suffix.lower() in extensions]
        
        logger.info(f"Found {len(files)} supported files in {directory}")
        
        results = []
        for file_path in files:
            result = self.import_document(str(file_path), source_type)
            results.append(result)
        
        summary = {
            'success': True,
            'directory': directory,
            'total_files': len(files),
            'successful_imports': sum(1 for r in results if r['success']),
            'failed_imports': sum(1 for r in results if not r['success']),
            'total_examples': sum(r.get('examples_stored', 0) for r in results),
            'results': results
        }
        
        return summary
    
    def get_stats(self) -> Dict:
        """Get import statistics"""
        return {
            **self.stats,
            'memory_stats': self.memory.get_stats(),
            'reddit_available': REDDIT_AVAILABLE and self.reddit is not None
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_files_processed': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'total_examples_extracted': 0,
            'total_examples_stored': 0,
            'reddit_threads_processed': 0
        }
