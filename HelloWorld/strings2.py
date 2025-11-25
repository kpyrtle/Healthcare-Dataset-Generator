# strings are a sequence data type.
    # We've seen how to print() and concatenate, but we can pick out specific characters, or substrings

# 1
#         012345678901234
parrot = "Norwegian Blue"
print(parrot) # we'd get the full string Norwegian Blue

# this gives us the fourth letter, w. Even though I put 3, python starts at zero
print(parrot[3])
# Four uses of square brackets in python. They all involve accessing individual items in something.

# Challenges

# Add code to a program so it prints out "we win"
# If you run the first two, you get the full on string Norwegian Blue, and then a w

# Each character should appear on a separate line
print(parrot[4])
print(parrot[9])
print(parrot[3])
print(parrot[6])
print(parrot[8])
    # Should get the characters from the parrot string, using indexing


# Let's index backwards
# print(parrot[-1]) # gets the last letter, which is e

# print(parrot[-14])
print(parrot)
print()
# use negative indexing to get the same message "we win"
print(parrot[-11])
print(parrot[-1])
print(parrot[-5])
print(parrot[-11])
print(parrot[-8])
print(parrot[-6])

