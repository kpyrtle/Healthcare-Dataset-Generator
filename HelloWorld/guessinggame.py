answer = 5

print("Please guess a number between 1 and 10: ")
guess = int(input())

# if guess != answer:
#     if guess < answer:
#         print("Please guess higher")
#     else:
#         print("Please guess lower")
#     guess = int(input())
#     if guess == answer:
#         print("Well done, you guessed it)")
#     else:
#         print("Sorry, you have not guessed correctly")
# else:
#     print("You got it the first time")




# if guess < answer:
#     print("Please guess higher")
#     guess = int(input())
#     if guess == answer:
#         print("Well done, you guessed it")
#     else:
#         print("Sorry, you have not guessed correctly")
# elif guess > answer:
#     print("Please guess lower")
#     guess = int(input())
#     if guess == answer:
#         print("Well done, you guessed it")
#     else:
#         print("Sorry, you have not guessed correctly")
# else:
#     print("You got it first time")


# You can have one or more elif blocks
# elif has to cme after if, but before else (if there is one)
# else doesn't have to be used, but must come after if

# a single = is used when binding a variable to a value, or when assigning a value to a variable
# when testing for quality, use two ==

# Challenge: change line 6 to if guess == answer, then change program to give correct results
if guess == answer:
    print("You got it the first time")
else:
    if guess < answer:
        print("Please guess higher")
    else:
        print("Please guess lower")
    guess = int(input())
    if guess == answer:
        print("Well done, you guessed it)")
    else:
        print("Sorry, you have not guessed correctly")
