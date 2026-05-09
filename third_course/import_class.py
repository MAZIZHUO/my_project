from person import Person as MyPerson  # 导入 person 模块中的 Person 和 Student 类
from person import Student as MyStudent

# 第一种 import person；import person as p
# 第二种 from person import Person ；from person import Person as MyPerson
# 第三种 from person import * ；不推荐使用，因为可能会引入不必要的名称，导致命名冲突

p1 = MyPerson("小明", 100)
print(p1.age)
p2 = MyStudent("小红", 90, "大二")
print(p2.age)
print(p2.grade)
