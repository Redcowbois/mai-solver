import my_module

# Test the function
result = my_module.add(10, 25)
print(f"10 + 25 = {result}")  # Outputs: 10 + 25 = 35

# Test keyword arguments (enabled by py::arg)
print(my_module.add(a=3, b=7))  # Outputs: 10

# Test the class
dog = my_module.Pet("Milo")
print(dog.bark())              # Outputs: Milo says woof!

# Test getter/setter property
dog.name = "Otis"
print(dog.name)                # Outputs: Otis
print(dog.bark())              # Outputs: Otis says woof!