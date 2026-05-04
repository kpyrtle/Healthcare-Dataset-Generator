splitstring = "This string has been\nsplit over\nseveral\nlines"
print(splitstring)

tabbedstring = "1\t2\t3\t4\t5"
print(tabbedstring)

print('The pet shop owner said "No, no, \'e\'s uh,...he\'s resting".')
# or
print("The pet shop owner said \"No, no, 'e's uh...he's resting\".")

print("""The pet shop owner said "No, no, \
 'e's uh,...he's resting". """)

anothersplitstring = """This string has been \
split over \
several \
lines"""
print(anothersplitstring)

# because of reserved letters, this can't work
    #print("C:\Users\timbuchalka\notes.txt")
# let's make it work with a raw string
print(r"C:\\Users\\timbuchalka\\notes.txt")
