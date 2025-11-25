# in is used in sequences
parrot = "Norwegian Blue"

letter = input("Enter a character: ")

if letter in parrot:
    print("{} is in {}".format(letter, parrot))
else:
    print("I don't need that letter")

# when entering input(), remember that string comparisons are case-sensitive
# you can type parts of the string, like Blue
