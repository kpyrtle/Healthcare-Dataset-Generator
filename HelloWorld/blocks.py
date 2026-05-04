# We've seen how to store values in variables and print them out
    # As well as getting input from the keyboard

# Now let's get Python to make decisions, based on the values of variables and input.

name = input("Please enter your name: ")
age = int(input("How old are you, {0} ".format(name)))
print(age)

# The input function returns as a str or string datatype
    # You have to convert it to an int if you want age to represent a number
        # We do that with the int function.
        # Change line 2: age = input("How old are you, {0}? ".format(name)) to use int and input
            # Using input and int together is common when you want to get a number from the user
            # Your code will crash if you type anything that can't be converted to an int

# Let's see what we can do with age
    # Are you old enough to vote?
# if age >= 18:
#     print("You are old enough to vote")
#     print("Please put an X in the box")
# else:
#     print("Please come back in {0} years",format(18 - age))

if age < 18:
    print("Please come back in {0} years".format(18 - age))
elif age== 900:
    print("Sorry, Yoda, you die in Return of the Jedi")
else:
    print("You are old enough to vote")
    print("Please put an X in the box")




