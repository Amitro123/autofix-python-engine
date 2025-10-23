"""
Manual testing script for MemoryService
Run this interactively to test the service
"""

from autofix_core.application.services.memory_service import MemoryService
import time

def test_basic_functionality():
    """Test basic store and search"""
    print("🧪 Testing MemoryService Basic Functionality\n")
    
    # Initialize
    print("1️⃣ Initializing MemoryService...")
    memory = MemoryService(persist_directory="./test_chroma_db")
    print(f"   ✅ Initialized. Collection: {memory.collection.name}\n")
    
    # Store some fixes
    print("2️⃣ Storing example fixes...")
    
    fixes = [
        {
            'original': "x = [1, 2, 3]\nprint(x[10])",
            'error': "IndexError",
            'fixed': "x = [1, 2, 3]\nif len(x) > 10:\n    print(x[10])\nelse:\n    print('Index out of range')"
        },
        {
            'original': "x = [5, 6]\nprint(x[100])",
            'error': "IndexError",
            'fixed': "x = [5, 6]\nprint(x[1])"
        },
        {
            'original': "name = 'Alice'\nage = '25'\ntotal = name + age",
            'error': "TypeError",
            'fixed': "name = 'Alice'\nage = '25'\ntotal = name + ' is ' + age"
        }
    ]
    
    for i, fix in enumerate(fixes, 1):
        fix_id = memory.store_fix(
            fix['original'],
            fix['error'],
            fix['fixed'],
            method='manual_test'
        )
        print(f"   ✅ Stored fix {i}: {fix_id[:8]}...")
    
    print()
    
    # Get stats
    print("3️⃣ Getting statistics...")
    stats = memory.get_stats()
    print(f"   📊 Total examples: {stats['total_examples']}")
    print(f"   📦 Collection: {stats['collection_name']}\n")
    
    # Search similar
    print("4️⃣ Searching for similar fixes...")
    
    test_code = "arr = [10, 20, 30]\nvalue = arr[999]"
    print(f"   🔍 Query: {test_code}")
    
    results = memory.search_similar(test_code, "IndexError", k=2)
    
    print(f"   📋 Found {len(results)} similar fixes:\n")
    
    for i, result in enumerate(results, 1):
        print(f"   Result {i}:")
        print(f"   - Original: {result['original_code'][:50]}...")
        print(f"   - Fixed: {result['fixed_code'][:50]}...")
        print(f"   - Distance: {result['distance']:.4f}")
        print()
    
    print("✅ All tests passed!\n")
    
    # Cleanup
    print("🧹 Cleaning up test database...")
    import shutil
    shutil.rmtree("./test_chroma_db", ignore_errors=True)
    print("   ✅ Cleaned up\n")

def test_persistence():
    """Test that data persists between sessions"""
    print("🧪 Testing Persistence\n")
    
    db_path = "./test_chroma_db_persist"
    
    # Session 1: Store data
    print("1️⃣ Session 1: Storing data...")
    memory1 = MemoryService(persist_directory=db_path)
    memory1.store_fix("code1", "Error1", "fixed1", "test")
    memory1.store_fix("code2", "Error2", "fixed2", "test")
    print(f"   ✅ Stored 2 fixes\n")
    
    # Session 2: Load data
    print("2️⃣ Session 2: Loading data...")
    memory2 = MemoryService(persist_directory=db_path)
    stats = memory2.get_stats()
    print(f"   ✅ Loaded. Found {stats['total_examples']} examples")
    
    if stats['total_examples'] == 2:
        print("   ✅ Persistence works!\n")
    else:
        print("   ❌ Persistence failed!\n")
    
    # Cleanup
    print("🧹 Cleaning up...")
    import shutil
    shutil.rmtree(db_path, ignore_errors=True)
    print("   ✅ Cleaned up\n")

def test_performance():
    """Test performance with many examples"""
    print("🧪 Testing Performance\n")
    
    memory = MemoryService(persist_directory="./test_chroma_db_perf")
    
    # Store 100 examples
    print("1️⃣ Storing 100 examples...")
    start = time.time()
    
    for i in range(100):
        memory.store_fix(
            f"code_{i} = []\nprint(code_{i}[{i}])",
            "IndexError",
            f"code_{i} = []\nif code_{i}:\n    print(code_{i}[0])",
            "perf_test"
        )
    
    store_time = time.time() - start
    print(f"   ⏱️ Stored 100 examples in {store_time:.2f}s")
    print(f"   📈 ~{store_time/100*1000:.1f}ms per example\n")
    
    # Search 10 times
    print("2️⃣ Searching 10 times...")
    start = time.time()
    
    for i in range(10):
        results = memory.search_similar(
            "test_code = []\nprint(test_code[999])",
            "IndexError",
            k=5
        )
    
    search_time = time.time() - start
    print(f"   ⏱️ 10 searches in {search_time:.2f}s")
    print(f"   📈 ~{search_time/10*1000:.1f}ms per search\n")
    
    # Cleanup
    print("🧹 Cleaning up...")
    import shutil
    shutil.rmtree("./test_chroma_db_perf", ignore_errors=True)
    print("   ✅ Cleaned up\n")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 MemoryService Manual Testing")
    print("=" * 60 + "\n")
    
    test_basic_functionality()
    test_persistence()
    test_performance()
    
    print("=" * 60)
    print("✅ All manual tests completed!")
    print("=" * 60)
