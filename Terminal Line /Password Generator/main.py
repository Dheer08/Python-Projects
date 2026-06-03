import random


print("Welcome to the Password Generator!")
print("Please answer the following questions to generate your password.")
length = int(input("Enter the desired length of your password: "))  
include_uppercase = input("Include uppercase letters? (yes/no): ").lower() == "yes"
include_numbers = input("Include numbers? (yes/no): ").lower() == "yes"
include_symbols = input("Include symbols? (yes/no): ").lower() == "yes"

password = ""
characters = ""

if include_uppercase:
    characters += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

if include_numbers:
    characters += "0123456789"

if include_symbols:
    characters += "!@#$%^&*()-+"

for _ in range(length):
    password += random.choice(characters)

print("Your generated password is:", password)
