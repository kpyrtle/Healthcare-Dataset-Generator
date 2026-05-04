# for loop works by iterating over some set of values
    # it assigns each of the values, one by one, to one or more variables.
    # it then executes a block of code once for each value
    # the set of values comes from a sequence, or some other iterable object
        # an iterable object is anything that can be iterated over. A sequence is also iterable

# parrot = "Norwegian Blue"
#
# for character in parrot:
#     print(character)
# # prints out each character from the string within parrot



# flow control: stepping through a for loop
    # we used a slice to extract all the delimiters from a list of numbers
# starts at 1, then extracts every fourth character (each symbol) until it reached the end of the string
    # this works, but relies on there being three digits in each section of #'s after the first one

# number = "9,223;372:036 854,775;807"
# separators = number[1::4]
# print(separators)

# values = "".join(char if char not in separators else " " for char in number).split()
# print([int(val) for val in values])


# We should examine each character in the number string to check if it's a digit or not.
    # A for loop can be used for that

# Iterate over numbers and append anything that isn't a digit to the separators string
    # First step is to initialize our separators variable
# number = "9,223;372:036 854,775;807"
# separators = ""
#
# for char in number:
#     if not char.isnumeric():
#         separators = separators + char
#
# print(separators)
#
# values = "".join(char if char not in separators else " " for char in number).split()
# print([int(val) for val in values])


number = input("Please enter a series of numbers, using any separators you like: ")
separators = ""

for char in number:
    if not char.isnumeric():
        separators = separators + char

# print(separators)

values = "".join(char if char not in separators else " " for char in number).split()
print(sum([int(val) for val in values]))

