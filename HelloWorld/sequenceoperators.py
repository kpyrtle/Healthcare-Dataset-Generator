string1 = "he's  "
string2 = "probably "
string3 = "pining "
string4 = "for the "
string5 = "fjords"

# Gets same result
print(string1 + string2 + string3 + string4 + string5)
print("he's " "probably " "pining " "for the " "fjords")

# prins hello 5 times
print("Hello " * 5)

# you can't concatenate or multiply a range
# print("Hello " * 5 + 4) #this would give the error: can only concatenate str (not "int") to str

print("Hello " * (5 + 4))
# because of the (), line 17 evaluates 5+4 to get 9, so it should repeat the line 9 times

print("Hello " * 5 + "4") # should repeat line 5 times and append the string "4"

print()

# There's also an operator to check if one string is a substring of another
today = "friday"
print("day" in today) # true
print("fri" in today) # true
print("thur" in today) # False
print("parrot" in "fjord") # false
