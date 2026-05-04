# #         012345678901234
# #parrot = "Norwegian Blue"
#
# # you can produce a slice by providing three numbers separated by colons
# # these numbers are the start, stop, and step values.
#
# # Let's look at slicing without a step first
# print(parrot[0:6]) # Norweg ~ this is up to 6 characters, but not including stop value
# print(parrot[-14:-8]) # Norweg
#
# print()
#
# print(parrot[-4:2]) # prints nothing because you can't go backwards from the starting
#
# print()
#
# print(parrot[-4:-2]) # Bl
# print(parrot[-4:12]) # Bl

#Comment out the above before moving onto slicing with a step
# Slicing with a step

#         012345678901234
parrot = "Norwegian Blue"

#starting at index 0 (which is N), extracts all characters up to, but not including index 6 (i), in steps of 2
print(parrot[0:6:2]) # Nre
#
print(parrot[0:6:3]) # Nw

print()

# number = "9,223,372,036,854,775,807"
# print(number[1::4])

number = "9,223;372:036 854,775;807"
seperators = number[1::4]
print(seperators)

values = "".join(char if char not in seperators else " " for char in number).split()
print([int(val) for val in values])


