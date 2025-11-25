# python sequence types let you create a slice

# strings are a sequence data type.
# We've seen how to print() and concatenate, but we can pick out specific characters, or substrings

# 1
#         012345678901234
parrot = "Norwegian Blue"

# you can produce a slice by providing three numbers separated by colons
    # these numbers are the start, stop, and step values.

# Let's look at slicing without a step first
print(parrot[0:6]) # Norweg this is up to 6, but not including stop value
print(parrot[3:5]) # gets w and e from string
print(parrot[0:9]) # gets the word norwegian
# we can also leave the starting value out
print(parrot[:9]) # gets the same result as 0:9

print()
# get the word Blue
print(parrot[10:14])
#rewrite last line with nothing after the colon
print(parrot[10:]) #still goes to end of string

print()

print(parrot[:6])
print(parrot[6:])

print()

print(parrot[:6] + parrot[6:])

print(parrot[:])

#practice
letters = "abcdefghijklmnopqrstuvwxyz"