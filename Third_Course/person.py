class HandleAge:
    def __set__(self, instance, value):
        print(f"正在设置 age = {value}，先检查是不是数字...")
        if not isinstance(value, (int, float)):
            raise TypeError("年龄必须是数字！")
        if value < 0 or value > 150:
            raise ValueError("年龄必须在 0-150 之间！")
        setattr(
            instance, "_age", value
        )  # 将值存储在 instance 的 _age 属性中, 避免与描述符属性名冲突

    def __get__(self, instance, owner):
        print("正在获取 age")
        return instance._age

    def __delete__(self, instance):
        print("删除了 age")
        del instance._age


class Person:
    """定义一个 Person 类，包含一个 age 属性，使用 HandleAge 作为描述符"""

    age = HandleAge()

    def __init__(self, value1, value2):
        self.name = value1
        self.age = value2
        print(f"创建了一个 {self.name} 年龄为 {self.age} 的人")


class Student(Person):  # 继承 Person 类
    """定义一个 Student 类，继承自 Person 类，增加一个 grade 属性"""

    def __init__(self, value1, value2, value3):
        super().__init__(value1, value2)  # 调用父类的 __init__ 方法
        self.grade = value3
        print(f"创建了一个 {self.name} 年龄为 {self.age} 的 {self.grade} 年级的学生")


if __name__ == "__main__":
    p1 = Person("小王", 18)
    print(p1.age)
    p1.age = 19
    print(p1.age)
    p2 = Student("小王", 18, "大一")
    print(p2.age)
    print(p2.grade)
    p2.age = 19
    print(p2.age)
