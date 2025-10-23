# Knowledge Base

This directory contains source files for the RAG system.

## Structure

knowledge_base/
├── stackoverflow/ # Stack Overflow Q&A exports
├── docs/ # Python documentation PDFs
├── reddit/ # Reddit posts/comments
├── github/ # GitHub issues/PRs
└── custom/ # Your own examples

## Usage

from autofix_core.application.services.knowledge_builder import KnowledgeBuilder

kb = KnowledgeBuilder(memory_service)

Import Stack Overflow
kb.import_document(
'knowledge_base/stackoverflow/errors.html',
source_type='stackoverflow'
)

Import documentation
kb.import_document(
'knowledge_base/docs/python_guide.pdf',
source_type='docs'
)

undefined
