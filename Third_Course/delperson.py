class Person:
    def __del__(self):
        print("Person.__del__ called!")


p1 = Person()
p2 = p1
print("Before del p1")
del p1
print("After del p1")
print("p2 still exists:", p2)

input("Press Enter to exit...")  # 等待用户输入
