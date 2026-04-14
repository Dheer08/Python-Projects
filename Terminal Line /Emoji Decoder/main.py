import emoji

text = input("Enter text with emojis: ")

decoded = emoji.demojize(text)

print("Decoded text:")
print(decoded)