# Nesting a for loop within another for loop is a powerful way to process data.
# It's just a block of code inside another block
# Let's see using for loops to generate times tables

for i in range(1, 13):
    for j in range(1, 13):
        print("{0} times {1} is {2}".format(j, i, i * j))
    print("---------------")


