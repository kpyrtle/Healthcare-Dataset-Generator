# Let's see what isn't in the sequence using not in

activity = input("What would you like to do today? ")

# if "cinema" not in activity:
#     print("But I want to go to the cinema")
# remember case sensitivity

# Use casefold() to convert string to lowercase
    # it handles different character sets better than just converting to lowercase would
if "cinema" not in activity.casefold():
    print("But I want to go to the cinema")