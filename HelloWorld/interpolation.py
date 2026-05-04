# python 2 formatter is % and is followed by a letter to indicate how formatting should work

age = 33
print("My age is %d years" % age)

# if you wanted to inject a float into a string, we'd use %f, provide a string, and to provide a string we'd use %s
major = "years"
minor = "months"
print("My age is %d %s, %d %s" % (age, major, 6, minor))
    # first %d is replaced by first variable age
    # first %s replaced by string variable major
    # second %d is replaced by value 6
    # final %s is replaced by minor

# Replacement is strictly one value at a time, from left to right
# with none of the flexibility offered by python 3's replacement fields

print("Pi is approximately %f" % (22 / 7))
# we've used %f to represent the floating-point result

# you can specify the precision of the #
    #instead of having %f, we can add the precision after the %, before the f
print("Pi is approximately %60.50f" % (22 / 7))

# you can also use:
    # %x to display #s in hexadecimal
    # %o for octal
    # %e for scientific notation