# 父类 Person
class Person:
    def __init__(self, a, b):
        self.name = a
        self.age = b

    def say(self, x):
        pass


# 子类1 - Student
class Student(Person):
    def __init__(self, a, b, c):
        super().__init__(a, b)
        self.grade = c

    def listen(self):
        print("听课")


# 子类2 - Teacher
class Teacher(Person):
    def __init__(self, a, b, c):
        super().__init__(a, b)
        self.level = c

    def teach(self):
        print("授课")


# 使用示例
if __name__ == "__main__":
    # 创建 Student 对象
    student = Student("小明", 20, "三年级")
    print(f"学生姓名：{student.name}")
    print(f"学生年龄：{student.age}")
    print(f"学生年级：{student.grade}")
    student.listen()

    print("\n")

    # 创建 Teacher 对象
    teacher = Teacher("王老师", 35, "高级")
    print(f"老师姓名：{teacher.name}")
    print(f"老师年龄：{teacher.age}")
    print(f"老师级别：{teacher.level}")
    teacher.teach()
