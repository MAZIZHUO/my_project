# 类的组合（Composition）案例
# 组合体现的是 "has-a" 关系，即一个类包含另一个类的实例

# ==================== 基础组件类 ====================


class Engine:
    """引擎类"""

    def __init__(self, horsepower):
        self.horsepower = horsepower

    def start(self):
        print(f"引擎启动，马力: {self.horsepower}")

    def stop(self):
        print("引擎停止")


class Wheel:
    """车轮类"""

    def __init__(self, size):
        self.size = size

    def rotate(self):
        print(f"{self.size}英寸车轮旋转")


class GPS:
    """GPS导航类"""

    def __init__(self, brand):
        self.brand = brand
        self.location = "未知位置"

    def get_location(self):
        return self.location

    def set_location(self, location):
        self.location = location
        print(f"GPS定位到: {location}")


# ==================== 组合类 ====================


class Car:
    """汽车类 - 通过组合使用Engine、Wheel和GPS"""

    def __init__(self, brand, engine_hp, wheel_size, gps_brand):
        self.brand = brand
        # 组合：汽车"拥有"引擎、车轮和GPS
        self.engine = Engine(engine_hp)
        self.wheels = [Wheel(wheel_size) for _ in range(4)]  # 4个车轮
        self.gps = GPS(gps_brand)

    def start_car(self):
        print(f"\n{self.brand} 汽车启动")
        self.engine.start()
        for i, wheel in enumerate(self.wheels, 1):
            wheel.rotate()

    def navigate(self, destination):
        print(f"\n导航前往: {destination}")
        self.gps.set_location(destination)
        print(f"当前位置: {self.gps.get_location()}")

    def stop_car(self):
        print(f"\n{self.brand} 汽车停止")
        self.engine.stop()


class Student:
    """学生类"""

    def __init__(self, name, age):
        self.name = name
        self.age = age

    def introduce(self):
        print(f"我叫{self.name}，今年{self.age}岁")


class Book:
    """书籍类"""

    def __init__(self, title, author):
        self.title = title
        self.author = author

    def show_info(self):
        print(f"《{self.title}》- 作者: {self.author}")


class Library:
    """图书馆类 - 通过组合管理多个Student和Book"""

    def __init__(self, name):
        self.name = name
        self.books = []  # 组合：图书馆"拥有"多本书
        self.students = []  # 组合：图书馆"拥有"多个学生

    def add_book(self, book):
        self.books.append(book)
        print(f"添加书籍: 《{book.title}》")

    def register_student(self, student):
        self.students.append(student)
        print(f"注册学生: {student.name}")

    def show_all_books(self):
        print(f"\n{self.name} 的藏书:")
        for book in self.books:
            book.show_info()

    def show_all_students(self):
        print(f"\n{self.name} 的注册学生:")
        for student in self.students:
            student.introduce()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("案例1: 汽车组合")
    print("=" * 50)

    # 创建汽车对象（自动创建引擎、车轮和GPS）
    my_car = Car("Tesla", 300, 18, "Garmin")
    my_car.start_car()
    my_car.navigate("北京天安门")
    my_car.stop_car()

    print("\n" + "=" * 50)
    print("案例2: 图书馆组合")
    print("=" * 50)

    # 创建图书馆
    city_library = Library("市立图书馆")

    # 添加书籍
    book1 = Book("Python编程", "张三")
    book2 = Book("数据结构", "李四")
    book3 = Book("算法导论", "王五")

    city_library.add_book(book1)
    city_library.add_book(book2)
    city_library.add_book(book3)

    # 注册学生
    student1 = Student("小明", 20)
    student2 = Student("小红", 22)

    city_library.register_student(student1)
    city_library.register_student(student2)

    # 显示所有信息
    city_library.show_all_books()
    city_library.show_all_students()
