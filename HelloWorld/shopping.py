# sometimes you may need to interrupt the normal flow of a loop, to either jump out of it or stop the current iteration and move on to the next one
# let's look at continue and break statements to use with loops
    # we'll be using lists, ordered sequences of values enclosed in square brackets.
    # We may have a shopping list

shopping_list = ["milk", "pasta", "eggs", "spam", "bread", "rice"]

# for item in shopping_list:
#     if item != "spam":
#         print("Buy " + item)

for item in  shopping_list:
    if item == "spam":
        break

    print("Buy " + item)