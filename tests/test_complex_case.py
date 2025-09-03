def a_function(
    param1,
    param2):

    if param1 > 10:
        print("Hello")
    else:
        print("World")

try:
    print("Testing")
except Exception as e:
    print(e)

if __name__ == "__main__":
    a_function(15, 5)
