print("Today is a good day to learn python")
print('Python is fun')
print("Python's string are easy to use")
print('We can even include "quotes" in strings')
print("hello" + "world")
greeting = "hello"

name = "Kayla"

# add a space if you want
print(greeting + ' ' + name)

age = 24
print(age)

#find the data types of age and greeting
print(type(greeting))
print(type(age))


# age_in_words = "2 years"
# print(age)
# print(name + " is " + age + "years old") # this gives an error due to age being int and not str

print(name + f" is {age} years old")
# f-string defined by putting f before opening quotes
# Now we can use a variable name inside {}
# remove " after is and the + symbols

print()

#formatting with replacement fields also works with f-strings
print(f"Pi is approximately {22 / 7:12.50f}")
# we've used an expression instead of a variable name (22 / 7:12.50f)

# we can also calculate 22 / 7 first, then use a variable
pi = 22 / 7
print(f"Pi is approximately {pi:12.50f}")

