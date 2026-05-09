password = "052096"
user_password = input("Enter your password: ")
n = 5

while password != user_password:
    print("Access Denied")
    n -= 1
    print(f"You have {n} attempts left")
    if n == 0:
        print("You have no attempts left")
        break
    user_password = input("Enter your password: ")
else:
    print("Access Granted")


while True:
    user_password = input("Enter your password: ")
    if user_password == f(n):
        print("Access Granted")
        break
    else:
        print("Access Denied")
        n -= 1
        print(f"You have {n} attempts left")
        if n == 0:
            print("You have no attempts left")
            break
