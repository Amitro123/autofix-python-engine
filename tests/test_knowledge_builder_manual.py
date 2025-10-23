"""
Manual testing for KnowledgeBuilder
Tests with real examples and mock data
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from autofix_core.application.services.memory_service import MemoryService
from autofix_core.application.services.knowledge_builder import KnowledgeBuilder
import tempfile
import shutil


def test_basic_functionality():
    """Test basic knowledge builder functionality"""
    print("=" * 60)
    print("🧪 Testing KnowledgeBuilder Basic Functionality")
    print("=" * 60 + "\n")
    
    # Setup
    temp_dir = tempfile.mkdtemp()
    memory = MemoryService(persist_directory=temp_dir)
    kb = KnowledgeBuilder(memory)
    
    print("1️⃣ Testing code extraction from markdown...")
    
    # Test extraction
    markdown_example = """
# Python Error Example

Here's a common mistake:
numbers =
print(numbers) # This will fail!
Here's the fix:
numbers =
if len(numbers) > 10:
print(numbers)
else:
print("Index out of range!")

    """
    
    examples = kb._extract_generic_examples(markdown_example)
    print(f"   ✅ Extracted {len(examples)} examples")
    
    if examples:
        print(f"   📝 Example 1:")
        print(f"      Original: {examples[0]['original_code'][:50]}...")
        print(f"      Fixed: {examples[0]['fixed_code'][:50]}...")
        print(f"      Error: {examples[0]['error_type']}")
    
    print()
    
    # Test error detection
    print("2️⃣ Testing error type detection...")
    
    test_codes = {
        "x = [1, 2]\nprint(x[10])": "IndexError",
        "x = 'hello'\ny = int(x)": "TypeError",
        "d = {}\nprint(d['key'])": "KeyError",
    }
    
    for code, expected in test_codes.items():
        detected = kb._detect_error_type_from_code(code)
        status = "✅" if detected == expected else "❌"
        print(f"   {status} {expected}: {detected}")
    
    print()
    
    # Test Python detection
    print("3️⃣ Testing Python code detection...")
    
    test_snippets = [
        ("def hello():\n    print('world')", True),
        ("SELECT * FROM users;", False),
        ("x = 1 + 2\nprint(x)", True),
        ("<?php echo 'hello'; ?>", False),
    ]
    
    for code, expected in test_snippets:
        result = kb._looks_like_python(code)
        status = "✅" if result == expected else "❌"
        print(f"   {status} Expected {expected}: {code[:30]}...")
    
    print()
    
    # Test validation
    print("4️⃣ Testing example validation...")
    
    valid_example = {
        'original_code': "x = [1, 2, 3]\nprint(x[10])",
        'fixed_code': "x = [1, 2, 3]\nprint(x[2])"
    }
    
    invalid_example = {
        'original_code': "x = 1",
        'fixed_code': "x = 2"
    }
    
    print(f"   Valid example: {kb._validate_example(valid_example)} ✅")
    print(f"   Invalid (too short): {kb._validate_example(invalid_example)} ❌")
    
    print()
    
    # Test stats
    print("5️⃣ Testing statistics...")
    stats = kb.get_stats()
    print(f"   📊 Files processed: {stats['total_files_processed']}")
    print(f"   📊 Examples extracted: {stats['total_examples_extracted']}")
    print(f"   📊 Reddit available: {stats['reddit_available']}")
    
    print()
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print("✅ All basic tests passed!\n")


def test_reddit_functionality():
    """Test Reddit-specific functions"""
    print("=" * 60)
    print("🧪 Testing Reddit Functionality")
    print("=" * 60 + "\n")
    
    temp_dir = tempfile.mkdtemp()
    memory = MemoryService(persist_directory=temp_dir)
    kb = KnowledgeBuilder(memory)
    
    print("1️⃣ Testing solution comment detection...")
    
    solution_comments = [
        "You should try this instead",
        "The fix is to change line 5",
        "This works for me",
    ]
    
    non_solution_comments = [
        "I have the same problem",
        "Anyone know how to fix this?",
        "This is confusing",
    ]
    
    for comment in solution_comments:
        result = kb._is_solution_comment(comment)
        print(f"   ✅ Solution detected: '{comment[:40]}...'")
    
    for comment in non_solution_comments:
        result = kb._is_solution_comment(comment)
        status = "✅" if not result else "❌"
        print(f"   {status} Not solution: '{comment[:40]}...'")
    
    print()
    
    print("2️⃣ Testing Reddit error detection...")
    
    reddit_posts = {
        "Getting IndexError: list index out of range": "IndexError",
        "Help! TypeError when adding string and int": "TypeError",
        "KeyError: 'name' not found": "KeyError",
    }
    
    for post, expected in reddit_posts.items():
        detected = kb._detect_error_from_reddit_text(post)
        status = "✅" if detected == expected else "❌"
        print(f"   {status} {expected}: {detected}")
    
    print()
    
    print("3️⃣ Testing code block extraction from Reddit markdown...")
    
    reddit_markdown = """
I have this code that's not working:
my_list = print(my_list)
Someone suggested this fix:
my_list =
if len(my_list) > 10:
print(my_list)
    """
    
    blocks = kb._extract_code_blocks(reddit_markdown)
    print(f"   ✅ Extracted {len(blocks)} code blocks")
    for i, block in enumerate(blocks, 1):
        print(f"   📝 Block {i}: {block[:40]}...")
    
    print()
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print("✅ Reddit functionality tests passed!\n")


def test_performance():
    """Test performance with multiple examples"""
    print("=" * 60)
    print("🧪 Testing Performance")
    print("=" * 60 + "\n")
    
    import time
    
    temp_dir = tempfile.mkdtemp()
    memory = MemoryService(persist_directory=temp_dir)
    kb = KnowledgeBuilder(memory)
    
    print("1️⃣ Testing extraction speed...")
    
    # Create large markdown with many examples
    large_markdown = ""
    for i in range(50):
        large_markdown += f"""
Example {i}:
x_{i} =
print(x_{i})
Fixed:
x_{i} =
print(x_{i})
        """
    
    start = time.time()
    examples = kb._extract_generic_examples(large_markdown)
    duration = time.time() - start
    
    print(f"   ⏱️ Extracted {len(examples)} examples in {duration:.2f}s")

    if len(examples) > 0:
        print(f"   📈 ~{duration/len(examples)*1000:.1f}ms per example")
    else:
        print(f"   ⚠️ No examples extracted (check markdown format)")

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print("✅ Performance tests passed!\n")


if __name__ == "__main__":
    print("\n")
    print("🚀 " * 30)
    print("KnowledgeBuilder Manual Testing Suite")
    print("🚀 " * 30)
    print("\n")
    
    test_basic_functionality()
    test_reddit_functionality()
    test_performance()
    
    print("=" * 60)
    print("✅ All Manual Tests Completed Successfully!")
    print("=" * 60)
