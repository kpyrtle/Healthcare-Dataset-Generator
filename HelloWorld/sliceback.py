letters = "abcdefghijklmnopqrstuvwxyz"

# Starts at index 25 (z), stop value to 0, and use step of -1
backwards = letters[25:0:-1]
print(backwards) # zyxwvutsrqponmlkjihgfedcb
# Remember, negative stop values count backwards from the end of the sequence.
    #  Minus 1 means the last character in the string, meaning you requested a slice that goes from the z up to, but not including the z
    # Meaning, we get nothing

backwards = letters[25::-1]
print(backwards) # zyxwvutsrqponmlkjihgfedcba


# Challenge

# Using letters string, add some code to create the following slices
    # letters = "abcdefghijklmnopqrstuvwxyz"

# create slice that produces characters q p and o
print(letters[16:13:-1])

# slice the string to produce edcba
print(letters[4::-1])

# slice the string to produce the last 8 characters in reverse order.
print(letters[:-9:-1]) # no start, stopping at -9 (s) go back one index at a time

print(letters[-4:])
print(letters[-1:])

# gets the same result
print(letters[:1])
print(letters[0])


