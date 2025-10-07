# demo_syntax_error.py
def greet(name)  # Missing colon!
    return f'Hello, {name}!'

print(greet('World'))
