# Write a small program to ask for a name and age
    # When both values have been entered, check if the person is the right age tto go on an 18-30 holiday (must be over 18 and under 31)

name = input("What is your name? ")
age = int(input("How old are you? "))

if age >= 18 and age < 31:
    print("Enjoy your holiday")
else:
    print("No holiday for you")