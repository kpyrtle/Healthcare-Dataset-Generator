age = 24
print("My age is " + str(age) + " years")

print()

# python 3 allows strings to be formatted using replacement fields and the dot format method
print("My age is {0} years".format(age))

print("There are {0} days in {1}, {2}, {3}, {4}, {5}, {6} and {7}"
      .format(31,"Jan", "Mar", "May", "Jul", "Aug", "Oct", "Dec"))
# the replacement fields are replaced by the values that appear in the dot format method
    # with the first value replacing 0, the second replacing 1 and so on
    # we've got a total of 8 items in the list after the dot format, each of those will go into the replacement fields numbered 0 to 7

#You could also just include it in the string
print("There are {0} days in Jan, Mar, May, Jul, Aug, Oct, and Dec".format(31))

print()

# fields can be used more than once and they don't have to appear in the order that the values are provided to the dot format method call
    # it's the field index, the number inside the {} that determines which value to be used

print("Jan: {2}, Feb: {0}, Mar: {2}, Apr: {1}, May: {2}, Jun: {1}, July: {2}, Sep: {1}, Oct: {2}, Nov: {2}, Dec: {2}"
      .format(28, 30, 31))

print()

print("""Jan: {2},
         Feb: {0},
         Mar: {2},
         Apr: {1},
         May: {2},
         Jun: {1},
         July: {2},
         Sep: {1},
         Oct: {2},
         Nov: {2},
         Dec: {2}""".format(28, 30, 31))