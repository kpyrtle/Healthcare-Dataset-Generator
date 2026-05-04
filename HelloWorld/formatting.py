for i in range(1, 13):
    print("No. {0} squared is {1} and cubed is {2}".format(i, i ** 2, i ** 3))
    #$ we have the values of the number, the value squared, and the value cubed

# you can provide any expression in the format (). they don't have to be variables or literal numbers

print()

# numbers aren't lined up, can be fixed by applying formatting
for i in range(1, 13):
    print("No. {0:2} squared is {1:4} and cubed is {2:4}".format(i, i ** 2, i ** 3))
# {0:2} with 2 being the width, separated from the index with a :
# Everything in the column prints in a width of two characters
# Think of it as reserving two spaces on the screen, so that the one digit values still line up with the two digit ones

print()

# Maybe a width of 3 on the {1:4} would be better
for i in range(1, 13):
    print("No. {0:2} squared is {1:3} and cubed is {2:4}".format(i, i ** 2, i ** 3))

print()

# Another example of whatever this is
# num = 75
# print("I made a formatted sentence using the number {0}. My number {1} * 2 = {2}".format(num, num, num * 2))


# We can also align the values in their field width.

# To left align the values, we place a < symbol after the colon
for i in range(1, 13):
    print("No. {0:2} squared is {1:<3} and cubed is {2:<4}".format(i, i ** 2, i ** 3))

print()

# < will left align, > will right align, and ^ will center within the field width
for i in range(1, 13):
    print("No. {0:2} squared is {1:<3} and cubed is {2:^4}".format(i, i ** 2, i ** 3))

print()

# for floating point numbers, you can specify a precision - the number of digits after the decimal point.
# For our precision, we specify the precision after a decimal point, following the width

# We're going to put replacement field 0:12, which is the precision for a floating-point number, then dot format
print("Pi is approximately {0:12}".format(22/7))
print("Pi is approximately {0:12f}".format(22/7))
print("Pi is approximately {0:12.50f}".format(22/7))
print("Pi is approximately {0:52.50f}".format(22/7))
print("Pi is approximately {0:62.50f}".format(22/7))
print("Pi is approximately {0:<72.50f}".format(22/7))
print("Pi is approximately {0:<72.54f}".format(22/7))

print()

# the field number in replacement fields is optional
    # If they're not specified, python takes the value from the format method in order
for i in range(1, 13):
    print("No. {} squared is {} and cubed is {:4}".format(i, i ** 2, i ** 3))
# In output, third field shows you can still use a colon to control the layout, even if you haven't specified a field #
# all values in the final column of output are printing in a field with the 4
# If you don't provide field #s, you can't use a value more than once
    #nor can you change the order in which values are used

# Our earlier example with the # of days in the month, wouldn't have worked without field #s
