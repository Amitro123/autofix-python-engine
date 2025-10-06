# Test AttributeError handling
class MyClass:
    def __init__(self):
        self.value = 42

obj = MyClass()
print(obj.nonexistent_attribute)  # This will raise AttributeError
